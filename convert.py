import base64
import json
import re
import sys
from collections import Counter
from urllib.parse import urlparse, parse_qs, unquote

import requests
import yaml

SOURCE_URL = "https://raw.githubusercontent.com/hamedcode/TCC/main/sent_configs.txt"
OUTPUT_FILE = "clash.yml"

LOCAL_CONFIGS_FILE = "sent_configs.txt"  # فایل محلی که داخل ریپو چک‌اوت شده
MAX_KEEP_IN_FILE    = 100  # حداکثر تعداد کانفیگ که داخل فایل نگه داشته میشه
USE_FOR_CONVERSION  = 50   # تعداد کانفیگ آخر که واسه ساخت clash.yml استفاده میشه

# ─── Feature switches ────────────────────────────────────────────────────────
# اگه هسته FlClash تو یکی از اینا مشکل داشت، فقط همون رو False کن.
# (یه پروکسی نامعتبر ممکنه کل کانفیگ رو توی FlClash لود نشه، پس اینا مهمن)
ENABLE_XHTTP            = True   # vless + network: xhttp
ENABLE_VLESS_ENCRYPTION = True   # vless + encryption=mlkem768x25519plus...
SYSTEM_DNS_FOR_SERVERS  = True   # resolve کردن دامنه سرورها با DNS سیستم

# ─── Constants (بر اساس مستندات رسمی mihomo) ────────────────────────────────

# همه cipher هایی که mihomo برای ss پشتیبانی می‌کنه
VALID_SS_CIPHERS = {
    'aes-128-ctr', 'aes-192-ctr', 'aes-256-ctr',
    'aes-128-cfb', 'aes-192-cfb', 'aes-256-cfb',
    'aes-128-gcm', 'aes-192-gcm', 'aes-256-gcm',
    'aes-128-ccm', 'aes-192-ccm', 'aes-256-ccm',
    'aes-128-gcm-siv', 'aes-256-gcm-siv',
    'chacha20-ietf', 'chacha20', 'xchacha20',
    'chacha20-ietf-poly1305', 'xchacha20-ietf-poly1305',
    'chacha8-ietf-poly1305', 'xchacha8-ietf-poly1305',
    '2022-blake3-aes-128-gcm', '2022-blake3-aes-256-gcm',
    '2022-blake3-chacha20-poly1305',
    'lea-128-gcm', 'lea-192-gcm', 'lea-256-gcm',
    'rabbit128-poly1305', 'aegis-128l', 'aegis-256',
    'aez-384', 'deoxys-ii-256-128', 'rc4-md5', 'none',
}
# اسم‌های مستعار v2ray/xray -> اسم mihomo
SS_CIPHER_ALIASES = {
    'chacha20-poly1305': 'chacha20-ietf-poly1305',
    'xchacha20-poly1305': 'xchacha20-ietf-poly1305',
}

VALID_FINGERPRINTS = {
    'chrome', 'firefox', 'safari', 'ios', 'android',
    'edge', '360', 'qq', 'random', 'randomized',
}

VALID_VMESS_CIPHERS = {'auto', 'none', 'zero', 'aes-128-gcm', 'chacha20-poly1305'}

# شبکه‌های مجاز برای هر پروتکل (لیست سفید)
ALLOWED_NETWORKS = {
    'vless' : {'tcp', 'ws', 'grpc', 'http', 'h2', 'xhttp'},
    'vmess' : {'tcp', 'ws', 'grpc', 'http', 'h2'},      # xhttp فقط VLESS
    'trojan': {'tcp', 'ws', 'grpc'},                     # http/h2/xhttp نه
}

XHTTP_MODES = {'auto', 'stream-one', 'stream-up', 'packet-up'}


class Skip(Exception):
    """کانفیگ قابل تبدیل نیست؛ دلیلش داخل پیام هست."""


# ─── Helpers ─────────────────────────────────────────────────────────────────

def b64decode_loose(s):
    s = s.strip().replace('-', '+').replace('_', '/')
    s += '=' * (-len(s) % 4)
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

