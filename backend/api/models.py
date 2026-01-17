from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from datetime import datetime, date

# Create your models here.

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
