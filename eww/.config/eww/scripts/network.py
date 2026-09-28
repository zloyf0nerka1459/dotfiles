#!/usr/bin/env python3
import subprocess
import json
import os
import sys
import time

CACHE_SCAN = '/tmp/eww_wifi_scan.json'
SCAN_TTL = 30  # seconds

def run_cmd(cmd, timeout=3):
    try:
        res = subprocess.run(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout
        )
        return res.stdout.strip()
    except Exception:
        return ''

def scan_wifi_networks(timeout=5):
    raw = run_cmd("LC_ALL=C.UTF-8 nmcli -t -m tabular -f 'IN-USE,SSID,SIGNAL,SECURITY' dev wifi list --rescan auto", timeout=timeout)
    networks = {}
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = []
        cur = []
        escaped = False
        for ch in line:
            if ch == '\\' and not escaped:
                escaped = True
                continue
            if ch == ':' and not escaped:
                parts.append(''.join(cur))
                cur = []
            else:
                cur.append(ch)
                escaped = False
        parts.append(''.join(cur))

        if len(parts) >= 4:
            in_use = (parts[0].strip() == '*')
            ssid = parts[1].strip()
            if not ssid:
                continue
            try:
                signal = int(parts[2].strip())
            except ValueError:
                signal = 0
            security = parts[3].strip()
            locked = (security != '--' and security != '')

            if signal >= 75:
                icon = '󰤨'
            elif signal >= 50:
                icon = '󰤥'
            elif signal >= 25:
                icon = '󰤢'
            else:
                icon = '󰤟'

            sec_display = security if (security and security != '--') else 'Открытая'
            if len(sec_display) > 8:
                sec_display = sec_display.split()[0]

            if ssid not in networks or signal > networks[ssid]['signal'] or in_use:
                networks[ssid] = {
                    'ssid': ssid,
                    'signal': signal,
                    'icon': icon,
                    'security': sec_display,
                    'locked': locked,
                    'in_use': in_use
                }

    sorted_nets = sorted(networks.values(), key=lambda x: (not x['in_use'], -x['signal']))
    result = sorted_nets[:7]
    try:
        with open(CACHE_SCAN, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False)
    except Exception:
        pass
    return result

