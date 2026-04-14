import re
import concurrent.futures
import requests

_DECORATIVE_SYMBOLS_RE = re.compile('[✪✿✦⚚➎★☆◆◇■□●○◎☀☁☂☃☄☾☽♛♕♚♔♤♡♢♧♠♥♦♣⚜⚡✨❖⬥⬦⬧⬨⬩⭐🌟🟊]+')

HYPIXEL_NAME = re.compile(r'(?<=content="Plancke" /><meta property="og:locale" content="en_US" /><meta property="og:description" content=").+?(?=")', re.S)
HYPIXEL_TITLE = re.compile(r'<title>(.+?)\s*\|\s*Plancke</title>', re.IGNORECASE)
HYPIXEL_LEVEL = re.compile(r'(?<=Level:</b> ).+?(?=<br/><b>)')
FIRST_LOGIN = re.compile(r'(?<=<b>First login: </b>).+?(?=<br/><b>)')
LAST_LOGIN = re.compile(r'(?<=<b>Last login: </b>).+?(?=<br/>)')
BW_STARS = re.compile(r'(?<=<li><b>Level:</b> ).+?(?=</li>)')
SB_NETWORTH = re.compile(r'(?<= Networth: ).+?(?=\\n)')


def clean_name(name):
    if not name:
        return ''
    return _DECORATIVE_SYMBOLS_RE.sub('', str(name)).strip()


def _clean_name_internal(name):
    if not name:
        return ''
    cleaned = _DECORATIVE_SYMBOLS_RE.sub('', str(name)).strip()
    cleaned = re.sub('apis', '', cleaned, flags=re.IGNORECASE).strip()
    return cleaned


def _format_coins(num):
    if not isinstance(num, (int, float)):
        return '0'
    num = float(num)
    abs_num = abs(num)
    if abs_num >= 1_000_000_000_000_000:
        return f'{num / 1_000_000_000_000_000:.1f}Q'
    if abs_num >= 1_000_000_000_000:
        return f'{num / 1_000_000_000_000:.1f}T'
    if abs_num >= 1_000_000_000:
        return f'{num / 1_000_000_000:.1f}B'
    if abs_num >= 1_000_000:
        return f'{num / 1_000_000:.1f}M'
    if abs_num >= 1_000:
        return f'{num / 1_000:.0f}K'
    return str(int(num))


def _get_skill_average(member):
    skills = member.get('skills', {})
    total_level = 0
    skill_count = 0
    skill_names = ['alchemy', 'carpentry', 'combat', 'enchanting', 'farming', 'fishing', 'foraging', 'mining', 'taming']
    for name in skill_names:
        skill_data = skills.get(name)
        if skill_data and 'levelWithProgress' in skill_data:
            total_level += skill_data['levelWithProgress']
            skill_count += 1
    return total_level / skill_count if skill_count > 0 else 0


