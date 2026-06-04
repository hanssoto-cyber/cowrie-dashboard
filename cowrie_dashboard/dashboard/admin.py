from django.contrib import admin
from .models import (
    Connection, LoginAttempt, IPGeolocation,
    Command, FileDownload, Session,
)


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


@admin.register(Command)
class CommandAdmin(admin.ModelAdmin):
    list_display = ('src_ip', 'command', 'timestamp')
    search_fields = ('src_ip', 'command', 'session')
    list_filter = ('timestamp',)


@admin.register(FileDownload)
class FileDownloadAdmin(admin.ModelAdmin):
    list_display = ('src_ip', 'url', 'shasum', 'timestamp')
    search_fields = ('src_ip', 'url', 'shasum')


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ('session', 'src_ip', 'client_version', 'hassh', 'timestamp')
    search_fields = ('session', 'src_ip', 'client_version', 'hassh')