def get_cached_wifi(force_rescan=False):
    if not force_rescan and os.path.exists(CACHE_SCAN):
        try:
            mtime = os.path.getmtime(CACHE_SCAN)
            if time.time() - mtime < SCAN_TTL:
                with open(CACHE_SCAN, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass
    return scan_wifi_networks()

def get_network_info(force_rescan=False):
    # 1. Default route & IP
    route_raw = run_cmd('ip -j route get 1.1.1.1 2>/dev/null', timeout=1)
    primary_dev = ''
    primary_ip = ''
    gateway = ''
    if route_raw:
        try:
            rdata = json.loads(route_raw)
            if rdata and isinstance(rdata, list):
                primary_dev = rdata[0].get('dev', '')
                primary_ip = rdata[0].get('prefsrc', '')
                gateway = rdata[0].get('gateway', '')
        except Exception:
            pass

    # 2. Devices status
    devices_raw = run_cmd('LC_ALL=C.UTF-8 nmcli -t -m tabular -f DEVICE,TYPE,STATE,CONNECTION device', timeout=2)
    eth_dev = ''
    eth_state = 'disconnected'
    eth_conn = ''
    eth_ip = ''

    wifi_dev = ''
    wifi_state = 'disconnected'
    wifi_conn = ''

    for line in devices_raw.splitlines():
        parts = line.split(':')
        if len(parts) >= 3:
            d_name, d_type, d_state = parts[0], parts[1], parts[2]
            d_conn = parts[3] if len(parts) > 3 else ''
            if d_type == 'ethernet' and not eth_dev:
                eth_dev = d_name
                eth_state = d_state
                eth_conn = d_conn
            elif d_type == 'wifi' and not wifi_dev:
                wifi_dev = d_name
                wifi_state = d_state
                wifi_conn = d_conn

    # 3. Wi-Fi general status
    gen_raw = run_cmd('LC_ALL=C.UTF-8 nmcli -t -f WIFI-HW,WIFI general', timeout=1)
    wifi_hw = 'missing'
    wifi_radio = 'disabled'
    if gen_raw:
        parts = gen_raw.split(':')
        if len(parts) >= 2:
            wifi_hw = parts[0]
            wifi_radio = parts[1]

    has_wifi_hw = (wifi_hw.lower() != 'missing')
    wifi_enabled = (wifi_radio.lower() == 'enabled')

    # Get Ethernet IP
    if eth_dev and eth_state == 'connected':
        if primary_dev == eth_dev and primary_ip:
            eth_ip = primary_ip
        else:
            ip_raw = run_cmd(f'ip -j addr show {eth_dev} 2>/dev/null', timeout=1)
            try:
                idata = json.loads(ip_raw)
                for addr in idata[0].get('addr_info', []):
                    if addr.get('family') == 'inet':
                        eth_ip = addr.get('local', '')
                        break
            except Exception:
                pass

    # Wi-Fi current connection details
    wifi_ssid = ''
    wifi_signal = 0
    wifi_ip = ''
    wifi_icon = '󰤮'
    if wifi_dev and wifi_state == 'connected':
        wifi_ssid = wifi_conn
        if primary_dev == wifi_dev and primary_ip:
            wifi_ip = primary_ip
        sig_raw = run_cmd(r"LC_ALL=C.UTF-8 nmcli -t -m tabular -f IN-USE,SIGNAL dev wifi list | grep '^\*' | cut -d: -f2", timeout=1)
        try:
            wifi_signal = int(sig_raw)
        except ValueError:
            wifi_signal = 80

        if wifi_signal >= 75:
            wifi_icon = '󰤨'
        elif wifi_signal >= 50:
            wifi_icon = '󰤥'
        elif wifi_signal >= 25:
            wifi_icon = '󰤢'
        else:
            wifi_icon = '󰤟'

    # Determine primary type and bar display
    net_type = 'none'
    bar_icon = '󰈂'
    bar_text = 'Офлайн'
    tooltip = 'Сеть: не подключено'

    if eth_state == 'connected':
        net_type = 'ethernet'
        bar_icon = '󰈀'
        bar_text = 'LAN'
        tooltip = f'Ethernet: {eth_dev} ({eth_ip})'
    elif wifi_state == 'connected':
        net_type = 'wifi'
        bar_icon = wifi_icon
        bar_text = wifi_ssid if wifi_ssid else 'Wi-Fi'
        tooltip = f'Wi-Fi: {wifi_ssid} ({wifi_signal}%) — {wifi_ip}'
    elif eth_dev and eth_state != 'connected':
        bar_icon = '󰈂'
        bar_text = 'Кабель откл.'
        tooltip = f'Ethernet: {eth_dev} (не подключен)'
    elif has_wifi_hw and not wifi_enabled:
        bar_icon = '󰤮'
        bar_text = 'Wi-Fi выкл.'
        tooltip = 'Беспроводной модуль выключен'

    wifi_list = []
    if has_wifi_hw and wifi_enabled:
        wifi_list = get_cached_wifi(force_rescan=force_rescan)

    return {
        'status': 'connected' if (eth_state == 'connected' or wifi_state == 'connected') else 'disconnected',
        'type': net_type,
        'icon': bar_icon,
        'text': bar_text,
        'tooltip': tooltip,
        'ip': primary_ip,
        'gateway': gateway,
        'ethernet': {
            'available': bool(eth_dev),
            'device': eth_dev if eth_dev else 'Не обнаружен',
            'name': eth_conn if eth_conn else 'Проводное подключение',
            'state': eth_state,
            'connected': (eth_state == 'connected'),
            'ip': eth_ip if eth_ip else 'Нет IP'
        },
        'wifi': {
            'has_hw': has_wifi_hw,
            'enabled': wifi_enabled,
            'connected': (wifi_state == 'connected'),
            'device': wifi_dev,
            'ssid': wifi_ssid,
            'signal': wifi_signal,
            'icon': wifi_icon,
            'ip': wifi_ip if wifi_ip else 'Нет IP'
        },
        'wifi_list': wifi_list
    }

def main():
    force_rescan = ('--rescan' in sys.argv)
    if '--toggle-wifi' in sys.argv:
        curr = run_cmd('LC_ALL=C.UTF-8 nmcli radio wifi')
        new_state = 'off' if curr == 'enabled' else 'on'
        run_cmd(f'nmcli radio wifi {new_state}')
        msg = 'Wi-Fi включен' if new_state == 'on' else 'Wi-Fi выключен'
        run_cmd(f'dunstify -a "Сеть" -t 2000 -i network-wireless "{msg}"')
        force_rescan = (new_state == 'on')

    elif '--disconnect-eth' in sys.argv:
        data = get_network_info()
        dev = data['ethernet']['device']
        if dev and dev != 'Не обнаружен':
            run_cmd(f'nmcli device disconnect {dev}')
            run_cmd(f'dunstify -a "Сеть" -t 2000 -i network-wired-disconnected "Ethernet ({dev}) отключен"')

    elif '--connect-eth' in sys.argv:
        data = get_network_info()
        dev = data['ethernet']['device']
        if dev and dev != 'Не обнаружен':
            run_cmd(f'nmcli device connect {dev}')
            run_cmd(f'dunstify -a "Сеть" -t 2000 -i network-wired "Ethernet ({dev}) подключается..."')

    elif '--disconnect-wifi' in sys.argv:
        data = get_network_info()
        dev = data['wifi']['device']
        if dev:
            run_cmd(f'nmcli device disconnect {dev}')
            run_cmd(f'dunstify -a "Сеть" -t 2000 -i network-wireless-disconnected "Wi-Fi отключен"')

    data = get_network_info(force_rescan=force_rescan)
    print(json.dumps(data, ensure_ascii=False))

if __name__ == '__main__':
    main()
