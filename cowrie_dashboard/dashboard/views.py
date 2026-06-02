import json
from collections import Counter
from django.shortcuts import render
from django.http import JsonResponse
from django.db.models import Count
from django.utils import timezone as djtz
from .models import Connection, LoginAttempt, IPGeolocation


def _build_stats():
    """Construye todas las estadísticas desde la base de datos."""
    total_connections = Connection.objects.count()

    # IPs únicas de TODOS los eventos (conexiones + logins)
    ips = set(Connection.objects.values_list('src_ip', flat=True))
    ips |= set(LoginAttempt.objects.values_list('src_ip', flat=True))
    ips.discard('')
    unique_ips = len(ips)

    login_success = LoginAttempt.objects.filter(success=True).count()
    login_failed = LoginAttempt.objects.filter(success=False).count()

    # Top contraseñas y usuarios (agregación en la BD)
    top_passwords = list(
        LoginAttempt.objects.exclude(password='')
        .values('password').annotate(count=Count('id'))
        .order_by('-count')[:10]
    )
    top_usernames = list(
        LoginAttempt.objects.exclude(username='')
        .values('username').annotate(count=Count('id'))
        .order_by('-count')[:10]
    )

    # Distribución por hora (convertida a hora de Santiago)
    hourly_counter = Counter()
    for ts in LoginAttempt.objects.values_list('timestamp', flat=True):
        local = djtz.localtime(ts)
        hourly_counter[local.strftime('%H:00')] += 1
    hourly = [{'hour': h, 'count': c} for h, c in sorted(hourly_counter.items())]

    # Últimos 20 ataques con geolocalización
    recent = LoginAttempt.objects.select_related('geo').order_by('-timestamp')[:20]
    recent_attacks = [{
        'src_ip': a.src_ip,
        'username': a.username,
        'password': a.password,
        'success': a.success,
        'country': a.geo.country if a.geo else '',
        'timestamp': djtz.localtime(a.timestamp).strftime('%Y-%m-%d %H:%M:%S'),
    } for a in recent]

    # Geolocalizaciones para el mapa
    geolocations = [{
        'ip': g.ip, 'country': g.country, 'city': g.city,
        'lat': g.lat, 'lon': g.lon,
    } for g in IPGeolocation.objects.exclude(lat__isnull=True)]

    return {
        'total_connections': total_connections,
        'unique_ips': unique_ips,
        'login_success': login_success,
        'login_failed': login_failed,
        'top_passwords': top_passwords,
        'top_usernames': top_usernames,
        'hourly': hourly,
        'recent_attacks': recent_attacks,
        'geolocations': geolocations,
        'max_password_count': top_passwords[0]['count'] if top_passwords else 1,
        'max_username_count': top_usernames[0]['count'] if top_usernames else 1,
    }


def index(request):
    data = _build_stats()
    context = {
        'stats': data,
        'geolocations_json': json.dumps(data['geolocations']),
        'hourly_json': json.dumps(data['hourly']),
    }
    return render(request, 'dashboard/index.html', context)


def attacks(request):
    data = _build_stats()
    return render(request, 'dashboard/attacks.html', {'stats': data})


def stats(request):
    data = _build_stats()
    context = {
        'stats': data,
        'hourly_json': json.dumps(data['hourly']),
    }
    return render(request, 'dashboard/stats.html', context)


def api_stats(request):
    data = _build_stats()
    return JsonResponse(data)