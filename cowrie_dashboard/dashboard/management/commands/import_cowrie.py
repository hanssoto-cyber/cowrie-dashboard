import json
import time
import requests
from datetime import datetime, timezone
from django.core.management.base import BaseCommand
from django.conf import settings
from dashboard.models import (
    Connection, LoginAttempt, IPGeolocation,
    Command as CommandModel, FileDownload, Session,
)


class Command(BaseCommand):
    help = 'Importa eventos del log JSON de Cowrie a la base de datos'

    def add_arguments(self, parser):
        parser.add_argument(
            '--path',
            type=str,
            default=settings.COWRIE_LOG_PATH,
            help='Ruta al archivo cowrie.json',
        )

    def handle(self, *args, **options):
        log_path = options['path']
        self.stdout.write(f"Leyendo log desde: {log_path}")

        try:
            with open(log_path, 'r') as f:
                lines = f.readlines()
        except FileNotFoundError:
            self.stderr.write(self.style.ERROR(f"No se encontró el archivo: {log_path}"))
            return

        nuevas_conexiones = 0
        nuevos_logins = 0
        nuevos_comandos = 0
        nuevas_descargas = 0
        ips_para_geolocalizar = set()

        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue

            eventid = event.get('eventid', '')
            src_ip = event.get('src_ip', '')
            session = event.get('session', '')
            ts_raw = event.get('timestamp', '')

            if not ts_raw:
                continue

            # Parsear timestamp ISO a datetime con timezone
            try:
                ts = datetime.fromisoformat(ts_raw.replace('Z', '+00:00'))
            except ValueError:
                continue

            # Conexiones
            if eventid == 'cowrie.session.connect':
                _, created = Connection.objects.get_or_create(
                    session=session,
                    defaults={'src_ip': src_ip, 'timestamp': ts},
                )
                if created:
                    nuevas_conexiones += 1
                if src_ip:
                    ips_para_geolocalizar.add(src_ip)

            # Logins (éxito o fallo)
            if eventid in ('cowrie.login.success', 'cowrie.login.failed'):
                success = eventid == 'cowrie.login.success'
                username = event.get('username', '')
                password = event.get('password', '')

                _, created = LoginAttempt.objects.get_or_create(
                    session=session,
                    timestamp=ts,
                    username=username,
                    password=password,
                    defaults={'src_ip': src_ip, 'success': success},
                )
                if created:
                    nuevos_logins += 1
                if src_ip:
                    ips_para_geolocalizar.add(src_ip)
            # Comandos ejecutados por el atacante
            if eventid == 'cowrie.command.input':
                cmd = event.get('input', '')
                _, created = CommandModel.objects.get_or_create(
                    session=session,
                    timestamp=ts,
                    command=cmd,
                    defaults={'src_ip': src_ip},
                )
                if created:
                    nuevos_comandos += 1
                if src_ip:
                    ips_para_geolocalizar.add(src_ip)

            # Archivos descargados (malware)
            if eventid in ('cowrie.session.file_download', 'cowrie.session.file_upload'):
                Session  # noqa
                _, created = FileDownload.objects.get_or_create(
                    session=session,
                    timestamp=ts,
                    url=event.get('url', '') or event.get('filename', ''),
                    defaults={
                        'src_ip': src_ip,
                        'shasum': event.get('shasum', ''),
                    },
                )
                if created:
                    nuevas_descargas += 1
                if src_ip:
                    ips_para_geolocalizar.add(src_ip)

            # Versión del cliente SSH (parte de la sesión)
            if eventid == 'cowrie.client.version':
                Session.objects.update_or_create(
                    session=session,
                    defaults={
                        'src_ip': src_ip,
                        'client_version': event.get('version', ''),
                        'timestamp': ts,
                    },
                )

            # Fingerprint HASSH del cliente SSH
            if eventid == 'cowrie.client.kex':
                Session.objects.update_or_create(
                    session=session,
                    defaults={
                        'src_ip': src_ip,
                        'hassh': event.get('hassh', ''),
                        'timestamp': ts,
                    },
                )

        # Geolocalizar solo IPs que aún no conocemos
        self._geolocalizar(ips_para_geolocalizar)

        # Vincular geo a los login attempts que no la tengan
        self._vincular_geo()

        self.stdout.write(self.style.SUCCESS(
            f"Importación completa: "
            f"{nuevas_conexiones} conexiones, "
            f"{nuevos_logins} logins, "
            f"{nuevos_comandos} comandos, "
            f"{nuevas_descargas} descargas"
        ))

    def _geolocalizar(self, ips):
        """Geolocaliza solo IPs nuevas, respetando el rate limit de ip-api.com."""
        nuevas = 0
        for ip in ips:
            if ip in ('127.0.0.1', 'localhost', '::1'):
                continue
            # Si ya la tenemos, saltar
            if IPGeolocation.objects.filter(ip=ip).exists():
                continue
            try:
                resp = requests.get(f'http://ip-api.com/json/{ip}', timeout=3)
                data = resp.json()
                if data.get('status') == 'success':
                    IPGeolocation.objects.create(
                        ip=ip,
                        country=data.get('country', ''),
                        city=data.get('city', ''),
                        lat=data.get('lat'),
                        lon=data.get('lon'),
                    )
                    nuevas += 1
                    # ip-api.com permite 45 req/min → esperamos un poco
                    time.sleep(1.5)
            except requests.RequestException:
                continue
        if nuevas:
            self.stdout.write(f"Geolocalizadas {nuevas} IPs nuevas")

    def _vincular_geo(self):
        """Vincula la geolocalización a los login attempts que no la tengan."""
        geo_map = {g.ip: g for g in IPGeolocation.objects.all()}
        sin_geo = LoginAttempt.objects.filter(geo__isnull=True)
        for attempt in sin_geo:
            geo = geo_map.get(attempt.src_ip)
            if geo:
                attempt.geo = geo
                attempt.save(update_fields=['geo'])