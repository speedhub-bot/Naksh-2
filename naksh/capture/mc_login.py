"""Self-contained Java-edition Minecraft login client.

Performs the full Mojang authentication handshake against an online-mode
server using the player's existing access token (from the MSA → Xbox → XSTS
chain we already do for auth).

Returns a structured :class:`LoginResult` whose ``status`` is one of
``login_success``, ``disconnected``, ``handshake_failed``, or ``error``.

We use this for ban detection on servers that perform their ban checks AFTER
authentication (DonutSMP, etc.) where the simple "send LoginStart and watch
for Disconnect" trick used for Hypixel doesn't surface the ban status.

No pyCraft, quarry, or twisted — just stdlib + ``cryptography``.

References:
* https://wiki.vg/Protocol#Login
* https://wiki.vg/Protocol_Encryption
* https://wiki.vg/Protocol#Set_Compression
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import socket
import struct
import threading
import time
import uuid as uuid_mod
import zlib
from dataclasses import dataclass
from typing import Any, Optional

import requests
from cryptography.hazmat.primitives.asymmetric import padding as asym_padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.serialization import load_der_public_key

log = logging.getLogger(__name__)

PROTOCOL_DEFAULT = 764  # 1.20.2 — modern enough for any current server
SESSION_JOIN_URL = "https://sessionserver.mojang.com/session/minecraft/join"
CONNECT_TIMEOUT = 8.0
READ_TIMEOUT = 12.0


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------
@dataclass
class LoginResult:
    status: str
    disconnect_reason: str = ""
    detail: str = ""

    @property
    def disconnected(self) -> bool:
        return self.status == "disconnected"

    @property
    def login_success(self) -> bool:
        return self.status == "login_success"


# ---------------------------------------------------------------------------
# Varint + packet helpers (no compression)
# ---------------------------------------------------------------------------
def _write_varint(value: int) -> bytes:
    if value < 0:
        value &= 0xFFFFFFFF
    out = bytearray()
    while True:
        temp = value & 0x7F
        value >>= 7
        if value:
            out.append(temp | 0x80)
        else:
            out.append(temp)
            return bytes(out)


def _read_varint_socket(sock: socket.socket) -> int:
    num = 0
    for i in range(5):
        chunk = sock.recv(1)
        if not chunk:
            raise ConnectionError("connection closed mid-varint")
        byte = chunk[0]
        num |= (byte & 0x7F) << (7 * i)
        if not (byte & 0x80):
            return num
    raise ValueError("varint too long")


def _read_varint_bytes(data: bytes, offset: int) -> tuple[int, int]:
    num, shift = 0, 0
    for _ in range(5):
        if offset >= len(data):
            raise ValueError("varint truncated")
        b = data[offset]
        offset += 1
        num |= (b & 0x7F) << shift
        if not (b & 0x80):
            return num, offset
        shift += 7
    raise ValueError("varint too long")


def _read_exact(sock: socket.socket, n: int) -> bytes:
    buf = bytearray()
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("connection closed mid-read")
        buf.extend(chunk)
    return bytes(buf)


def _string(s: str) -> bytes:
    encoded = s.encode("utf-8")
    return _write_varint(len(encoded)) + encoded


def _build_packet(packet_id: int, payload: bytes) -> bytes:
    inner = _write_varint(packet_id) + payload
    return _write_varint(len(inner)) + inner


# ---------------------------------------------------------------------------
# AES-CFB8 stream wrapper around a socket
# ---------------------------------------------------------------------------
class EncryptedStream:
    """Wrap a socket so reads decrypt and writes encrypt with AES/CFB8.

    Minecraft uses the shared secret as both key and IV — that's a quirk of
    the protocol, not a bug in our code.
    """

    def __init__(self, sock: socket.socket, shared_secret: bytes):
        cipher = Cipher(algorithms.AES(shared_secret), modes.CFB8(shared_secret))
        self._sock = sock
        self._encryptor = cipher.encryptor()
        self._decryptor = cipher.decryptor()
        self._buffer = bytearray()  # decrypted leftover bytes

    def recv(self, n: int) -> bytes:
        while len(self._buffer) < n:
            chunk = self._sock.recv(max(n - len(self._buffer), 1))
            if not chunk:
                raise ConnectionError("connection closed mid-encrypted-read")
            self._buffer.extend(self._decryptor.update(chunk))
        out = bytes(self._buffer[:n])
        del self._buffer[:n]
        return out

    def sendall(self, data: bytes) -> None:
        self._sock.sendall(self._encryptor.update(data))

    def settimeout(self, t: float) -> None:
        self._sock.settimeout(t)

    def close(self) -> None:
        try:
            self._sock.close()
        except OSError:
            pass


def _read_varint_stream(stream) -> int:
    """Read a varint from either a raw socket or an EncryptedStream."""
    num = 0
    for i in range(5):
        chunk = stream.recv(1)
        if not chunk:
            raise ConnectionError("connection closed mid-varint")
        byte = chunk[0]
        num |= (byte & 0x7F) << (7 * i)
        if not (byte & 0x80):
            return num
    raise ValueError("varint too long")


def _read_packet(stream, *, compression_threshold: int = -1) -> tuple[int, bytes]:
    """Read a single packet, returning ``(packet_id, payload)``.

    Handles SetCompression-enabled framing transparently. ``compression_threshold``
    of ``-1`` means compression is disabled.
    """
    packet_length = _read_varint_stream(stream)
    raw = bytearray()
    while len(raw) < packet_length:
        chunk = stream.recv(packet_length - len(raw))
        if not chunk:
            raise ConnectionError("connection closed mid-packet")
        raw.extend(chunk)
    raw = bytes(raw)

    if compression_threshold < 0:
        # No compression layer
        packet_id, off = _read_varint_bytes(raw, 0)
        return packet_id, raw[off:]

    data_length, off = _read_varint_bytes(raw, 0)
    body = raw[off:]
    if data_length == 0:
        # Below threshold → uncompressed payload follows
        packet_id, p_off = _read_varint_bytes(body, 0)
        return packet_id, body[p_off:]
    # Above threshold → zlib-compressed
    decompressed = zlib.decompress(body)
    packet_id, p_off = _read_varint_bytes(decompressed, 0)
    return packet_id, decompressed[p_off:]


# ---------------------------------------------------------------------------
# Mojang server-id hash
# ---------------------------------------------------------------------------
def _mojang_server_id(server_id_str: str, shared_secret: bytes,
                     public_key_der: bytes) -> str:
    sha1 = hashlib.sha1()
    sha1.update(server_id_str.encode("ascii"))
    sha1.update(shared_secret)
    sha1.update(public_key_der)
    digest = sha1.digest()
    n = int.from_bytes(digest, byteorder="big", signed=True)
    if n < 0:
        return "-" + format(-n, "x")
    return format(n, "x")


# ---------------------------------------------------------------------------
# Chat-component flattener (for disconnect reasons)
# ---------------------------------------------------------------------------
def flatten_chat(obj: Any) -> str:
    if obj is None:
        return ""
    if isinstance(obj, str):
        if obj.startswith("{") or obj.startswith("["):
            try:
                return flatten_chat(json.loads(obj))
            except json.JSONDecodeError:
                return obj
        return obj
    if isinstance(obj, list):
        return " ".join(flatten_chat(o) for o in obj)
    if isinstance(obj, dict):
        out = ""
        if "text" in obj:
            out += str(obj["text"])
        if "extra" in obj:
            out += flatten_chat(obj["extra"])
        if "translate" in obj:
            out += " " + str(obj["translate"])
        if "with" in obj:
            out += " " + flatten_chat(obj["with"])
        return out
    return str(obj)


# ---------------------------------------------------------------------------
# Packet builders
# ---------------------------------------------------------------------------
def _build_handshake(host: str, port: int, protocol: int) -> bytes:
    payload = (
        _write_varint(protocol)
        + _string(host)
        + struct.pack(">H", port)
        + _write_varint(2)  # Login state
    )
    return _build_packet(0x00, payload)


def _build_login_start(username: str, player_uuid: uuid_mod.UUID,
                       protocol: int) -> bytes:
    if protocol >= 764:
        # 1.20.2+: name + uuid (no signature data anymore)
        payload = _string(username) + player_uuid.bytes
    elif protocol >= 759:  # 1.19+
        # name + has_sig=false + has_uuid=true + uuid
        payload = (
            _string(username)
            + b"\x00"      # has signature data: false
            + b"\x01"      # has uuid: true
            + player_uuid.bytes
        )
    else:
        payload = _string(username)
    return _build_packet(0x00, payload)


def _build_encryption_response(encrypted_secret: bytes,
                               encrypted_token: bytes) -> bytes:
    payload = (
        _write_varint(len(encrypted_secret)) + encrypted_secret
        + _write_varint(len(encrypted_token)) + encrypted_token
    )
    return _build_packet(0x01, payload)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------
def login_check(
    *,
    host: str,
    port: int,
    username: str,
    player_uuid: str,
    access_token: str,
    protocol: int = PROTOCOL_DEFAULT,
    timeout: float = READ_TIMEOUT,
) -> LoginResult:
    """Perform a full Mojang-authenticated login attempt against ``host:port``.

    Returns a :class:`LoginResult`. The caller decides how to interpret it
    (e.g. mapping ``disconnected`` + a "banned" reason → BANNED).
    """
    try:
        clean_uuid = uuid_mod.UUID(hex=player_uuid.replace("-", ""))
    except (ValueError, AttributeError):
        return LoginResult("error", detail="invalid uuid")

    sock: Optional[socket.socket] = None
    try:
        sock = socket.create_connection((host, port), timeout=CONNECT_TIMEOUT)
        sock.settimeout(timeout)

        # 1. Handshake + LoginStart
        sock.sendall(_build_handshake(host, port, protocol))
        sock.sendall(_build_login_start(username, clean_uuid, protocol))

        # 2. Read response: Disconnect | EncryptionRequest | LoginSuccess | SetCompression
        compression_threshold = -1
        stream: Any = sock
        for _ in range(8):  # safety bound on the negotiation loop
            packet_id, payload = _read_packet(
                stream, compression_threshold=compression_threshold,
            )
            if packet_id == 0x00:
                # Disconnect (Login state)
                reason = _decode_login_disconnect(payload)
                return LoginResult("disconnected", disconnect_reason=reason)

            if packet_id == 0x02:
                # LoginSuccess — server has accepted us. We don't proceed
                # into the play state; just close cleanly.
                return LoginResult("login_success")

            if packet_id == 0x03:
                # SetCompression (during Login state)
                threshold, _ = _read_varint_bytes(payload, 0)
                compression_threshold = threshold
                continue

            if packet_id == 0x01:
                # EncryptionRequest — switch into encrypted mode
                new_stream = _do_encryption(
                    sock=sock,
                    payload=payload,
                    access_token=access_token,
                    selected_profile=clean_uuid.hex,
                )
                if new_stream is None:
                    return LoginResult(
                        "error", detail="encryption negotiation failed",
                    )
                stream = new_stream
                continue

            return LoginResult(
                "error", detail=f"unexpected login packet id {packet_id}",
            )

        return LoginResult("error", detail="login negotiation didn't terminate")
    except (socket.timeout, OSError, ConnectionError, ValueError) as e:
        return LoginResult("error", detail=str(e))
    finally:
        if sock is not None:
            try:
                sock.close()
            except OSError:
                pass


def _do_encryption(
    *,
    sock: socket.socket,
    payload: bytes,
    access_token: str,
    selected_profile: str,
) -> Optional[EncryptedStream]:
    """Handle an EncryptionRequest. Returns the new encrypted stream or None."""
    try:
        # server_id(string), pubkey_len(varint), pubkey, token_len(varint), token
        server_id_len, off = _read_varint_bytes(payload, 0)
        server_id = payload[off:off + server_id_len].decode("utf-8")
        off += server_id_len

        pubkey_len, off = _read_varint_bytes(payload, off)
        pubkey_der = payload[off:off + pubkey_len]
        off += pubkey_len

        token_len, off = _read_varint_bytes(payload, off)
        verify_token = payload[off:off + token_len]

        public_key = load_der_public_key(pubkey_der)
        shared_secret = os.urandom(16)

        server_id_hash = _mojang_server_id(server_id, shared_secret, pubkey_der)
        join_resp = requests.post(
            SESSION_JOIN_URL,
            json={
                "accessToken": access_token,
                "selectedProfile": selected_profile,
                "serverId": server_id_hash,
            },
            timeout=10,
        )
        if join_resp.status_code not in (200, 204):
            log.debug("sessionserver join %s: %s",
                      join_resp.status_code, join_resp.text[:200])
            return None

        encrypted_secret = public_key.encrypt(
            shared_secret, asym_padding.PKCS1v15(),
        )
        encrypted_token = public_key.encrypt(
            verify_token, asym_padding.PKCS1v15(),
        )

        sock.sendall(_build_encryption_response(encrypted_secret, encrypted_token))
        return EncryptedStream(sock, shared_secret)
    except Exception as e:
        log.debug("encryption handshake failed: %s", e)
        return None


def _decode_login_disconnect(payload: bytes) -> str:
    """Decode a Login-state Disconnect packet body."""
    try:
        length, off = _read_varint_bytes(payload, 0)
        reason_json = payload[off:off + length].decode("utf-8", errors="ignore")
        try:
            obj = json.loads(reason_json)
        except json.JSONDecodeError:
            return reason_json
        return flatten_chat(obj)
    except Exception:
        return payload.decode("utf-8", errors="ignore")


# ---------------------------------------------------------------------------
# Concurrency limiter so we don't hammer Mojang sessionserver / target server
# ---------------------------------------------------------------------------
_global_lock = threading.Semaphore(2)


def acquire_slot(timeout: float = 15.0) -> bool:
    return _global_lock.acquire(timeout=timeout)


def release_slot() -> None:
    _global_lock.release()
