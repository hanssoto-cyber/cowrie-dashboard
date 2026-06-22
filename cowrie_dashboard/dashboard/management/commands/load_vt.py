import csv
from django.core.management.base import BaseCommand
from dashboard.models import FileDownload


class Command(BaseCommand):
    help = 'Carga los resultados de VirusTotal desde reporte_vt.csv'

    def add_arguments(self, parser):
        parser.add_argument('--path', default='/home/ubuntu/reporte_vt.csv',
                            help='Ruta al CSV de VirusTotal')

    def handle(self, *args, **options):
        path = options['path']
        actualizados = 0

        with open(path, newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                sha = row['sha256']
                try:
                    detecciones = int(row['detecciones_maliciosas'])
                    total = int(row['total_motores'])
                except (ValueError, KeyError):
                    detecciones, total = None, None
                familia = row.get('nombre', '') or ''
                if familia == '-':
                    familia = ''

                # Actualiza todas las descargas con ese hash
                n = FileDownload.objects.filter(shasum=sha).update(
                    vt_detections=detecciones,
                    vt_total=total,
                    vt_familia=familia,
                )
                if n:
                    actualizados += n

        self.stdout.write(self.style.SUCCESS(
            f'Actualizadas {actualizados} descargas con datos de VirusTotal'
        ))