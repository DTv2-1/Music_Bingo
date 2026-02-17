"""
Blind Date Pub Game — Django Models

Anonymous social mixer game for pubs:
- Players scan QR, register with nickname + description + up to 3 questions
- AI DJ (Celia Slack) announces players, reads questions, evaluates answers
- Real-time sync via SSE, TTS via ElevenLabs
"""

from django.db import models
from django.utils import timezone
import secrets


class BlindDateSession(models.Model):
    """A single Blind Date game event at a venue"""

    session_code = models.CharField(
        max_length=8, unique=True, editable=False, default='TEMP0000',
        help_text="Random 8-character code for URL/QR access"
    )
    venue_name = models.CharField(max_length=200)
    host_name = models.CharField(max_length=200, default="Celia Slack")

    # Game config
    min_players = models.IntegerField(default=5, help_text="Minimum players to start")
    answer_time_seconds = models.IntegerField(default=120, help_text="Seconds to answer each question")
    max_funny_shown = models.IntegerField(default=3, help_text="Top N funniest answers read aloud")

    # State
    STATUS_CHOICES = [
        ('lobby', 'Lobby — Waiting for Players'),
        ('in_progress', 'In Progress — Playing Rounds'),
        ('between_rounds', 'Between Rounds'),
        ('completed', 'Completed'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='lobby')

    # Current game position
    current_player_idx = models.IntegerField(default=0, help_text="Index in player queue")
    current_question_idx = models.IntegerField(default=0, help_text="Which question (0-2) of current player")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    started_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Blind Date Session"

    def save(self, *args, **kwargs):
        if not self.session_code or self.session_code == 'TEMP0000':
            while True:
                code = secrets.token_urlsafe(6)[:8].upper().replace('-', '0').replace('_', '1')
                if not BlindDateSession.objects.filter(session_code=code).exists():
                    self.session_code = code
                    break
        super().save(*args, **kwargs)

    def __str__(self):
        return f"BlindDate @ {self.venue_name} [{self.session_code}]"

    @property
    def player_count(self):
        return self.players.count()

    @property
    def can_start(self):
        return self.player_count >= self.min_players


class BlindDatePlayer(models.Model):
    """Anonymous player in a Blind Date session"""

    session = models.ForeignKey(BlindDateSession, on_delete=models.CASCADE, related_name='players')

    # Anonymous identity
    nickname = models.CharField(max_length=100)
    description = models.TextField(max_length=300, help_text="Short self-description")
    session_token = models.CharField(
        max_length=64, unique=True, editable=False,
        help_text="Temporary anonymous session token"
    )

    # Up to 3 questions the player wants to ask everyone
    question_1 = models.CharField(max_length=200, blank=True)
    question_2 = models.CharField(max_length=200, blank=True)
    question_3 = models.CharField(max_length=200, blank=True)

    # Whether this player's round has been played
    round_completed = models.BooleanField(default=False)

    # Queue order (set on game start)
    queue_order = models.IntegerField(default=0)

    # Timestamps
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['queue_order', 'joined_at']
        unique_together = ['session', 'nickname']

    def save(self, *args, **kwargs):
        if not self.session_token:
            self.session_token = secrets.token_urlsafe(48)[:64]
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nickname} @ {self.session.session_code}"

    @property
    def questions(self):
        """Return list of non-empty questions"""
        return [q for q in [self.question_1, self.question_2, self.question_3] if q]


class BlindDateAnswer(models.Model):
    """An answer to a player's question"""

    # Who asked the question
    question_player = models.ForeignKey(
        BlindDatePlayer, on_delete=models.CASCADE, related_name='received_answers'
    )
    question_index = models.IntegerField(help_text="0, 1, or 2 — which question")

    # Who answered
    answerer = models.ForeignKey(
        BlindDatePlayer, on_delete=models.CASCADE, related_name='given_answers'
    )

    answer_text = models.TextField(max_length=500)

    # AI evaluation
    humor_score = models.IntegerField(null=True, blank=True, help_text="AI humor rating 1-10")
    ai_commentary = models.TextField(blank=True, help_text="AI sarcastic remark about this answer")

    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['question_player', 'question_index', 'answerer']
        ordering = ['-humor_score']

    def __str__(self):
        return f"{self.answerer.nickname} → Q{self.question_index} of {self.question_player.nickname}"


class BlindDateLike(models.Model):
    """Mutual interest flag — if both players like each other, reveal nicknames"""

    session = models.ForeignKey(BlindDateSession, on_delete=models.CASCADE, related_name='likes')
    from_player = models.ForeignKey(BlindDatePlayer, on_delete=models.CASCADE, related_name='likes_given')
    to_player = models.ForeignKey(BlindDatePlayer, on_delete=models.CASCADE, related_name='likes_received')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['from_player', 'to_player']

    def __str__(self):
        return f"{self.from_player.nickname} ♥ {self.to_player.nickname}"

    @staticmethod
    def is_mutual(player_a, player_b):
        """Check if both players liked each other"""
        return (
            BlindDateLike.objects.filter(from_player=player_a, to_player=player_b).exists() and
            BlindDateLike.objects.filter(from_player=player_b, to_player=player_a).exists()
        )
