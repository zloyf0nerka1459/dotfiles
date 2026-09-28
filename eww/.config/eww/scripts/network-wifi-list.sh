#!/usr/bin/env bash
python3 -c "
import json, os
CACHE = '/tmp/eww_wifi_scan.json'
if os.path.exists(CACHE):
    try:
        with open(CACHE, 'r', encoding='utf-8') as f:
            print(json.dumps(json.load(f), ensure_ascii=False))
            exit(0)
    except Exception:
        pass
print('[]')
"