def split_fragment(line, default):
    """(uri بدون #، اسم تمیز‌شده) برمی‌گردونه."""
    if '#' in line:
        uri, frag = line.split('#', 1)
        return uri, clean_name(frag) if frag.strip() else default
    return line, default

def qparams(query):
    """parse_qs یه بار decode می‌کنه؛ دیگه unquote دوباره نمی‌زنیم."""
    params = parse_qs(query, keep_blank_values=True)
    def p(k, d=''):
        v = params.get(k)
        val = v[0].strip() if v else ''
        return val or d
    return p

def truthy(v):
    return str(v).strip().lower() in ('1', 'true', 'yes')

def split_csv(v):
    return [x.strip() for x in v.split(',') if x.strip()]

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
    # باید base64url معتبر، بدون فاصله، حداقل ۳۰ کاراکتر
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
    بررسی نهایی یک پروکسی با قوانین Clash/Mihomo.
    (True, 'ok') یا (False, 'دلیل') برمیگردونه.
    """
    ptype  = proxy.get('type', '')
    server = proxy.get('server', '')
    port   = proxy.get('port')

    if not is_valid_hostname(server):
        return False, f"bad server: {server!r}"
    if not is_valid_port(port):
        return False, f"bad port: {port!r}"

    if ptype in ALLOWED_NETWORKS:
        net = proxy.get('network', 'tcp')
        if net not in ALLOWED_NETWORKS[ptype]:
            return False, f"network {net!r} not supported for {ptype}"
        fp = proxy.get('client-fingerprint', '')
        if fp and fp not in VALID_FINGERPRINTS:
            return False, f"bad fingerprint: {fp!r}"

    if ptype in ('vless', 'vmess'):
        if not is_valid_uuid(proxy.get('uuid', '')):
            return False, "bad uuid"

    if ptype == 'vless':
        ro = proxy.get('reality-opts')
        if ro is not None:
            if not is_valid_reality_pbk(ro.get('public-key', '')):
                return False, f"bad reality public-key: {ro.get('public-key','')!r}"
            if not is_valid_reality_sid(ro.get('short-id', '')):
                return False, f"bad reality short-id: {ro.get('short-id','')!r}"
        flow = proxy.get('flow', '')
        if flow and flow != 'xtls-rprx-vision':
            return False, f"bad flow: {flow!r}"
        if proxy.get('network') in ('h2', 'xhttp') and not proxy.get('tls'):
            return False, f"{proxy.get('network')} needs tls/reality"

    elif ptype == 'vmess':
        if proxy.get('cipher', 'auto') not in VALID_VMESS_CIPHERS:
            return False, f"bad vmess cipher: {proxy.get('cipher')!r}"
        if proxy.get('network') == 'h2' and not proxy.get('tls'):
            return False, "h2 needs tls"

    elif ptype == 'ss':
        if proxy.get('cipher', '') not in VALID_SS_CIPHERS:
            return False, f"bad cipher: {proxy.get('cipher')!r}"
        pw = proxy.get('password', '')
        if not pw or has_control_chars(pw):
            return False, "bad password"

    elif ptype == 'trojan':
        pw = proxy.get('password', '')
        if not pw or has_control_chars(pw):
            return False, "bad password"

    elif ptype == 'hysteria2':
        pw = proxy.get('password', '')
        if not pw or has_control_chars(pw):
            return False, "bad password"

    else:
        return False, f"unknown type: {ptype!r}"

    if not fields_are_clean(proxy):
        return False, "control chars in fields"

    return True, "ok"

# ─── Shared builders ─────────────────────────────────────────────────────────

def apply_tls(proxy, p, sni_key, host_hint='', reality=False):
    """
    sni_key: 'servername' (vless/vmess) یا 'sni' (trojan).
    host_hint: برای ws/xhttp/... اگه sni نبود، host رو به‌عنوان SNI می‌ذاریم
               (v2rayN هم همین کارو می‌کنه؛ بدونش روی کانفیگ‌های CDN وصل نمیشه).
    """
    sni = p('sni') or p('peer') or ('' if reality else host_hint)
    if sni:
        proxy[sni_key] = sni
    fp = p('fp').lower()
    if fp in VALID_FINGERPRINTS:
        proxy['client-fingerprint'] = fp
    alpn = split_csv(p('alpn'))
    if alpn:
        proxy['alpn'] = alpn
    if not reality and (truthy(p('allowInsecure')) or truthy(p('insecure'))):
        proxy['skip-cert-verify'] = True

def apply_reality(proxy, p, sni_key):
    pbk = p('pbk').replace(' ', '+')   # parse_qs هر '+' رو به فاصله تبدیل می‌کنه
    sid = p('sid')
    if not is_valid_reality_pbk(pbk):
        raise Skip("bad reality public-key")
    if not is_valid_reality_sid(sid):
        raise Skip("bad reality short-id")
    proxy['tls'] = True
    proxy['reality-opts'] = {'public-key': pbk, 'short-id': sid}
    apply_tls(proxy, p, sni_key, reality=True)
    proxy.setdefault('client-fingerprint', 'chrome')

XHTTP_EXTRA_MAP = {
    'xPaddingBytes': 'x-padding-bytes',
    'xPaddingObfsMode': 'x-padding-obfs-mode',
    'xPaddingKey': 'x-padding-key',
    'xPaddingHeader': 'x-padding-header',
    'xPaddingPlacement': 'x-padding-placement',
    'xPaddingMethod': 'x-padding-method',
    'noGRPCHeader': 'no-grpc-header',
    'uplinkHTTPMethod': 'uplink-http-method',
    'sessionPlacement': 'session-placement',
    'sessionKey': 'session-key',
    'seqPlacement': 'seq-placement',
    'seqKey': 'seq-key',
    'uplinkDataPlacement': 'uplink-data-placement',
    'uplinkDataKey': 'uplink-data-key',
    'uplinkChunkSize': 'uplink-chunk-size',
    'scMaxEachPostBytes': 'sc-max-each-post-bytes',
    'scMinPostsIntervalMs': 'sc-min-posts-interval-ms',
}
XHTTP_XMUX_MAP = {
    'maxConcurrency': 'max-concurrency',
    'maxConnections': 'max-connections',
    'cMaxReuseTimes': 'c-max-reuse-times',
    'hMaxRequestTimes': 'h-max-request-times',
    'hMaxReusableSecs': 'h-max-reusable-secs',
    'hKeepAlivePeriod': 'h-keep-alive-period',
}

def _range_value(v):
    if isinstance(v, dict) and 'from' in v and 'to' in v:
        return f"{v['from']}-{v['to']}"
    return v

def apply_xhttp_extra(xo, raw):
    try:
        extra = json.loads(raw)
    except Exception:
        raise Skip("xhttp extra is not valid JSON")
    if not isinstance(extra, dict):
        raise Skip("xhttp extra is not an object")
    if extra.get('downloadSettings'):
        raise Skip("xhttp downloadSettings (split up/down) not converted")
    for k, v in extra.items():
        if k in ('downloadSettings',):
            continue
        if k in XHTTP_EXTRA_MAP:
            if v in ('', None):
                continue
            xo[XHTTP_EXTRA_MAP[k]] = _range_value(v)
        elif k == 'headers':
            if isinstance(v, dict) and v:
                xo['headers'] = {str(a): str(b) for a, b in v.items()}
        elif k == 'xmux':
            if not isinstance(v, dict):
                raise Skip("xhttp xmux is not an object")
            reuse = {}
            for a, b in v.items():
                if a not in XHTTP_XMUX_MAP:
                    raise Skip(f"xhttp xmux key not supported: {a}")
                if b in ('', None, 0, '0'):
                    continue
                reuse[XHTTP_XMUX_MAP[a]] = str(_range_value(b))
            if reuse:
                xo['reuse-settings'] = reuse
        elif k in ('path', 'host', 'mode'):
            continue
        else:
            raise Skip(f"xhttp extra key not supported: {k}")

def apply_transport(proxy, ptype, net, p, sec):
    """
    transport مشترک بین vless / vmess / trojan.
    خروجی: host_hint برای SNI (فقط وقتی TLS هست).
    ترنسپورت‌های ناشناخته => Skip (به‌جای اینکه بی‌صدا tcp بشن).
    """
    allowed = ALLOWED_NETWORKS[ptype]
    host   = p('host')
    path   = p('path')
    header = p('headerType', 'none').lower()

    if net in ('tcp', ''):
        if header in ('none', ''):
            return ''
        if header == 'http' and 'http' in allowed:
            proxy['network'] = 'http'
            opts = {'method': 'GET', 'path': split_csv(path) or ['/']}
            if host:
                opts['headers'] = {'Host': split_csv(host)}
            proxy['http-opts'] = opts
            return host.split(',')[0].strip() if host else ''
        raise Skip(f"unsupported tcp headerType: {header}")

    if net == 'ws':
        proxy['network'] = 'ws'
        ws = {'path': path or '/'}
        if host:
            ws['headers'] = {'Host': host}
        proxy['ws-opts'] = ws
        return host

    if net == 'httpupgrade':
        # توی mihomo: network ws + v2ray-http-upgrade
        proxy['network'] = 'ws'
        ws = {'path': path or '/', 'v2ray-http-upgrade': True}
        if host:
            ws['headers'] = {'Host': host}
        proxy['ws-opts'] = ws
        return host

    if net == 'grpc':
        proxy['network'] = 'grpc'
        svc = p('serviceName')
        if svc:
            proxy['grpc-opts'] = {'grpc-service-name': svc}
        return ''

    if net in ('h2', 'http'):
        if 'h2' not in allowed:
            raise Skip(f"network {net} not supported for {ptype}")
        if sec == 'none':
            raise Skip("h2 needs tls")
        proxy['network'] = 'h2'
        h2 = {'path': path or '/'}
        if host:
            h2['host'] = split_csv(host)
        proxy['h2-opts'] = h2
        return host.split(',')[0].strip() if host else ''

    if net in ('xhttp', 'splithttp'):
        if 'xhttp' not in allowed:
            raise Skip(f"xhttp is VLESS-only (not {ptype})")
        if not ENABLE_XHTTP:
            raise Skip("xhttp disabled (ENABLE_XHTTP=False)")
        if sec == 'none':
            raise Skip("xhttp without tls/reality not converted")
        proxy['network'] = 'xhttp'
        xo = {'path': path or '/'}
        if host:
            xo['host'] = host
        mode = p('mode').lower()
        if mode in XHTTP_MODES:
            xo['mode'] = mode
        extra = p('extra')
        if extra:
            apply_xhttp_extra(xo, extra)
        proxy['xhttp-opts'] = xo
        return host

    raise Skip(f"unsupported network: {net}")   # kcp, quic, ...

# ─── Parsers ──────────────────────────────────────────────────────────────────

def parse_vless(line):
    uri, name = split_fragment(line, 'vless')
    u = urlparse(uri)
    uuid, server = unquote(u.username or ''), u.hostname
    port = u.port or 443
    if not server or not uuid:
        raise Skip("missing server/uuid")
    p = qparams(u.query)

    sec = p('security', 'none').lower()
    net = p('type', 'tcp').lower()
    if sec not in ('none', 'tls', 'reality'):
        raise Skip(f"unsupported security: {sec}")

    proxy = {'name': name, 'type': 'vless', 'server': server,
             'port': port, 'uuid': uuid, 'udp': True}

    enc = p('encryption', 'none')
    if enc.lower() != 'none':
        if not ENABLE_VLESS_ENCRYPTION:
            raise Skip("vless encryption disabled (ENABLE_VLESS_ENCRYPTION=False)")
        if not enc.startswith('mlkem768x25519plus.'):
            raise Skip(f"unsupported vless encryption: {enc[:20]}")
        proxy['encryption'] = enc

    host_hint = apply_transport(proxy, 'vless', net, p, sec)

    if sec == 'tls':
        proxy['tls'] = True
        apply_tls(proxy, p, 'servername', host_hint=host_hint)
    elif sec == 'reality':
        apply_reality(proxy, p, 'servername')

    flow = p('flow')
    if flow:
        if not flow.startswith('xtls-rprx-vision'):
            raise Skip(f"bad flow: {flow}")
        proxy['flow'] = 'xtls-rprx-vision'   # flow برای هر security ای نگه داشته میشه، نه فقط reality

    pe = p('packetEncoding').lower()
    if pe in ('xudp', 'packetaddr'):
        proxy['packet-encoding'] = pe
    return proxy


def _vmess_build(name, server, port, uuid, aid, q):
    p = lambda k, d='': (str(q.get(k, '') or '').strip() or d)
    sec = p('security', 'none').lower()
    if sec not in ('none', 'tls'):
        raise Skip(f"unsupported security: {sec}")
    net = p('network', 'tcp').lower()
    cipher = p('cipher', 'auto').lower()

    proxy = {'name': name, 'type': 'vmess', 'server': server, 'port': port,
             'uuid': uuid, 'alterId': aid, 'cipher': cipher, 'udp': True}

    host_hint = apply_transport(proxy, 'vmess', net, p, sec)
    if net == 'grpc' and not proxy.get('grpc-opts') and p('path'):
        # فرمت JSON ی vmess: service name توی path هست
        proxy['grpc-opts'] = {'grpc-service-name': p('path')}
    if sec == 'tls':
        proxy['tls'] = True
        apply_tls(proxy, p, 'servername', host_hint=host_hint)
    return proxy


def parse_vmess(line):
    uri, frag_name = split_fragment(line, '')
    body = uri[len('vmess://'):]

    dec = b64decode_loose(body.split('?')[0])
    if dec and dec.lstrip().startswith('{'):
        try:
            j = json.loads(dec)
        except Exception:
            raise Skip("vmess json is invalid")
        name = clean_name(str(j.get('ps') or frag_name or 'vmess'))
        server = str(j.get('add') or '').strip()
        port = int(str(j.get('port') or 0))
        uuid = str(j.get('id') or '').strip()
        aid = int(str(j.get('aid') or 0))
        q = {
            'network'   : j.get('net', 'tcp'),
            'headerType': j.get('type', 'none'),
            'host'      : j.get('host', ''),
            'path'      : j.get('path', ''),
            'security'  : 'tls' if str(j.get('tls', '')).lower() == 'tls' else 'none',
            'sni'       : j.get('sni', ''),
            'alpn'      : j.get('alpn', ''),
            'fp'        : j.get('fp', ''),
            'cipher'    : j.get('scy', 'auto'),
            'allowInsecure': '1' if truthy(j.get('allowInsecure', '')) or truthy(j.get('insecure', '')) else '',
            'serviceName': j.get('path', '') if str(j.get('net', '')).lower() == 'grpc' else '',
        }
        # grpc: توی JSON اسم سرویس داخل path هست
        if str(j.get('net', '')).lower() == 'grpc':
            q['path'] = ''
        return _vmess_build(name, server, port, uuid, aid, q)

    # فرمت URI: vmess://uuid@host:port?type=ws&security=tls...
    u = urlparse(uri)
    if not u.username or not u.hostname:
        raise Skip("unrecognized vmess link")
    p = qparams(u.query)
    q = {
        'network': p('type', 'tcp'), 'headerType': p('headerType', 'none'),
        'host': p('host'), 'path': p('path'), 'security': p('security', 'none'),
        'sni': p('sni'), 'alpn': p('alpn'), 'fp': p('fp'),
        'cipher': p('encryption', 'auto'), 'serviceName': p('serviceName'),
        'allowInsecure': p('allowInsecure') or p('insecure'), 'mode': p('mode'),
        'extra': p('extra'),
    }
    return _vmess_build(frag_name or 'vmess', u.hostname, u.port or 443,
                        unquote(u.username), 0, q)


def parse_trojan(line):
    uri, name = split_fragment(line, 'trojan')
    u = urlparse(uri)
    password = unquote(u.username or '')
    if u.password:
        password += ':' + unquote(u.password)
    server = u.hostname
    port = u.port or 443
    if not server or not password:
        raise Skip("missing server/password")
    p = qparams(u.query)

    sec = p('security', 'tls').lower()
    net = p('type', 'tcp').lower()
    if sec not in ('tls', 'reality'):
        raise Skip(f"trojan without tls/reality (security={sec})")

    proxy = {'name': name, 'type': 'trojan', 'server': server,
             'port': port, 'password': password, 'udp': True}

    host_hint = apply_transport(proxy, 'trojan', net, p, sec)
    if sec == 'tls':
        apply_tls(proxy, p, 'sni', host_hint=host_hint)
        if 'skip-cert-verify' not in proxy:
            proxy['skip-cert-verify'] = False
    else:
        apply_reality(proxy, p, 'sni')
    return proxy


def convert_ss_plugin(raw):
    parts = raw.split(';')
    name = parts[0].strip().lower()
    opts, flags = {}, set()
    for item in parts[1:]:
        item = item.strip()
        if '=' in item:
            k, v = item.split('=', 1)
            opts[k.strip()] = v.strip()
        elif item:
            flags.add(item)

    if name in ('obfs-local', 'simple-obfs', 'obfs'):
        mode = opts.get('obfs', 'http')
        if mode not in ('http', 'tls'):
            raise Skip(f"unsupported obfs mode: {mode}")
        po = {'mode': mode}
        if opts.get('obfs-host'):
            po['host'] = opts['obfs-host']
        return {'plugin': 'obfs', 'plugin-opts': po}

    if name == 'v2ray-plugin':
        mode = opts.get('mode', 'websocket')
        if mode != 'websocket':
            raise Skip(f"v2ray-plugin mode {mode!r} not supported by mihomo (websocket only)")
        po = {'mode': 'websocket', 'mux': opts.get('mux', '1') != '0'}
        if 'tls' in flags:
            po['tls'] = True
        if opts.get('host'):
            po['host'] = opts['host']
        if opts.get('path'):
            po['path'] = opts['path']
        return {'plugin': 'v2ray-plugin', 'plugin-opts': po}

    if name == 'shadow-tls':
        po = {'host': opts.get('host', ''), 'password': opts.get('password', ''),
              'version': int(opts.get('version', '2') or 2)}
        if not po['host'] or not po['password']:
            raise Skip("shadow-tls needs host and password")
        return {'plugin': 'shadow-tls', 'plugin-opts': po}

    raise Skip(f"ss plugin not converted: {name}")


def parse_ss(line):
    uri, name = split_fragment(line, 'ss')
    rest = uri[len('ss://'):]

    if '@' not in rest:
        # فرمت قدیمی: ss://BASE64(method:password@host:port)
        body, _, query = rest.partition('?')
        dec = b64decode_loose(unquote(body.rstrip('/')))
        if not dec or '@' not in dec:
            raise Skip("unrecognized ss link")
        userinfo, _, hostport = dec.rpartition('@')
    else:
        userinfo_raw, _, tail = rest.rpartition('@')
        hostport, _, query = tail.partition('?')
        hostport = hostport.rstrip('/')
        userinfo = unquote(userinfo_raw)          # پسورد/base64 ممکنه percent-encoded باشه (%3D ...)
        if ':' not in userinfo:
            dec = b64decode_loose(userinfo)
            if not dec or ':' not in dec:
                raise Skip("cannot decode ss userinfo")
            userinfo = dec

    method, _, password = userinfo.partition(':')
    method = SS_CIPHER_ALIASES.get(method.lower(), method.lower())
    if method not in VALID_SS_CIPHERS:
        raise Skip(f"unsupported ss cipher: {method}")
    if not password and method != 'none':
        raise Skip("empty ss password")

    m = re.fullmatch(r'\[?([^\]]+?)\]?:(\d+)', hostport)
    if not m:
        raise Skip("bad ss host:port")
    server, port = m.group(1), int(m.group(2))

    proxy = {'name': name, 'type': 'ss', 'server': server, 'port': port,
             'cipher': method, 'password': password, 'udp': True}

    p = qparams(query)
    plugin = p('plugin')
    if plugin:
        proxy.update(convert_ss_plugin(plugin))
    else:
        # فرمت غیراستاندارد v2rayN: ?type=ws&security=tls&host=...&path=...
        net = p('type', 'tcp').lower()
        if net in ('tcp', ''):
            pass
        elif net == 'ws':
            po = {'mode': 'websocket', 'path': p('path', '/'), 'mux': False}
            host = p('host') or p('sni')
            if host:
                po['host'] = host     # توی v2ray-plugin: host همزمان Host header و SNI هست
            if p('security').lower() == 'tls':
                po['tls'] = True
                if truthy(p('allowInsecure')) or truthy(p('insecure')):
                    po['skip-cert-verify'] = True
            proxy['plugin'] = 'v2ray-plugin'
            proxy['plugin-opts'] = po
        else:
            raise Skip(f"ss transport {net!r} not supported by mihomo")
    return proxy


def parse_hy2(line):
    scheme = 'hysteria2' if line.startswith('hysteria2://') else 'hy2'
    uri, name = split_fragment(line, 'hysteria2')
    u = urlparse(uri)
    password = unquote(u.username or '')
    if u.password:
        password += ':' + unquote(u.password)
    server = u.hostname
    try:
        port = u.port or 443
    except ValueError:
        raise Skip("hysteria2 port range not converted")
    if not server or not password:
        raise Skip("missing server/password")
    p = qparams(u.query)
    if p('mport') or p('ports'):
        raise Skip("hysteria2 port hopping not converted")

    proxy = {'name': name, 'type': 'hysteria2', 'server': server,
             'port': port, 'password': password}
    if p('sni'):
        proxy['sni'] = p('sni')
    if truthy(p('insecure')) or truthy(p('allowInsecure')):
        proxy['skip-cert-verify'] = True
    alpn = split_csv(p('alpn'))
    if alpn:
        proxy['alpn'] = alpn
    if p('obfs'):
        if p('obfs').lower() != 'salamander':
            raise Skip(f"unsupported hysteria2 obfs: {p('obfs')}")
        proxy['obfs'] = 'salamander'
        proxy['obfs-password'] = p('obfs-password')
    pin = p('pinSHA256')
    if pin:
        proxy['fingerprint'] = pin.replace(':', '').lower()
    return proxy


PARSERS = {
    'vless://'    : parse_vless,
    'vmess://'    : parse_vmess,
    'trojan://'   : parse_trojan,
    'ss://'       : parse_ss,
    'hysteria2://': parse_hy2,
    'hy2://'      : parse_hy2,
}

def convert_line(line):
    for prefix, fn in PARSERS.items():
        if line.startswith(prefix):
            try:
                return fn(line)
            except Skip:
                raise
            except Exception as e:
                raise Skip(f"parse error: {type(e).__name__}: {e}")
    scheme = line.split('://', 1)[0] if '://' in line else 'unknown'
    raise Skip(f"protocol not converted: {scheme}")

# ─── Main ─────────────────────────────────────────────────────────────────────

def build_clash_config(proxies):
    proxy_names = [p['name'] for p in proxies]

    dns = {
        'enable'    : True,
        'ipv6'      : False,
        # فقط IP باشه؛ برای resolve کردن خود DNS-over-HTTPS ها
        'default-nameserver': ['1.1.1.1', '8.8.8.8'],
        'nameserver': ['8.8.8.8', '1.1.1.1', 'https://dns.google/dns-query'],
        'fallback'  : ['tls://1.0.0.1:853', 'tls://8.8.4.4:853'],
    }
    if SYSTEM_DNS_FOR_SERVERS:
        # دامنه‌ی خود سرورها با DNS سیستم resolve بشه (مثل v2ray)،
        # نه با 8.8.8.8 که ممکنه توی شبکه بلاک/دستکاری شده باشه.
        dns['proxy-server-nameserver'] = ['system']

    return {
        'mixed-port'         : 7890,
        'allow-lan'          : False,
        'mode'               : 'rule',
        'log-level'          : 'info',
        'external-controller': '127.0.0.1:9090',

        'dns': dns,

        'proxies': proxies,

        'proxy-groups': [
            {
                'name'   : '🚀 Select',
                'type'   : 'select',
                'proxies': ['♻️ Auto', 'DIRECT'] + proxy_names,
            },
            {
                'name'    : '♻️ Auto',
                'type'    : 'url-test',
                'proxies' : proxy_names,
                'url'     : 'https://www.gstatic.com/generate_204',
                'interval': 300,
                'lazy'    : False,
            },
        ],

        'rules': [
            'GEOIP,IR,DIRECT',
            'GEOIP,private,DIRECT',
            'MATCH,🚀 Select',
        ],
    }


def main():
    print(f"[*] Downloading {SOURCE_URL}")
    resp = requests.get(SOURCE_URL, timeout=30)
    resp.raise_for_status()
    all_lines = [l.strip() for l in resp.text.splitlines() if l.strip()]
    print(f"[*] Total configs in source: {len(all_lines)}")

    # ─── نگه‌داری فقط ۱۰۰ کانفیگ آخر داخل فایل محلی ─────────────────────────
    if len(all_lines) > MAX_KEEP_IN_FILE:
        trimmed_lines = all_lines[-MAX_KEEP_IN_FILE:]
        with open(LOCAL_CONFIGS_FILE, 'w', encoding='utf-8') as f:
            f.write('\n'.join(trimmed_lines) + '\n')
        print(f"[*] {LOCAL_CONFIGS_FILE} trimmed: {len(all_lines)} -> {len(trimmed_lines)} "
              f"(removed {len(all_lines) - len(trimmed_lines)} oldest configs)")
    else:
        trimmed_lines = all_lines
        with open(LOCAL_CONFIGS_FILE, 'w', encoding='utf-8') as f:
            f.write('\n'.join(trimmed_lines) + '\n')
        print(f"[*] {LOCAL_CONFIGS_FILE} unchanged ({len(trimmed_lines)} configs, under limit)")

    # ─── فقط ۵۰ کانفیگ آخر واسه تبدیل به clash استفاده میشه ─────────────────
    lines = trimmed_lines[-USE_FOR_CONVERSION:]
    print(f"[*] Using last {len(lines)} configs for clash conversion")

    proxies, seen_names = [], set()
    reasons = Counter()

    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        try:
            proxy = convert_line(line)
            ok, reason = validate(proxy)
            if not ok:
                raise Skip(reason)
        except Skip as e:
            label = line.split('#', 1)[1][:40] if '#' in line else line[:30]
            print(f"  [skip] {unquote(label)} — {e}")
            reasons[str(e).split(':')[0]] += 1
            continue
        proxy['name'] = make_unique_name(proxy['name'], seen_names)
        proxies.append(proxy)

    print(f"\n[✓] Converted : {len(proxies)}")
    print(f"[✗] Skipped   : {sum(reasons.values())}")
    for r, n in reasons.most_common():
        print(f"      {n:3d} × {r}")

    if not proxies:
        print("[!] No valid proxies — aborting")
        sys.exit(1)

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        yaml.dump(build_clash_config(proxies), f, allow_unicode=True,
                  sort_keys=False, default_flow_style=False)

    print(f"[✓] Written to {OUTPUT_FILE}")


if __name__ == '__main__':
    main()
