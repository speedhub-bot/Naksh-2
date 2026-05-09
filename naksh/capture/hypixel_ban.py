"""Lightweight Hypixel ban check via the Minecraft protocol.

We perform a real login handshake to ``mc.hypixel.net:25565`` and read back
the first packet the server sends in the Login state. If the server replies
with a Disconnect (packet id ``0x00``) and the JSON reason contains the words
``ban``, ``permanent``, ``ipban``, ``security alert``, ``temporary ban`` etc,
the account is considered banned.

If the server replies with an Encryption Request (``0x01``) the account is
*not* banned at the IP/UUID level — Hypixel is willing to negotiate auth.
We never actually complete the encryption step; we close the socket.

This is intentionally a self-contained module — no pyCraft, no extra deps,
just stdlib socket+struct+json. Concurrency-limited at the call site to
avoid Hypixel IP-banning the bot.
"""

from __future__ import annotations

import json
import logging
import socket
import struct
import threading
from typing import Optional

log = logging.getLogger(__name__)

HOST = "mc.hypixel.net"
PORT = 25565
PROTOCOL = 47          # 1.8 — accepted everywhere on Hypixel
CONNECT_TIMEOUT = 6.0  # seconds
READ_TIMEOUT = 8.0

BAN_KEYWORDS = (
    "you are temporarily banned",
    "you are permanently banned",
    "you are banned",
    "your account has been banned",
    "permanently banned",
    "banned from this server",
    "banned for",
    "ipban",
    "ip-ban",
    "security alert",
)

_global_lock = threading.Semaphore(2)  # at most 2 concurrent connections


def _write_varint(value: int) -> bytes:
    out = b""
    while True:
        temp = value & 0x7F
        value >>= 7
        if value:
            temp |= 0x80
        out += struct.pack("B", temp)
        if not value:
            return out


def _read_varint(sock: socket.socket) -> int:
    num = 0
    for i in range(5):
        b = sock.recv(1)
        if not b:
            raise ConnectionError("connection closed mid-varint")
        byte = b[0]
        num |= (byte & 0x7F) << (7 * i)
        if not (byte & 0x80):
            return num
    raise ValueError("varint too long")


def _read_exact(sock: socket.socket, n: int) -> bytes:
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("connection closed mid-payload")
        buf += chunk
    return buf


def _build_handshake(host: str, port: int, next_state: int = 2) -> bytes:
    host_bytes = host.encode("utf-8")
    payload = (
        _write_varint(0x00)             # packet id 0x00 — Handshake
        + _write_varint(PROTOCOL)
        + _write_varint(len(host_bytes)) + host_bytes
        + struct.pack(">H", port)
        + _write_varint(next_state)     # 1 = status, 2 = login
    )
    return _write_varint(len(payload)) + payload


def _build_login_start(username: str) -> bytes:
    name = username.encode("utf-8")
    payload = (
        _write_varint(0x00)             # packet id 0x00 — LoginStart
        + _write_varint(len(name)) + name
    )
    return _write_varint(len(payload)) + payload


def check_hypixel_ban(
    username: str, *, host: str = HOST, port: int = PORT,
) -> Optional[bool]:
    """Return ``True`` if banned, ``False`` if not, ``None`` if undetermined.

    A return value of ``None`` means we couldn't reach the server, the protocol
    drifted, or the response didn't fit any known shape. Treat it as
    "unknown" — never as "banned".
    """
    if not username or username == "N/A":
        return None
    if not _global_lock.acquire(timeout=10):
        log.debug("hypixel ban check semaphore timeout for %s", username)
        return None
    try:
        with socket.create_connection((host, port), timeout=CONNECT_TIMEOUT) as sock:
            sock.settimeout(READ_TIMEOUT)
            sock.sendall(_build_handshake(host, port, next_state=2))
            sock.sendall(_build_login_start(username))

            packet_len = _read_varint(sock)
            data = _read_exact(sock, packet_len)
            # data[0] = packet id varint (single byte for ids < 128)
            packet_id = data[0]
            body = data[1:]

            if packet_id == 0x00:
                # Disconnect (Login state) — body is a JSON string prefixed with
                # a varint length. Parse it.
                # Read varint manually from `body`.
                idx = 0
                length = 0
                shift = 0
                while idx < len(body):
                    b = body[idx]
                    idx += 1
                    length |= (b & 0x7F) << shift
                    if not (b & 0x80):
                        break
                    shift += 7
                reason_bytes = body[idx:idx + length]
                try:
                    reason_json = reason_bytes.decode("utf-8", errors="ignore")
                    reason_obj = json.loads(reason_json)
                    text = _flatten_chat_component(reason_obj).lower()
                except Exception:
                    text = reason_bytes.decode("utf-8", errors="ignore").lower()
                log.debug("hypixel ban check %s -> disconnect: %s", username, text[:200])
                return any(kw in text for kw in BAN_KEYWORDS)

            if packet_id == 0x01:
                # Encryption Request — server is willing to authenticate, so
                # the account is not pre-banned at the connection layer.
                return False

            log.debug("hypixel ban check %s -> unknown packet id %s",
                      username, packet_id)
            return None
    except (socket.timeout, OSError, ConnectionError, ValueError) as e:
        log.debug("hypixel ban check error for %s: %s", username, e)
        return None
    finally:
        _global_lock.release()


def _flatten_chat_component(obj) -> str:
    """Hypixel disconnect reasons are JSON chat components — flatten to text."""
    if isinstance(obj, str):
        return obj
    if isinstance(obj, list):
        return " ".join(_flatten_chat_component(o) for o in obj)
    if isinstance(obj, dict):
        out = ""
        if "text" in obj:
            out += str(obj["text"])
        if "extra" in obj:
            out += _flatten_chat_component(obj["extra"])
        if "translate" in obj:
            out += " " + str(obj["translate"])
        if "with" in obj:
            out += " " + _flatten_chat_component(obj["with"])
        return out
    return ""
