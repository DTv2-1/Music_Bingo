from django.contrib import admin
from .models import JingleSchedule, JinglePlayHistory, VenueConfiguration, KaraokeSession, KaraokeQueue

# Register your models here.

@admin.register(JingleSchedule)
class JingleScheduleAdmin(admin.ModelAdmin):
    list_display = ('jingle_name', 'venue_name', 'start_date', 'end_date', 'repeat_pattern', 'enabled', 'priority')
    list_filter = ('enabled', 'repeat_pattern', 'venue_name')
    search_fields = ('jingle_name', 'venue_name')
    ordering = ('-priority', '-created_at')

@admin.register(JinglePlayHistory)
class JinglePlayHistoryAdmin(admin.ModelAdmin):
    list_display = ('jingle_filename', 'played_at', 'round_number')
    list_filter = ('played_at',)
    ordering = ('-played_at',)

@admin.register(VenueConfiguration)
class VenueConfigurationAdmin(admin.ModelAdmin):
    list_display = ('venue_name', 'num_players', 'voice_id', 'include_qr', 'created_at')
    search_fields = ('venue_name',)
    ordering = ('venue_name',)

@admin.register(KaraokeSession)
class KaraokeSessionAdmin(admin.ModelAdmin):
    list_display = ('venue_name', 'status', 'created_at', 'started_at', 'get_queue_count')
    list_filter = ('status', 'created_at')
    search_fields = ('venue_name',)
    ordering = ('-created_at',)
    
    def get_queue_count(self, obj):
        return obj.get_queue_count()
    get_queue_count.short_description = 'Queue Count'

@admin.register(KaraokeQueue)
class KaraokeQueueAdmin(admin.ModelAdmin):
    list_display = ('name', 'song_title', 'artist', 'session', 'position', 'status', 'requested_at')
    list_filter = ('status', 'session')
    search_fields = ('name', 'song_title', 'artist')
    ordering = ('session', 'position')

