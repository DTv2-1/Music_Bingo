from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from datetime import datetime, date

# Create your models here.

class TaskStatus(models.Model):
    """
    Stores async task status for card generation, jingle generation, etc.
    Replaces in-memory tasks_storage dict to support multiple Cloud Run instances
    """
    task_id = models.CharField(max_length=36, primary_key=True, help_text="UUID of the task")
    task_type = models.CharField(max_length=50, help_text="Type: 'card_generation', 'jingle_generation'")
    status = models.CharField(
        max_length=20,
        default='pending',
        help_text="Status: pending, processing, completed, failed"
    )
    progress = models.IntegerField(default=0, help_text="Progress percentage (0-100)")
    current_step = models.CharField(max_length=100, blank=True, help_text="Current processing step")
    
    # Timing
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Results
    result = models.JSONField(null=True, blank=True, help_text="Success result data")
    error = models.TextField(blank=True, help_text="Error message if failed")
    
    # Metadata
    metadata = models.JSONField(null=True, blank=True, help_text="Additional task parameters")
    
    class Meta:
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['status', '-started_at']),
            models.Index(fields=['task_type', '-started_at']),
        ]
    
    def __str__(self):
        return f"{self.task_type} - {self.task_id[:8]} ({self.status})"

class JingleSchedule(models.Model):
    """
    Scheduled jingle with time-based playback rules
    Allows scheduling jingles based on:
    - Date ranges (start_date to end_date)
    - Time periods (time_start to time_end)
    - Days of the week (monday through sunday)
    - Repeat patterns (occasional, regular, often)
    """
    
    # Jingle Identification
    jingle_name = models.CharField(
        max_length=200,
        help_text="Display name (e.g., 'Tuesday Night Taco Promotion')"
    )
    jingle_filename = models.CharField(
        max_length=255,
        help_text="Actual audio file (e.g., 'jingle_12345.mp3')"
    )
    
    # Venue Filter
    venue_name = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="Optional: Venue name to filter schedules (e.g., 'Admiral Rodney'). Leave empty for all venues."
    )
    
    # Session Filter (most specific)
    session = models.ForeignKey(
        'BingoSession',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='jingle_schedules',
        help_text="Optional: Specific bingo session. If set, this schedule applies only to this session. If null, uses venue_name filtering."
    )
    
    # Date Range
    start_date = models.DateField(
        help_text="First day this jingle becomes active"
    )
    end_date = models.DateField(
        null=True,
        blank=True,
        help_text="Last day this jingle is active (null = no end)"
    )
    
    # Time Period (Optional)
    time_start = models.TimeField(
        null=True,
        blank=True,
        help_text="Start time (e.g., 17:00 for 5pm)"
    )
    time_end = models.TimeField(
        null=True,
        blank=True,
        help_text="End time (e.g., 22:00 for 10pm)"
    )
    
    # Days of Week
    monday = models.BooleanField(default=True)
    tuesday = models.BooleanField(default=True)
    wednesday = models.BooleanField(default=True)
    thursday = models.BooleanField(default=True)
    friday = models.BooleanField(default=True)
    saturday = models.BooleanField(default=True)
    sunday = models.BooleanField(default=True)
    
    # Repeat Pattern
    REPEAT_CHOICES = [
        ('occasional', 'Occasional - Every 8-10 rounds'),
        ('regular', 'Regular - Every 5-7 rounds'),
        ('often', 'Often - Every 3-4 rounds'),
    ]
    repeat_pattern = models.CharField(
        max_length=20,
        choices=REPEAT_CHOICES,
        default='regular'
    )
    
    # Status
    enabled = models.BooleanField(
        default=True,
        help_text="Master on/off switch for this schedule"
    )
    
    # Priority (for conflict resolution)
    priority = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Higher priority wins if multiple jingles qualify (0-100)"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-priority', '-created_at']
        verbose_name = "Jingle Schedule"
        verbose_name_plural = "Jingle Schedules"
    
    def __str__(self):
        return f"{self.jingle_name} ({self.start_date} to {self.end_date or 'ongoing'})"
    
    def is_active_now(self):
        """
        Check if this schedule is currently active based on:
        - enabled flag
        - current date within date range
        - current time within time range (if specified)
        - current day of week matches selected days
        
        Returns:
            bool: True if schedule should be active now
        """
        if not self.enabled:
            return False
        
        now = datetime.now()
        today = date.today()
        
        # Check date range
        if today < self.start_date:
            return False
        if self.end_date and today > self.end_date:
            return False
        
        # Check time range (if specified)
        if self.time_start and self.time_end:
            current_time = now.time()
            if not (self.time_start <= current_time <= self.time_end):
                return False
        
        # Check day of week
        day_map = {
            0: self.monday,
            1: self.tuesday,
            2: self.wednesday,
            3: self.thursday,
            4: self.friday,
            5: self.saturday,
            6: self.sunday,
        }
        if not day_map[today.weekday()]:
            return False
        
        return True
    
    def get_interval(self):
        """
        Get the round interval based on repeat pattern
        
        Returns:
            int: Number of rounds between jingle plays
        """
        patterns = {
            'occasional': 9,  # Average of 8-10
            'regular': 6,     # Average of 5-7
            'often': 3,       # Average of 3-4
        }
        return patterns.get(self.repeat_pattern, 6)


