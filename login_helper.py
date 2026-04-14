import re
import requests
import time
from urllib.parse import urlparse, parse_qs

# Regexes from various checker implementations
RE_SFTTAG_VALUE = re.compile(r'value="([^"]+)" name="PPFT"')
RE_SFTTAG_VALUE_ALT = re.compile(r'sFTTag":"<input type=\\"hidden\\" name=\\"PPFT\\" id=\\"[^\\"]+\\" value=\\"([^\\"]+)\\"')
RE_URLPOST_VALUE = re.compile(r"urlPost:'([^']+)'")
RE_URLPOST_VALUE_ALT = re.compile(r'urlPost":"([^"]+)"')
RE_IPT = re.compile(r'ipt: "([^"]+)"')
RE_PPRID = re.compile(r'pprid: "([^"]+)"')
RE_UAID = re.compile(r'uaid: "([^"]+)"')
RE_ACTION_FMHF = re.compile(r'action="([^"]+)"')
RE_RETURN_URL = re.compile(r'window.location.replace\("([^"]+)"\)')

def microsoft_login(session, email, password):
    """
    Performs Microsoft Login and returns (token, xbox_token).
    Returns ("2FA", None) if 2FA is encountered.
    Returns (None, None) if login fails.
    """
    try:
        # Step 1: Get PPFT and urlPost
        sFTTag_url = (
            "https://login.live.com/oauth20_authorize.srf"
            "?client_id=00000000402b5328&response_type=token"
            "&scope=service::user.auth.xboxlive.com::MBI_SSL&redirect_uri=https://login.live.com/oauth20_desktop.srf"
        )
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        }

        resp = session.get(sFTTag_url, headers=headers, timeout=10)

        sft_match = RE_SFTTAG_VALUE.search(resp.text)
        if not sft_match:
            sft_match = RE_SFTTAG_VALUE_ALT.search(resp.text)

        url_match = RE_URLPOST_VALUE.search(resp.text)
        if not url_match:
            url_match = RE_URLPOST_VALUE_ALT.search(resp.text)

        if not sft_match or not url_match:
            return None, None

        sFTTag = sft_match.group(1)
        urlPost = url_match.group(1).replace('&amp;', '&')

        # Step 2: Submit Credentials
        data = {
            'login': email,
            'loginfmt': email,
            'passwd': password,
            'PPFT': sFTTag
        }

        login_resp = session.post(urlPost, data=data, headers=headers, allow_redirects=True, timeout=10)

        if '#' in login_resp.url:
            token = parse_qs(urlparse(login_resp.url).fragment).get('access_token', [None])[0]
        else:
            # Check for 2FA or errors
            if any(v in login_resp.text for v in ['recover?mkt', 'identity/confirm', 'Email/Confirm', '/Abuse?mkt=']):
                return "2FA", None
            return None, None

        if not token:
            return None, None

        # Step 3: Exchange for XBL Token
        xbl_resp = session.post(
            'https://user.auth.xboxlive.com/user/authenticate',
            json={
                'Properties': {
                    'AuthMethod': 'RPS',
                    'SiteName': 'user.auth.xboxlive.com',
                    'RpsTicket': f'd={token}'
                },
                'RelyingParty': 'http://auth.xboxlive.com/',
                'TokenType': 'JWT'
            },
            headers={'Content-Type': 'application/json', 'Accept': 'application/json'}
        )

        if xbl_resp.status_code != 200:
            return token, None

        xbl_data = xbl_resp.json()
        xbl_token = xbl_data.get('Token')
        uhs = xbl_data.get('DisplayClaims', {}).get('xui', [{}])[0].get('uhs')

        # Step 4: Exchange for XSTS Token
        xsts_resp = session.post(
            'https://xsts.auth.xboxlive.com/xsts/authorize',
            json={
                'Properties': {
                    'SandboxId': 'RETAIL',
                    'UserTokens': [xbl_token]
                },
                'RelyingParty': 'rp://api.minecraftservices.com/',
                'TokenType': 'JWT'
            },
            headers={'Content-Type': 'application/json', 'Accept': 'application/json'}
        )

        if xsts_resp.status_code != 200:
            return token, None

        xsts_data = xsts_resp.json()
        xsts_token = xsts_data.get('Token')

        # Step 5: Get Minecraft Token
        mc_resp = session.post(
            'https://api.minecraftservices.com/authentication/login_with_xbox',
            json={
                'identityToken': f'XBL3.0 x={uhs};{xsts_token}'
            }
        )

        if mc_resp.status_code != 200:
            return token, None

        final_token = mc_resp.json().get('access_token')
        return final_token, xbl_token

    except Exception:
        return None, None
