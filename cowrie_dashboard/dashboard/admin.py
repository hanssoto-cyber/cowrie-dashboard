from django.contrib import admin
from .models import Connection, LoginAttempt, IPGeolocation


@admin.register(IPGeolocation)
class IPGeolocationAdmin(admin.ModelAdmin):
    list_display = ('ip', 'country', 'city', 'lat', 'lon', 'created_at')
    search_fields = ('ip', 'country', 'city')
    list_filter = ('country',)


@admin.register(Connection)
class ConnectionAdmin(admin.ModelAdmin):
    list_display = ('src_ip', 'session', 'timestamp')
    search_fields = ('src_ip', 'session')
    list_filter = ('timestamp',)


@admin.register(LoginAttempt)
class LoginAttemptAdmin(admin.ModelAdmin):
    list_display = ('src_ip', 'username', 'password', 'success', 'timestamp')
    search_fields = ('src_ip', 'username', 'password')
    list_filter = ('success', 'timestamp')