class JinglePlayHistory(models.Model):
    """
    Track when jingles were played for analytics
    Optional table for tracking jingle playback history
    """
    schedule = models.ForeignKey(
        JingleSchedule,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='play_history'
    )
    jingle_filename = models.CharField(max_length=255)
    played_at = models.DateTimeField(auto_now_add=True)
    round_number = models.IntegerField()
    
    class Meta:
        ordering = ['-played_at']
        verbose_name = "Jingle Play History"
        verbose_name_plural = "Jingle Play History"
    
    def __str__(self):
        return f"{self.jingle_filename} played at {self.played_at}"


class VenueConfiguration(models.Model):
    """
    Store venue-specific configuration for Music Bingo
    Each venue has its own branding, settings, and preferences
    """
    venue_name = models.CharField(
        max_length=200,
        unique=True,
        help_text="Unique venue name (e.g., 'The Admiral Rodney Southwell')"
    )
    
    # Game Settings
    num_players = models.IntegerField(
        default=25,
        validators=[MinValueValidator(5), MaxValueValidator(100)],
        help_text="Default number of players for this venue"
    )
    voice_id = models.CharField(
        max_length=100,
        default='JBFqnCBsd6RMkjVDRZzb',
        help_text="ElevenLabs voice ID for announcements"
    )
    selected_decades = models.JSONField(
        default=list,
        help_text="Array of selected decades (e.g., ['60s', '70s', '80s'])"
    )
    
    # Branding
    pub_logo = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        help_text="URL to pub logo image"
    )
    
    # Social Media
    social_platform = models.CharField(
        max_length=50,
        blank=True,
        default='instagram',
        help_text="Social media platform (instagram, facebook, tiktok, twitter)"
    )
    social_username = models.CharField(
        max_length=200,
        blank=True,
        help_text="Social media username (without @)"
    )
    include_qr = models.BooleanField(
        default=False,
        help_text="Include QR code on bingo cards"
    )
    
    # Prizes
    prize_4corners = models.CharField(
        max_length=200,
        blank=True,
        help_text="Prize for 4 corners (e.g., '£10 voucher')"
    )
    prize_first_line = models.CharField(
        max_length=200,
        blank=True,
        help_text="Prize for first line (e.g., '£15 voucher')"
    )
    prize_full_house = models.CharField(
        max_length=200,
        blank=True,
        help_text="Prize for full house (e.g., '£50 cash prize')"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['venue_name']
        verbose_name = "Venue Configuration"
        verbose_name_plural = "Venue Configurations"
    
    def __str__(self):
        return f"{self.venue_name} Configuration"


# ============================================================
# KARAOKE SYSTEM MODELS
# ============================================================

class KaraokeSession(models.Model):
    """
    Karaoke session for a venue
    Manages the overall karaoke night with queue and settings
    """
    SESSION_STATUS = [
        ('waiting', 'Waiting to Start'),
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('ended', 'Ended'),
    ]
    
    venue_name = models.CharField(
        max_length=200,
        help_text="Venue hosting this karaoke session"
    )
    status = models.CharField(
        max_length=20,
        choices=SESSION_STATUS,
        default='waiting',
        help_text="Current session status"
    )
    
    # Settings
    avg_song_duration = models.IntegerField(
        default=240,  # 4 minutes in seconds
        help_text="Average song duration in seconds for time estimation"
    )
    auto_advance = models.BooleanField(
        default=True,
        help_text="Automatically advance to next singer when song completes"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Karaoke Session"
        verbose_name_plural = "Karaoke Sessions"
    
    def __str__(self):
        return f"Karaoke @ {self.venue_name} ({self.status})"
    
    def get_active_queue(self):
        """Get all pending entries in queue order"""
        return self.queue_entries.filter(
            status='pending'
        ).order_by('position')
    
    def get_current_singer(self):
        """Get currently singing entry"""
        return self.queue_entries.filter(status='singing').first()
    
    def get_queue_count(self):
        """Get number of people waiting"""
        return self.queue_entries.filter(status='pending').count()


class KaraokeQueue(models.Model):
    """
    Queue entry for a singer in a karaoke session
    Represents one person's song request
    """
    QUEUE_STATUS = [
        ('pending', 'Waiting in Queue'),
        ('singing', 'Currently Singing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    session = models.ForeignKey(
        KaraokeSession,
        on_delete=models.CASCADE,
        related_name='queue_entries',
        help_text="Session this queue entry belongs to"
    )
    
    # Singer Info
    name = models.CharField(
        max_length=200,
        help_text="Singer's name"
    )
    message = models.TextField(
        blank=True,
        help_text="Optional message to the crowd (e.g., 'Dedicated to my friends')"
    )
    
    # Song Info (from Karafun API or manual entry)
    song_id = models.CharField(
        max_length=100,
        help_text="Karafun song ID or custom identifier"
    )
    song_title = models.CharField(
        max_length=300,
        help_text="Song title"
    )
    artist = models.CharField(
        max_length=200,
        help_text="Artist name"
    )
    duration = models.IntegerField(
        default=240,
        help_text="Song duration in seconds"
    )
    
    # URLs (from Karafun API)
    audio_url = models.URLField(
        max_length=500,
        blank=True,
        help_text="URL to instrumental audio track"
    )
    lyrics_url = models.URLField(
        max_length=500,
        blank=True,
        help_text="URL to synchronized lyrics (LRC format)"
    )
    
    # Queue Management
    position = models.IntegerField(
        help_text="Position in queue (1 = next up)"
    )
    status = models.CharField(
        max_length=20,
        choices=QUEUE_STATUS,
        default='pending',
        help_text="Current status in queue"
    )
    
    # Timestamps
    requested_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['session', 'position']
        verbose_name = "Karaoke Queue Entry"
        verbose_name_plural = "Karaoke Queue Entries"
    
    def __str__(self):
        return f"{self.name} - {self.song_title} ({self.status})"
    
    def estimated_wait_time(self):
        """
        Calculate estimated wait time in minutes
        Based on position and average song duration
        """
        if self.status != 'pending':
            return 0
        
        # Count entries ahead in queue
        ahead = KaraokeQueue.objects.filter(
            session=self.session,
            status='pending',
            position__lt=self.position
        ).count()
        
        # Add current singer if any
        current = self.session.get_current_singer()
        if current:
            ahead += 1
        
        # Calculate time (in minutes)
        avg_duration = self.session.avg_song_duration
        wait_seconds = ahead * avg_duration
        return round(wait_seconds / 60)


class BingoSession(models.Model):
    """
    Music Bingo game session with configuration and state
    """
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    # Session Identification
    session_id = models.CharField(
        max_length=100,
        unique=True,
        help_text="Unique session identifier (UUID)"
    )
    
    # Venue Information
    venue_name = models.CharField(
        max_length=200,
        help_text="Pub or venue name"
    )
    host_name = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="Optional host/DJ name"
    )
    
    # Game Configuration
    num_players = models.IntegerField(
        default=25,
        validators=[MinValueValidator(5), MaxValueValidator(100)],
        help_text="Number of players (affects song selection)"
    )
    voice_id = models.CharField(
        max_length=100,
        default='JBFqnCBsd6RMkjVDRZzb',
        help_text="ElevenLabs voice ID for announcements"
    )
    decades = models.JSONField(
        default=list,
        help_text="Selected decades (e.g., ['1960s', '1970s', '1980s'])"
    )
    genres = models.JSONField(
        default=list,
        blank=True,
        help_text="Selected genres (e.g., ['Rock', 'Pop', 'Dance']). Empty means all genres."
    )
    
    # Branding (Optional)
    logo_url = models.TextField(
        blank=True,
        null=True,
        help_text="URL to pub logo (supports data URIs for uploaded images)"
    )
    social_media = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        help_text="Social media URL for QR code"
    )
    include_qr = models.BooleanField(
        default=False,
        help_text="Include QR code on cards"
    )
    
    # Prizes
    prizes = models.JSONField(
        default=dict,
        help_text="Prize information (4corners, first_line, full_house)"
    )
    
    # Song Pool - CRITICAL for matching cards with game
    song_pool = models.JSONField(
        default=list,
        help_text="Array of songs used to generate the cards (ensures songs match printed cards)"
    )
    pdf_url = models.TextField(
        blank=True,
        null=True,
        help_text="URL to generated PDF cards in Google Cloud Storage"
    )
    game_number = models.IntegerField(
        default=1,
        help_text="Game number for this venue/date"
    )
    
    # Game State
    songs_played = models.JSONField(
        default=list,
        help_text="Array of song IDs that have been played"
    )
    current_song_index = models.IntegerField(
        default=0,
        help_text="Current position in song pool"
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        help_text="Current session status"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['venue_name', '-created_at']),
            models.Index(fields=['status', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.venue_name} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"
    
    def get_duration_minutes(self):
        """Calculate session duration in minutes"""
        if not self.started_at:
            return 0
        end_time = self.completed_at or datetime.now()
        duration = end_time - self.started_at
        return round(duration.total_seconds() / 60)
    
    def get_songs_count(self):
        """Get number of songs played"""
        return len(self.songs_played)


