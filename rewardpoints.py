import re
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


def check_rewards_points(session, config, token_cache=None):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Pragma': 'no-cache',
            'Accept': '*/*'
        }
        r = session.get('https://rewards.bing.com/', headers=headers, timeout=int(config.get('timeout', 10)))
        if 'action="https://rewards.bing.com/signin-oidc"' in r.text or 'id="fmHF"' in r.text:
            action_match = re.search('action="([^"]+)"', r.text)
            if action_match:
                action_url = action_match.group(1)
                data = {}
                for input_match in re.finditer('<input type="hidden" name="([^"]+)" id="[^"]+" value="([^"]+)">', r.text):
                    data[input_match.group(1)] = input_match.group(2)
                r = session.post(action_url, data=data, headers=headers, timeout=int(config.get('timeout', 10)))

        all_matches = re.findall(r',"availablePoints":(\d+)', r.text)
        if all_matches:
            points = max(all_matches, key=int)
            if points != '0':
                return points

        headers_home = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://www.bing.com/',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8'
        }
        session.get('https://www.bing.com/', headers=headers_home, timeout=15)

        ts = int(time.time() * 1000)
        flyout_url = f'https://www.bing.com/rewards/panelflyout/getuserinfo?timestamp={ts}'
        headers_flyout = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json',
            'Accept-Encoding': 'identity',
            'Referer': 'https://www.bing.com/',
            'X-Requested-With': 'XMLHttpRequest'
        }
        r_flyout = session.get(flyout_url, headers=headers_flyout, timeout=15)
        if r_flyout.status_code == 200:
            try:
                data = r_flyout.json()
                if data.get('userInfo', {}).get('isRewardsUser'):
                    balance = data.get('userInfo', {}).get('balance')
                    return str(balance)
            except ValueError:
                pass
        return None
    except Exception:
        return None


def fetch_rewards(session, email, password, config, fname, write_dedupe, token_cache=None):
    if not config.get('check_rewards_points', True):
        return None
    points = check_rewards_points(session, config, token_cache)
    if points:
        write_dedupe(fname, 'Ms_Points.txt', f'{email}:{password} | Points: {points}\n')
        return points
    return None
