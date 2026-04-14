import re
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

DONUT_API_URL = 'https://api.donutsmp.net/v1/player/'


def _format_seconds(seconds_value):
    try:
        total_seconds = int(seconds_value)
    except Exception:
        return str(seconds_value)
    if total_seconds < 0:
        total_seconds = 0
    days, rem = divmod(total_seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, seconds = divmod(rem, 60)
    parts = []
    if days:
        parts.append(f'{days}d')
    if hours:
        parts.append(f'{hours}h')
    if minutes:
        parts.append(f'{minutes}m')
    if not parts:
        parts.append(f'{seconds}s')
    return ' '.join(parts)


def _duration_to_days(text):
    if not text:
        return None
    try:
        text_lower = text.lower()
        total_days = 0
        for match in re.findall(r'(\d+)\s*(?:day|days|d)\b', text_lower):
            total_days += int(match)
        for match in re.findall(r'(\d+)\s*(?:week|weeks|w)\b', text_lower):
            total_days += int(match) * 7
        for match in re.findall(r'(\d+)\s*(?:month|months|mo|m)\b', text_lower):
            total_days += int(match) * 30
        for match in re.findall(r'(\d+)\s*(?:year|years|y)\b', text_lower):
            total_days += int(match) * 365
        if total_days == 0:
            hour_matches = re.findall(r'(\d+)\s*(?:hour|hours|h)\b', text_lower)
            if hour_matches:
                hours = sum(int(h) for h in hour_matches)
                total_days = max(1, (hours + 23) // 24)
        return total_days if total_days > 0 else None
    except:
        return None


def _format_duration_short(original_text, total_days):
    try:
        text_lower = original_text.lower()
        hour_matches = re.findall(r'(\d+)\s*(?:hour|hours|h)\b', text_lower)
        if hour_matches and 'day' not in text_lower and 'week' not in text_lower and 'month' not in text_lower:
            return f'{sum(int(h) for h in hour_matches)}h'
        week_matches = re.findall(r'(\d+)\s*(?:week|weeks|w)\b', text_lower)
        if week_matches and 'day' not in text_lower and 'month' not in text_lower:
            return f'{sum(int(w) for w in week_matches)}w'
        month_matches = re.findall(r'(\d+)\s*(?:month|months|mo|m)\b', text_lower)
        if month_matches and 'week' not in text_lower and 'day' not in text_lower:
            total_months = sum(int(m) for m in month_matches)
            return '4w' if total_months == 1 else f'{total_months * 30}d'
        return f'{total_days}d'
    except:
        return original_text


def _parse_ban_info(ban_text):
    ban_info = {}
    if not ban_text or not isinstance(ban_text, str):
        return ban_info
    ban_id_match = re.search(r'Ban ID: ([A-Za-z0-9]+)', ban_text)
    if ban_id_match:
        ban_info['ban_id'] = ban_id_match.group(1)
    if 'Permanently' in ban_text or 'permanently' in ban_text:
        ban_info['duration'] = 'Permanently'
        ban_info['ban_days'] = None
    else:
        duration_match = re.search(r'\[([^\]]+)\]', ban_text)
        if duration_match:
            duration_text = duration_match.group(1)
            if 'Permanently' not in duration_text and 'permanently' not in duration_text:
                ban_days = _duration_to_days(duration_text)
                if ban_days is not None:
                    ban_info['ban_days'] = ban_days
                    ban_info['duration'] = _format_duration_short(duration_text, ban_days)
                else:
                    ban_info['duration'] = duration_text
    if 'Suspicious activity' in ban_text:
        ban_info['reason'] = 'Suspicious activity'
    ban_info['full_message'] = ban_text
    return ban_info


def fetch_donut_stats(username, email, password, banned, fname, file_lock,
                      config, getproxy, proxytype,
                      UI_ENABLED=False, ui=None,
                      donut_api_url=DONUT_API_URL):
    if not config.get('donut_stats', True):
        return
    if not username or username == 'N/A':
        if UI_ENABLED and ui:
            ui.log_info('Donut SMP: skipped (username unavailable)')
        return

    try:
        donut_api_key = config.get('donut_api_key')
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json'
        }
        if donut_api_key:
            headers['Authorization'] = f'Bearer {donut_api_key}'

        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.75,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=['GET'],
            respect_retry_after_header=True,
            raise_on_status=False
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount('https://', adapter)
        session.mount('http://', adapter)

        proxy_candidates = []
        if proxytype != "'4'":
            try:
                for _ in range(4):
                    p = getproxy()
                    if p:
                        proxy_candidates.append(p)
            except Exception:
                pass

        seen = set()
        unique = []
        for p in proxy_candidates:
            key = str(p)
            if key not in seen:
                seen.add(key)
                unique.append(p)
        proxy_candidates = unique + [None]

        valid_proxies = []
        for p in proxy_candidates:
            try:
                r = session.get('https://api.donutsmp.net/index.html', headers=headers, proxies=p, verify=False, timeout=10)
                if r.status_code == 200:
                    valid_proxies.append(p)
                elif UI_ENABLED and ui:
                    ui.log_info(f"Donut SMP: preflight {r.status_code}{' (no proxy)' if p is None else ''}")
            except Exception as e:
                if UI_ENABLED and ui:
                    ui.log_info(f"Donut SMP: preflight failed {'(no proxy)' if p is None else ''} - {e.__class__.__name__}: {str(e)[:160]}")

        if not valid_proxies:
            valid_proxies = [None]

        response = None
        for idx, p in enumerate(valid_proxies):
            try:
                r = session.get(f'{donut_api_url}{username}', headers=headers, proxies=p, verify=False, timeout=20)
                time.sleep(0.3 * (idx + 1))
                if r.status_code == 200 or r.status_code in (401, 404, 429):
                    response = r
                    break
                else:
                    if UI_ENABLED and ui:
                        ui.log_info(f"Donut SMP: server error {r.status_code} on attempt {idx + 1}{' (no proxy)' if p is None else ''}")
                    continue
            except (
                requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
                requests.exceptions.RetryError,
                requests.exceptions.ProxyError,
                requests.exceptions.SSLError,
                requests.exceptions.InvalidSchema
            ) as e:
                if UI_ENABLED and ui:
                    ui.log_info(f"Donut SMP: connection failed on attempt {idx + 1}{' (no proxy)' if p is None else ''} - {e.__class__.__name__}: {str(e)[:160]}")
                continue

        if response is None:
            if UI_ENABLED and ui:
                ui.log_info('Donut SMP API: Connection failed after retries')
            return

        if response.status_code == 200:
            try:
                data = response.json()
            except Exception:
                data = None

            stats_data = None
            if isinstance(data, dict) and 'result' in data and isinstance(data['result'], dict):
                stats_data = data['result']

            if isinstance(stats_data, dict):
                stats_lines = [
                    f'{email}:{password}',
                    f'Username: {username}',
                ]

                if stats_data.get('broken_blocks'):
                    stats_lines.append(f"broken_blocks: {stats_data['broken_blocks']}")
                if stats_data.get('deaths'):
                    stats_lines.append(f"deaths: {stats_data['deaths']}")
                if stats_data.get('kills'):
                    stats_lines.append(f"kills: {stats_data['kills']}")
                if stats_data.get('mobs_killed'):
                    stats_lines.append(f"mobs_killed: {stats_data['mobs_killed']}")
                if stats_data.get('money'):
                    stats_lines.append(f"money: {stats_data['money']}")
                if stats_data.get('money_made_from_sell'):
                    stats_lines.append(f"money_made_from_sell: {stats_data['money_made_from_sell']}")
                if stats_data.get('money_spent_on_shop'):
                    stats_lines.append(f"money_spent_on_shop: {stats_data['money_spent_on_shop']}")
                if stats_data.get('placed_blocks'):
                    stats_lines.append(f"placed_blocks: {stats_data['placed_blocks']}")
                if stats_data.get('playtime'):
                    try:
                        raw_playtime = stats_data['playtime']
                        stats_lines.append(f'playtime: {raw_playtime} ({_format_seconds(raw_playtime)})')
                    except Exception:
                        stats_lines.append(f"playtime: {stats_data['playtime']}")

                if banned is not None:
                    if banned and banned != 'False':
                        stats_lines.append('banned: true')
                        if banned not in ('True', 'true', True):
                            ban_info = _parse_ban_info(banned)
                            if ban_info.get('ban_id'):
                                stats_lines.append(f"ban_id: {ban_info['ban_id']}")
                            if ban_info.get('duration'):
                                stats_lines.append(f"ban_duration: {ban_info['duration']}")
                        else:
                            stats_lines.append('ban_duration: Unknown')
                    else:
                        stats_lines.append('banned: false')

                if len(stats_lines) > 2:
                    with file_lock:
                        with open(f'results/{fname}/donut_stats.txt', 'a', encoding='utf-8') as f:
                            f.write('\n'.join(stats_lines))
                            f.write('\n' + '=' * 50 + '\n')
                    if UI_ENABLED and ui:
                        ui.log_info(f'Donut SMP stats saved for {username}')

        elif response.status_code == 404:
            if UI_ENABLED and ui:
                ui.log_info('Donut SMP: player not found')
        elif response.status_code == 401:
            if UI_ENABLED and ui:
                ui.log_info('Donut SMP API: Invalid API key')
        elif response.status_code == 429:
            if UI_ENABLED and ui:
                ui.log_info('Donut SMP API: Rate limited')

    except requests.exceptions.RequestException as e:
        if UI_ENABLED and ui:
            if 'Max retries exceeded' in str(e):
                ui.log_info('Donut SMP API: Connection failed after retries')
            elif 'Connection' in str(e) or 'Timeout' in str(e):
                ui.log_info('Donut SMP API: Connection timeout')
            else:
                ui.log_info('Donut SMP API: Request failed')
    except Exception as e:
        if UI_ENABLED and ui:
            ui.log_info(f'Donut SMP error: {str(e)[:100]}')
