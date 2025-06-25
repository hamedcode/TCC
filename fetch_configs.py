import json
import requests
import re
from bs4 import BeautifulSoup

def load_channels(path='channels.json'):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def extract_configs(text):
    patterns = [
        r'(vmess://[^\s"\']+)',
        r'(vless://[^\s"\']+)',
        r'(ss://[^\s"\']+)',
        r'(trojan://[^\s"\']+)',
        r'(tuic://[^\s"\']+)',
        r'(hy2://[^\s"\']+)',
    ]
    res = []
    for p in patterns:
        res.extend(re.findall(p, text))
    return res

def fetch_from_channel(channel):
    url = f'https://t.me/s/{channel}'
    resp = requests.get(url)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, 'html.parser')
    msgs = soup.select('.tgme_widget_message_text')
    configs = []
    for m in msgs:
        configs += extract_configs(m.get_text())
    return configs

def main():
    channels = load_channels()
    all_configs = set()
    for ch in channels:
        try:
            cfgs = fetch_from_channel(ch)
            all_configs.update(cfgs)
            print(f'Found {len(cfgs)} configs in {ch}')
        except Exception as e:
            print(f'Error fetching {ch}: {e}')
    with open('output.txt', 'w', encoding='utf-8') as f:
        for cfg in sorted(all_configs):
            f.write(cfg + '\n')
    print(f'Total configs saved: {len(all_configs)} in output.txt')

if __name__ == '__main__':
    main()
