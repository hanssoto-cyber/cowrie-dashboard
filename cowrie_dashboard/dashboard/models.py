from django.db import models


class IPGeolocation(models.Model):
    """Geolocalización cacheada de cada IP (se consulta una sola vez)."""
    ip = models.GenericIPAddressField(unique=True)
    country = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    lat = models.FloatField(null=True, blank=True)
    lon = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.ip} ({self.country})"


class Connection(models.Model):
    """Cada conexión SSH al honeypot (evento cowrie.session.connect)."""
    src_ip = models.GenericIPAddressField()
    session = models.CharField(max_length=64, unique=True)
    timestamp = models.DateTimeField()

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.src_ip} @ {self.timestamp}"


class LoginAttempt(models.Model):
    """Cada intento de login (éxito o fallo)."""
    src_ip = models.GenericIPAddressField()
    username = models.CharField(max_length=255, blank=True)
    password = models.CharField(max_length=255, blank=True)
    success = models.BooleanField(default=False)
    session = models.CharField(max_length=64, blank=True)
    timestamp = models.DateTimeField()
    geo = models.ForeignKey(
        IPGeolocation,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='attempts',
    )

    class Meta:
        ordering = ['-timestamp']
        constraints = [
            models.UniqueConstraint(
                fields=['session', 'timestamp', 'username', 'password'],
                name='unique_login_event',
            )
        ]

    def __str__(self):
        estado = 'OK' if self.success else 'FAIL'
        return f"{self.src_ip} {self.username}/{self.password} [{estado}]"


class Command(models.Model):
    """Comando ejecutado por un atacante dentro de la sesión (cowrie.command.input)."""
    src_ip = models.GenericIPAddressField()
    session = models.CharField(max_length=64)
    command = models.TextField()
    timestamp = models.DateTimeField()
    geo = models.ForeignKey(
        IPGeolocation, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='commands',
    )

    class Meta:
        ordering = ['-timestamp']
        constraints = [
            models.UniqueConstraint(
                fields=['session', 'timestamp', 'command'],
                name='unique_command_event',
            )
        ]

    def __str__(self):
        return f"{self.src_ip}: {self.command[:50]}"


class FileDownload(models.Model):
    """Archivo que un atacante intentó descargar (cowrie.session.file_download)."""
    src_ip = models.GenericIPAddressField()
    session = models.CharField(max_length=64)
    url = models.TextField(blank=True)
    shasum = models.CharField(max_length=64, blank=True)
    timestamp = models.DateTimeField()
    geo = models.ForeignKey(
        IPGeolocation, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='downloads',
    )
    vt_detections = models.IntegerField(null=True, blank=True)
    vt_total = models.IntegerField(null=True, blank=True)
    vt_familia = models.CharField(max_length=255, blank=True)
    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.src_ip}: {self.url[:60]}"


class Session(models.Model):
    """Sesión SSH completa, con fingerprint del cliente atacante."""
    session = models.CharField(max_length=64, unique=True)
    src_ip = models.GenericIPAddressField()
    client_version = models.CharField(max_length=255, blank=True)
    hassh = models.CharField(max_length=64, blank=True)
    timestamp = models.DateTimeField()
    geo = models.ForeignKey(
        IPGeolocation, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='sessions',
    )

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.session} ({self.src_ip})"