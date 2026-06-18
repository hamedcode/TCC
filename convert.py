import base64
import re
import sys
from urllib.parse import urlparse, parse_qs, unquote
import requests
import yaml

SOURCE_URL = "https://raw.githubusercontent.com/hamedcode/TCC/main/sent_configs.txt"
OUTPUT_FILE = "clash.yml"

# ─── Constants ───────────────────────────────────────────────────────────────

VALID_SS_CIPHERS = {
    'aes-128-gcm', 'aes-256-gcm',
    'chacha20-ietf-poly1305',
    'aes-128-cfb', 'aes-192-cfb', 'aes-256-cfb',
    'aes-128-ctr', 'aes-192-ctr', 'aes-256-ctr',
    'rc4-md5', 'xchacha20-ietf-poly1305',
    '2022-blake3-aes-128-gcm', '2022-blake3-aes-256-gcm',
    '2022-blake3-chacha20-poly1305',
}

VALID_FINGERPRINTS = {
    'chrome', 'firefox', 'safari', 'ios', 'android',
    'edge', 'qq', 'random', 'randomized',
}

VALID_NETWORKS = {'ws', 'grpc', 'http', 'h2', 'tcp'}

VALID_FLOW = {'xtls-rprx-vision', 'xtls-rprx-vision-udp443', ''}

# ─── Helpers ─────────────────────────────────────────────────────────────────

def safe_b64decode(s):
    s = s.strip().replace('-', '+').replace('_', '/')
    pad = 4 - len(s) % 4
    if pad != 4:
        s += '=' * pad
    try:
        return base64.b64decode(s).decode('utf-8', errors='strict')
    except Exception:
        return None

