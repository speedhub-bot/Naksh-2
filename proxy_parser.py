import re

def parse_proxy(proxy_str):
    """
    Parses a proxy string into a dictionary compatible with requests.
    Supports 15+ formats by handling various delimiters and credential placements.
    """
    proxy_str = proxy_str.strip()
    if not proxy_str:
        return None

    # Common separators: :, |, @, whitespace
    # Patterns to match:
    # 1. ip:port
    # 2. ip:port:user:pass
    # 3. user:pass:ip:port
    # 4. user:pass@ip:port
    # 5. scheme://ip:port
    # 6. scheme://user:pass@ip:port
    # 7. ip|port|user|pass etc.

    # Remove scheme if present and detect it
    scheme = "http"
    if "://" in proxy_str:
        scheme_part, proxy_str = proxy_str.split("://", 1)
        if "socks5" in scheme_part.lower():
            scheme = "socks5"
        elif "socks4" in scheme_part.lower():
            scheme = "socks4"
        elif "https" in scheme_part.lower():
            scheme = "https"

    # Replace all common separators with a single one (colon)
    # But be careful with @ if it's user:pass@ip:port
    if "@" in proxy_str:
        parts = proxy_str.split("@")
        if len(parts) == 2:
            creds_part = parts[0]
            addr_part = parts[1]
            creds = re.split(r'[:| ]', creds_part)
            addr = re.split(r'[:| ]', addr_part)
            if len(creds) == 2 and len(addr) == 2:
                return {
                    "http": f"{scheme}://{creds[0]}:{creds[1]}@{addr[0]}:{addr[1]}",
                    "https": f"{scheme}://{creds[0]}:{creds[1]}@{addr[0]}:{addr[1]}"
                }

    # Standardize delimiters
    normalized = re.split(r'[:|@ ]', proxy_str)
    normalized = [p for p in normalized if p]

    if len(normalized) == 2:
        # ip, port
        return {
            "http": f"{scheme}://{normalized[0]}:{normalized[1]}",
            "https": f"{scheme}://{normalized[0]}:{normalized[1]}"
        }
    elif len(normalized) == 4:
        # Check if first two are likely IP/Port or User/Pass
        # Simple heuristic: if the second part is all digits, it's likely port
        if normalized[1].isdigit() and not normalized[3].isdigit():
            # ip:port:user:pass
            return {
                "http": f"{scheme}://{normalized[2]}:{normalized[3]}@{normalized[0]}:{normalized[1]}",
                "https": f"{scheme}://{normalized[2]}:{normalized[3]}@{normalized[0]}:{normalized[1]}"
            }
        elif normalized[3].isdigit() and not normalized[1].isdigit():
            # user:pass:ip:port
            return {
                "http": f"{scheme}://{normalized[0]}:{normalized[1]}@{normalized[2]}:{normalized[3]}",
                "https": f"{scheme}://{normalized[0]}:{normalized[1]}@{normalized[2]}:{normalized[3]}"
            }
        else:
            # Fallback to ip:port:user:pass if ambiguous
            return {
                "http": f"{scheme}://{normalized[2]}:{normalized[3]}@{normalized[0]}:{normalized[1]}",
                "https": f"{scheme}://{normalized[2]}:{normalized[3]}@{normalized[0]}:{normalized[1]}"
            }

    return None

def test_parser():
    test_cases = [
        "1.1.1.1:8080",
        "1.1.1.1|8080",
        "1.1.1.1:8080:user:pass",
        "user:pass:1.1.1.1:8080",
        "user:pass@1.1.1.1:8080",
        "http://1.1.1.1:8080",
        "socks5://user:pass@1.1.1.1:8080",
        "1.1.1.1 8080",
        "user|pass|1.1.1.1|8080",
        "1.1.1.1:8080|user|pass",
        "socks4://1.1.1.1:8080",
        "https://user:pass:1.1.1.1:8080",
    ]
    for case in test_cases:
        print(f"{case} -> {parse_proxy(case)}")

if __name__ == "__main__":
    test_parser()
