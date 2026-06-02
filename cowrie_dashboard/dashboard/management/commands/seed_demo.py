import random
from datetime import datetime, timedelta, timezone
from django.core.management.base import BaseCommand
from dashboard.models import Connection, LoginAttempt, IPGeolocation


# IPs reales de rangos conocidos por escaneos, con su geo aproximada
FAKE_IPS = [
    {'ip': '218.92.0.107', 'country': 'China', 'city': 'Nanjing', 'lat': 32.06, 'lon': 118.78},
    {'ip': '185.220.101.34', 'country': 'Alemania', 'city': 'Frankfurt', 'lat': 50.11, 'lon': 8.68},
    {'ip': '45.142.182.96', 'country': 'Países Bajos', 'city': 'Ámsterdam', 'lat': 52.37, 'lon': 4.89},
    {'ip': '193.46.255.12', 'country': 'Rusia', 'city': 'Moscú', 'lat': 55.75, 'lon': 37.61},
    {'ip': '141.98.10.63', 'country': 'Lituania', 'city': 'Vilna', 'lat': 54.68, 'lon': 25.27},
    {'ip': '209.141.55.26', 'country': 'Estados Unidos', 'city': 'Las Vegas', 'lat': 36.17, 'lon': -115.13},
    {'ip': '103.74.123.45', 'country': 'India', 'city': 'Bombay', 'lat': 19.07, 'lon': 72.87},
    {'ip': '61.177.172.140', 'country': 'China', 'city': 'Shanghái', 'lat': 31.22, 'lon': 121.45},
    {'ip': '92.118.39.88', 'country': 'Rumania', 'city': 'Bucarest', 'lat': 44.43, 'lon': 26.10},
    {'ip': '159.65.220.10', 'country': 'Singapur', 'city': 'Singapur', 'lat': 1.35, 'lon': 103.81},
]

USERNAMES = ['root', 'admin', 'user', 'test', 'oracle', 'postgres', 'ubuntu', 'pi', 'guest', 'administrator']
PASSWORDS = ['123456', 'admin', 'password', 'root', '12345678', 'qwerty', '1234', 'toor', 'P@ssw0rd', 'raspberry', 'admin123', '000000']


class Command(BaseCommand):
    help = 'Genera datos de prueba realistas para el dashboard (DEMO)'

    def add_arguments(self, parser):
        parser.add_argument('--count', type=int, default=200, help='Número de intentos a generar')

    def handle(self, *args, **options):
        count = options['count']

        # Crear geolocalizaciones
        geo_objs = {}
        for data in FAKE_IPS:
            geo, _ = IPGeolocation.objects.get_or_create(
                ip=data['ip'],
                defaults={
                    'country': data['country'], 'city': data['city'],
                    'lat': data['lat'], 'lon': data['lon'],
                }
            )
            geo_objs[data['ip']] = geo

        now = datetime.now(timezone.utc)
        nuevos = 0

        for i in range(count):
            ip_data = random.choice(FAKE_IPS)
            ip = ip_data['ip']
            # Timestamp aleatorio en las últimas 24 horas
            ts = now - timedelta(
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59),
                seconds=random.randint(0, 59),
            )
            session = f"demo{i:05d}"

            # Conexión
            Connection.objects.get_or_create(
                session=session,
                defaults={'src_ip': ip, 'timestamp': ts},
            )

            # Login: 90% fallidos, 10% exitosos (realista para honeypot)
            success = random.random() < 0.10
            username = random.choice(USERNAMES)
            password = random.choice(PASSWORDS)

            _, created = LoginAttempt.objects.get_or_create(
                session=session,
                timestamp=ts,
                username=username,
                password=password,
                defaults={
                    'src_ip': ip,
                    'success': success,
                    'geo': geo_objs.get(ip),
                }
            )
            if created:
                nuevos += 1

        self.stdout.write(self.style.SUCCESS(
            f"Demo generada: {nuevos} intentos de login en {len(FAKE_IPS)} IPs de {len(set(d['country'] for d in FAKE_IPS))} países"
        ))