def has_control_chars(s):
    return bool(re.search(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', str(s)))

def clean_name(raw):
    name = unquote(raw).strip()
    name = re.sub(r'[\x00-\x1f\x7f]', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name or 'proxy'

def make_unique_name(base, seen):
    if base not in seen:
        seen.add(base)
        return base
    i = 2
    while f"{base} {i}" in seen:
        i += 1
    name = f"{base} {i}"
    seen.add(name)
    return name

# ─── Clash Validators ─────────────────────────────────────────────────────────

def is_valid_hostname(h):
    if not h or len(h) > 253:
        return False
    return bool(re.match(
        r'^(\d{1,3}\.){3}\d{1,3}$'          # IPv4
        r'|^\[?[0-9a-fA-F:]+\]?$'            # IPv6
        r'|^[a-zA-Z0-9]([a-zA-Z0-9\-\.]*[a-zA-Z0-9])?$',  # domain
        h
    ))

def is_valid_port(p):
    try:
        return 1 <= int(p) <= 65535
    except Exception:
        return False

def is_valid_uuid(u):
    return bool(re.fullmatch(
        r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
        str(u), re.IGNORECASE
    ))

def is_valid_reality_pbk(pbk):
    # باید base64url معتبل، بدون فاصله، حداقل ۳۰ کاراکتر
    if not pbk or ' ' in pbk or len(pbk) < 30:
        return False
    return bool(re.fullmatch(r'[A-Za-z0-9+/=_\-]+', pbk))

def is_valid_reality_sid(sid):
    # خالی مجازه، وگرنه فقط hex، بدون فاصله، حداکثر ۱۶ کاراکتر
    if sid == '':
        return True
    return bool(re.fullmatch(r'[0-9a-fA-F]{1,16}', sid)) and ' ' not in sid

def fields_are_clean(proxy):
    def check(v):
        if isinstance(v, str):
            return not has_control_chars(v)
        if isinstance(v, dict):
            return all(check(x) for x in v.values())
        if isinstance(v, list):
            return all(check(x) for x in v)
        return True
    return all(check(v) for k, v in proxy.items() if k != 'name')

def validate(proxy):
    """
    بررسی کامل یک پروکسی با قوانین Clash/Mihomo.
    (True, 'ok') یا (False, 'دلیل') برمیگردونه.
    """
    ptype  = proxy.get('type', '')
    server = proxy.get('server', '')
    port   = proxy.get('port')

    if not is_valid_hostname(server):
        return False, f"bad server: {server!r}"
    if not is_valid_port(port):
        return False, f"bad port: {port!r}"

    if ptype == 'vless':
        if not is_valid_uuid(proxy.get('uuid', '')):
            return False, f"bad uuid"

        ro = proxy.get('reality-opts')
        if ro is not None:
            if not is_valid_reality_pbk(ro.get('public-key', '')):
                return False, f"bad reality public-key: {ro.get('public-key','')!r}"
            if not is_valid_reality_sid(ro.get('short-id', '')):
                return False, f"bad reality short-id: {ro.get('short-id','')!r}"

        flow = proxy.get('flow', '')
        if flow and flow not in VALID_FLOW:
            return False, f"bad flow: {flow!r}"

        fp = proxy.get('client-fingerprint', '')
        if fp and fp not in VALID_FINGERPRINTS:
            return False, f"bad fingerprint: {fp!r}"

        net = proxy.get('network', 'tcp')
        if net not in VALID_NETWORKS:
            return False, f"bad network: {net!r}"

    elif ptype == 'ss':
        cipher = proxy.get('cipher', '')
        if cipher not in VALID_SS_CIPHERS:
            return False, f"bad cipher: {cipher!r}"
        pw = proxy.get('password', '')
        if not pw or has_control_chars(pw):
            return False, "bad password"

    elif ptype == 'trojan':
        pw = proxy.get('password', '')
        if not pw or has_control_chars(pw):
            return False, "bad password"
        fp = proxy.get('client-fingerprint', '')
        if fp and fp not in VALID_FINGERPRINTS:
            return False, f"bad fingerprint: {fp!r}"
        net = proxy.get('network', 'tcp')
        if net and net not in VALID_NETWORKS:
            return False, f"bad network: {net!r}"

    else:
        return False, f"unknown type: {ptype!r}"

    if not fields_are_clean(proxy):
        return False, "control chars in fields"

    return True, "ok"

# ─── Parsers ──────────────────────────────────────────────────────────────────

def _frag(line, default):
    return (line.rsplit('#', 1) + [default])[:2] if '#' in line else (line, default)

def parse_vless(line, seen):
    try:
        uri, frag = _frag(line, 'vless')
        parsed = urlparse(uri)
        uuid   = parsed.username
        server = parsed.hostname
        port   = parsed.port or 443
        if not server or not uuid:
            return None

        params = parse_qs(parsed.query)
        def p(k, d=''):
            return params.get(k, [d])[0]

        security = p('security', 'none')
        net_type = p('type', 'tcp')

        proxy = {
            'name'  : make_unique_name(clean_name(frag), seen),
            'type'  : 'vless',
            'server': server,
            'port'  : port,
            'uuid'  : uuid,
            'udp'   : True,
        }

        if net_type == 'ws':
            proxy['network'] = 'ws'
            ws = {'path': unquote(p('path')) or '/'}
            if p('host'):
                ws['headers'] = {'Host': p('host')}
            proxy['ws-opts'] = ws

        elif net_type == 'grpc':
            proxy['network'] = 'grpc'
            svc = p('serviceName') or p('mode', '')
            if svc:
                proxy['grpc-opts'] = {'grpc-service-name': svc}

        elif net_type in ('tcp',) and p('headerType') == 'http':
            proxy['network'] = 'http'
            if p('host'):
                proxy['http-opts'] = {'headers': {'Host': [p('host')]}}

        elif net_type in ('xhttp', 'httpupgrade'):
            proxy['network'] = 'http'
            if p('host'):
                proxy['http-opts'] = {'headers': {'Host': [p('host')]}}

        if security == 'tls':
            proxy['tls'] = True
            if p('sni'):
                proxy['servername'] = p('sni')
            if p('fp'):
                proxy['client-fingerprint'] = p('fp')
            if p('alpn'):
                proxy['alpn'] = [a for a in p('alpn').split(',') if a]

        elif security == 'reality':
            pbk = p('pbk', '').strip()
            sid = p('sid', '').strip()
            # اگه reality نامعتبل بود اینجا رد کن (قبل از validate)
            if not is_valid_reality_pbk(pbk) or not is_valid_reality_sid(sid):
                return None
            proxy['tls'] = True
            proxy['reality-opts'] = {'public-key': pbk, 'short-id': sid}
            if p('sni'):
                proxy['servername'] = p('sni')
            if p('fp'):
                proxy['client-fingerprint'] = p('fp')
            if p('flow'):
                proxy['flow'] = p('flow')

        return proxy
    except Exception:
        return None

def parse_ss(line, seen):
    try:
        uri, frag = _frag(line, 'ss')
        rest   = uri[5:]
        at_idx = rest.rfind('@')
        if at_idx == -1:
            return None

        user_part = rest[:at_idx]
        host_part = rest[at_idx + 1:]
        host_port = host_part.split('?')[0]
        qs        = host_part.split('?')[1] if '?' in host_part else ''

        hp = host_port.rsplit(':', 1)
        if len(hp) != 2:
            return None
        server = hp[0].strip('[]')
        port   = int(hp[1])

        method = password = None

        if ':' in user_part:
            head, tail = user_part.split(':', 1)
            if head.lower() in VALID_SS_CIPHERS:
                method, password = head.lower(), tail
            else:
                decoded = safe_b64decode(head)
                if decoded and ':' in decoded:
                    m, pw = decoded.split(':', 1)
                    if m.lower() in VALID_SS_CIPHERS:
                        method   = m.lower()
                        password = pw + ':' + tail if tail else pw
        else:
            decoded = safe_b64decode(user_part)
            if decoded and ':' in decoded:
                m, pw = decoded.split(':', 1)
                if m.lower() in VALID_SS_CIPHERS:
                    method, password = m.lower(), pw

        if not method or method not in VALID_SS_CIPHERS:
            return None
        if not password or has_control_chars(password):
            return None

        params = parse_qs(qs) if qs else {}
        def p(k, d=''):
            return params.get(k, [d])[0]

        net_type = p('type', 'tcp')
        security = p('security', 'none')

        proxy = {
            'name'    : make_unique_name(clean_name(frag), seen),
            'type'    : 'ss',
            'server'  : server,
            'port'    : port,
            'cipher'  : method,
            'password': password,
            'udp'     : True,
        }

        if net_type == 'ws':
            opts = {
                'mode': 'websocket',
                'path': unquote(p('path', '/')),
            }
            host = p('host', '')
            if host:
                opts['headers'] = {'Host': host}
            if security == 'tls':
                opts['tls'] = True
                opts['skip-cert-verify'] = False
            proxy['plugin']      = 'v2ray-plugin'
            proxy['plugin-opts'] = opts
        elif net_type == 'grpc':
            proxy['plugin']      = 'v2ray-plugin'
            proxy['plugin-opts'] = {'mode': 'grpc'}

        return proxy
    except Exception:
        return None

def parse_trojan(line, seen):
    try:
        uri, frag = _frag(line, 'trojan')
        parsed   = urlparse(uri)
        password = parsed.username
        server   = parsed.hostname
        port     = parsed.port or 443
        if not server or not password:
            return None

        params = parse_qs(parsed.query)
        def p(k, d=''):
            return params.get(k, [d])[0]

        net_type = p('type', 'tcp')

        proxy = {
            'name'            : make_unique_name(clean_name(frag), seen),
            'type'            : 'trojan',
            'server'          : server,
            'port'            : port,
            'password'        : password,
            'udp'             : True,
            'skip-cert-verify': p('allowInsecure','0')=='1' or p('insecure','0')=='1',
        }

        if p('sni'):
            proxy['sni'] = p('sni')
        if p('fp'):
            proxy['client-fingerprint'] = p('fp')
        if p('alpn'):
            proxy['alpn'] = [a for a in p('alpn').split(',') if a]

        if net_type == 'ws':
            path = unquote(p('path')) or '/'
            if path.startswith('http'):
                path = '/'
            ws = {'path': path}
            if p('host'):
                ws['headers'] = {'Host': p('host')}
            proxy['network']  = 'ws'
            proxy['ws-opts']  = ws
        elif net_type == 'grpc':
            proxy['network'] = 'grpc'
            if p('serviceName'):
                proxy['grpc-opts'] = {'grpc-service-name': p('serviceName')}
        elif net_type in ('xhttp', 'httpupgrade'):
            proxy['network'] = 'http'

        return proxy
    except Exception:
        return None

# ─── Main ─────────────────────────────────────────────────────────────────────

print(f"[*] Downloading {SOURCE_URL}")
resp = requests.get(SOURCE_URL, timeout=30)
resp.raise_for_status()
lines = resp.text.splitlines()
print(f"[*] Total lines: {len(lines)}")

proxies    = []
seen_names = set()
stats      = {'skipped': 0, 'invalid': 0}

for raw in lines:
    line = raw.strip()
    if not line:
        continue

    proxy = None
    if line.startswith('vless://'):
        proxy = parse_vless(line, seen_names)
    elif line.startswith('ss://'):
        proxy = parse_ss(line, seen_names)
    elif line.startswith('trojan://'):
        proxy = parse_trojan(line, seen_names)
    else:
        stats['skipped'] += 1
        continue

    if not proxy or not proxy.get('server') or not proxy.get('port'):
        stats['skipped'] += 1
        continue

    ok, reason = validate(proxy)
    if ok:
        proxies.append(proxy)
    else:
        stats['invalid'] += 1
        print(f"  [skip] {proxy.get('name','?')} — {reason}")

print(f"\n[✓] Valid   : {len(proxies)}")
print(f"[✗] Invalid : {stats['invalid']}")
print(f"[-] Skipped : {stats['skipped']}")

if not proxies:
    print("[!] No valid proxies — aborting")
    sys.exit(1)

proxy_names = [p['name'] for p in proxies]

clash_config = {
    'mixed-port'         : 7890,
    'allow-lan'          : False,
    'mode'               : 'rule',
    'log-level'          : 'info',
    'external-controller': '127.0.0.1:9090',

    'dns': {
        'enable'    : True,
        'ipv6'      : False,
        'nameserver': ['8.8.8.8', '1.1.1.1', 'https://dns.google/dns-query'],
        'fallback'  : ['tls://1.0.0.1:853', 'tls://8.8.4.4:853'],
    },

    'proxies': proxies,

    'proxy-groups': [
        {
            'name'   : '🚀 Select',
            'type'   : 'select',
            'proxies': ['♻️ Auto'] + proxy_names,
        },
        {
            'name'    : '♻️ Auto',
            'type'    : 'url-test',
            'proxies' : proxy_names,
            'url'     : 'http://www.gstatic.com/generate_204',
            'interval': 300,
            'tolerance': 50,
        },
        {
            'name'   : '🎯 Direct',
            'type'   : 'select',
            'proxies': ['DIRECT', 'REJECT'],
        },
    ],

    'rules': [
        'GEOIP,IR,DIRECT',
        'GEOIP,private,DIRECT',
        'MATCH,🚀 Select',
    ],
}

with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
    yaml.dump(clash_config, f, allow_unicode=True, sort_keys=False,
              default_flow_style=False)

print(f"[✓] Written to {OUTPUT_FILE}")
