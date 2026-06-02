import json
import requests
from collections import Counter
from datetime import datetime

def read_cowrie_logs(log_path):
    """Lee el archivo JSON de Cowrie y retorna lista de eventos."""
    events = []
    try:
        with open(log_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        events.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    except FileNotFoundError:
        pass
    return events

def get_stats(log_path):
    """Procesa los logs y retorna estadísticas completas."""
    events = read_cowrie_logs(log_path)

    total_connections = 0
    unique_ips = set()
    login_success = 0
    login_failed = 0
    recent_attacks = []
    passwords = []
    usernames = []
    hourly = Counter()

    for event in events:
        eventid = event.get('eventid', '')
        src_ip = event.get('src_ip', '')
        timestamp = event.get('timestamp', '')

        if eventid == 'cowrie.session.connect':
            total_connections += 1
            if src_ip:
                unique_ips.add(src_ip)

        if eventid == 'cowrie.login.success':
            login_success += 1
            recent_attacks.append({
                'src_ip': src_ip,
                'username': event.get('username', ''),
                'password': event.get('password', ''),
                'success': True,
                'timestamp': timestamp[:19].replace('T', ' '),
                'country': '',
            })

        if eventid == 'cowrie.login.failed':
            login_failed += 1
            passwords.append(event.get('password', ''))
            usernames.append(event.get('username', ''))
            recent_attacks.append({
                'src_ip': src_ip,
                'username': event.get('username', ''),
                'password': event.get('password', ''),
                'success': False,
                'timestamp': timestamp[:19].replace('T', ' '),
                'country': '',
            })

        # Agrupar por hora
        if timestamp:
            try:
                hour = timestamp[11:13] + ':00'
                hourly[hour] += 1
            except:
                pass

    # Top contraseñas y usuarios
    top_passwords = Counter(passwords).most_common(10)
    top_usernames = Counter(usernames).most_common(10)

    # Últimos 20 ataques
    recent_attacks = recent_attacks[-20:]
    recent_attacks.reverse()

    # Horas ordenadas
    hourly_list = [{'hour': h, 'count': c} for h, c in sorted(hourly.items())]

    return {
        'total_connections': total_connections,
        'unique_ips': len(unique_ips),
        'login_success': login_success,
        'login_failed': login_failed,
        'recent_attacks': recent_attacks,
        'top_passwords': top_passwords,
        'top_usernames': top_usernames,
        'hourly': hourly_list,
        'unique_ips_list': list(unique_ips),
    }

def geolocate_ips(ip_list):
    """Geolocaliza una lista de IPs usando ip-api.com (gratis, 45 req/min)."""
    geolocations = []
    for ip in ip_list[:15]:  # Límite para no exceder el rate limit
        if ip in ('127.0.0.1', 'localhost'):
            continue
        try:
            response = requests.get(
                f'http://ip-api.com/json/{ip}',
                timeout=3
            )
            data = response.json()
            if data.get('status') == 'success':
                geolocations.append({
                    'ip': ip,
                    'country': data.get('country', ''),
                    'city': data.get('city', ''),
                    'lat': data.get('lat'),
                    'lon': data.get('lon'),
                })
        except:
            continue
    return geolocations