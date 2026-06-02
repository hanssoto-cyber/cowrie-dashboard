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