def fetch_hypixel_stats(username, uuid=None, timeout=10):
    try:
        timeout_val = int(timeout)
        player_url = f'https://api.soopy.dev/player/{username}'
        p_data = None
        s_data = None

        if uuid:
            clean_uuid = uuid.replace('-', '')
            skyblock_url = f'https://soopy.dev/api/v2/player_skyblock/{clean_uuid}?networth=true'
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                f1 = executor.submit(requests.get, player_url, timeout=timeout_val)
                f2 = executor.submit(requests.get, skyblock_url, timeout=timeout_val)
                try:
                    resp1 = f1.result()
                    if resp1.status_code == 200:
                        p_data = resp1.json()
                except:
                    pass
                try:
                    resp2 = f2.result()
                    if resp2.status_code == 200:
                        s_data = resp2.json()
                except:
                    pass
        else:
            p = requests.get(player_url, timeout=timeout_val).json()
            if p.get('success') and 'data' in p:
                p_data = p
                fetched_uuid = p['data'].get('uuid', '').replace('-', '')
                if fetched_uuid:
                    skyblock_url = f'https://soopy.dev/api/v2/player_skyblock/{fetched_uuid}?networth=true'
                    s = requests.get(skyblock_url, timeout=timeout_val).json()
                    s_data = s

        if not p_data or not p_data.get('success') or 'data' not in p_data:
            return None

        data = p_data['data']
        final_uuid = uuid.replace('-', '') if uuid else data.get('uuid', '').replace('-', '')
        ach = data.get('achievements', {})
        skywars_stars = ach.get('skywars_you_re_a_star', 0)
        arcade_coins = ach.get('arcade_arcade_banker', 0)
        bedwars_stars = ach.get('bedwars_level', 0)
        uhc_bounty = ach.get('uhc_bounty', 0)
        pit_gold = ach.get('pit_gold', 0)

        s = s_data if s_data else {}
        best_member = None
        max_score = -1
        profiles_data = s.get('data', {}).get('profiles', {})

        for profile_id, profile in profiles_data.items():
            members = profile.get('members', {})
            member = members.get(final_uuid)
            if member:
                nw_detailed = member.get('nwDetailed', {})
                networth = nw_detailed.get('networth', 0) if nw_detailed else 0
                skill_avg = _get_skill_average(member)
                sb_lvl = member.get('skyblock_level', 0)
                score = networth / 1_000_000 * 100 + skill_avg * 100 + sb_lvl * 10
                if score > max_score:
                    max_score = score
                    best_member = member

        coins = kills = fairy = networth = sb_lvl = 0
        avg_skill_level = 0.0
        item_list_str = ''

        if best_member:
            coins = best_member.get('coin_purse', 0)
            kills = best_member.get('kills', {}).get('total', 0)
            fairy = best_member.get('fairy_souls_collected', 0)
            sb_lvl = best_member.get('skyblock_level', 0)
            nw_detailed = best_member.get('nwDetailed', {})
            networth = nw_detailed.get('networth', 0) if nw_detailed else 0
            types = nw_detailed.get('types', {}) if nw_detailed else {}
            if networth == 0 and coins > 0:
                networth = coins
            avg_skill_level = _get_skill_average(best_member)

            def collect_items(category_data):
                items_list = []
                if category_data and category_data.get('items'):
                    for i in category_data['items']:
                        c = _clean_name_internal(i.get('name'))
                        if c:
                            items_list.append(c)
                return items_list

            all_valid_items = []
            for cat in ['armor', 'equipment', 'wardrobe', 'weapons', 'inventory']:
                all_valid_items.extend(collect_items(types.get(cat)))

            MAX_SHOWN_ITEMS = 5
            if len(all_valid_items) > MAX_SHOWN_ITEMS:
                shown_items = ', '.join(all_valid_items[:MAX_SHOWN_ITEMS])
                remaining = len(all_valid_items) - MAX_SHOWN_ITEMS
                item_list_str = f'{shown_items}, +{remaining} more'
            else:
                item_list_str = ', '.join(all_valid_items)

        parts = []
        if networth > 0:
            parts.append(f'NW: {_format_coins(networth)}')
        if coins > 0:
            parts.append(f'Purse: {_format_coins(coins)}')
        if avg_skill_level > 0:
            parts.append(f'Avg_Skill: {avg_skill_level:.2f}')
        if skywars_stars > 0:
            parts.append(f'SW: {skywars_stars}')
        if bedwars_stars > 0:
            parts.append(f'BW: {bedwars_stars}')
        if pit_gold > 0:
            parts.append(f'Pit_Gold: {_format_coins(pit_gold)}')
        if uhc_bounty > 0:
            parts.append(f'UHC_Bounty: {_format_coins(uhc_bounty)}')
        if sb_lvl > 0:
            parts.append(f'Sb_Lvl: {sb_lvl}')
        if arcade_coins > 0:
            parts.append(f'Arcade_Coins: {_format_coins(arcade_coins)}')
        if kills > 0:
            parts.append(f'Sb_Kills: {kills}')
        if fairy > 0:
            parts.append(f'Sb_Fairy_Souls: {fairy}')
        if item_list_str:
            parts.append(f'Sb_Valuable_Items: {item_list_str}')

        return ' '.join(parts) if parts else None
    except Exception:
        return None


def fetch_plancke_stats(session, username, config, getproxy, is_no_proxy):
    result = {
        'hypixl': None,
        'level': None,
        'firstlogin': None,
        'lastlogin': None,
        'bwstars': None,
    }
    try:
        proxy_to_use = getproxy() if not is_no_proxy() else None
        resp = session.get(
            'https://plancke.io/hypixel/player/stats/' + username,
            proxies=proxy_to_use,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0',
                'Accept-Encoding': 'gzip, deflate'
            },
            verify=False,
            timeout=(5, 8)
        )
        tx = resp.text
    except Exception:
        return result

    if config.get('hypixelname'):
        try:
            match = HYPIXEL_NAME.search(tx)
            if match:
                result['hypixl'] = match.group()
                match_title = HYPIXEL_TITLE.search(tx)
                if match_title:
                    result['hypixl'] = match_title.group(1)
                else:
                    try:
                        pattern = r'\[(VIP\+?|MVP\+\+?|YOUTUBE|ADMIN|MOD|HELPER)\]\s*' + re.escape(username)
                        match_brute = re.search(pattern, tx, re.IGNORECASE)
                        if match_brute:
                            result['hypixl'] = match_brute.group(0)
                    except:
                        pass
        except:
            pass

    if config.get('hypixellevel'):
        try:
            match = HYPIXEL_LEVEL.search(tx)
            if match:
                result['level'] = match.group()
        except:
            pass

    if config.get('hypixelfirstlogin'):
        try:
            match = FIRST_LOGIN.search(tx)
            if match:
                result['firstlogin'] = match.group()
        except:
            pass

    if config.get('hypixellastlogin'):
        try:
            match = LAST_LOGIN.search(tx)
            if match:
                result['lastlogin'] = match.group()
        except:
            pass

    if config.get('hypixelbwstars'):
        try:
            match = BW_STARS.search(tx)
            if match:
                result['bwstars'] = match.group()
        except:
            pass

    return result
