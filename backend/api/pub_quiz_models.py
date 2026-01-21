"""
Modelos de datos para el sistema Pub Quiz
Basado en la especificación extraída de los PDFs
"""

from django.db import models
from django.utils import timezone
import json


class QuizGenre(models.Model):
    """Géneros/categorías de preguntas para el quiz"""
    
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True, help_text="Emoji o clase de icono")
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['order', 'name']
        verbose_name = "Quiz Genre"
        verbose_name_plural = "Quiz Genres"
    
    def __str__(self):
        return self.name


class PubQuizSession(models.Model):
    """Sesión de Pub Quiz (un evento completo)"""
    
    venue_name = models.CharField(max_length=200)
    host_name = models.CharField(max_length=200, default="Perfect DJ")
    date = models.DateTimeField(default=timezone.now)
    
    # Configuración del quiz
    total_rounds = models.IntegerField(default=6, help_text="4-8 rounds typical")
    questions_per_round = models.IntegerField(default=10)
    duration_minutes = models.IntegerField(default=120, help_text="90-180 minutos típico")
    
    # Estado
    STATUS_CHOICES = [
        ('registration', 'Registration Open'),
        ('voting', 'Genre Voting'),
        ('ready', 'Ready to Start'),
        ('in_progress', 'In Progress'),
        ('halftime', 'Halftime Break'),
        ('buzzer_round', 'Buzzer Round'),
        ('completed', 'Completed'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='registration')
    current_round = models.IntegerField(default=0)
    current_question = models.IntegerField(default=0)
    
    # Géneros seleccionados (basado en votación)
    selected_genres = models.ManyToManyField(QuizGenre, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Social media tracking
    social_hashtag = models.CharField(max_length=100, blank=True, default="#PerfectDJQuiz")
    social_handle = models.CharField(max_length=100, blank=True, default="@PerfectDJ")
    
    class Meta:
        ordering = ['-date']
        verbose_name = "Pub Quiz Session"
        verbose_name_plural = "Pub Quiz Sessions"
    
    def __str__(self):
        return f"{self.venue_name} - {self.date.strftime('%Y-%m-%d %H:%M')}"
    
    @property
    def total_questions(self):
        return self.total_rounds * self.questions_per_round


class QuizTeam(models.Model):
    """Equipo participante en el quiz"""
    
    session = models.ForeignKey(PubQuizSession, on_delete=models.CASCADE, related_name='teams')
    team_name = models.CharField(max_length=200)
    table_number = models.IntegerField(null=True, blank=True)
    num_players = models.IntegerField(default=4, help_text="4-6 jugadores típico")
    
    # Contacto y social media
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)
    social_handle = models.CharField(max_length=100, blank=True)
    followed_social = models.BooleanField(default=False, help_text="¿Siguió redes sociales?")
    
    # Votación de géneros (top 3-5)
    genre_votes = models.ManyToManyField(QuizGenre, blank=True, through='GenreVote')
    
    # Puntuación
    total_score = models.IntegerField(default=0)
    bonus_points = models.IntegerField(default=0, help_text="Por seguir redes, buzzers, etc.")
    
    # Timestamps
    registered_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-total_score', 'team_name']
        unique_together = ['session', 'team_name']
        verbose_name = "Quiz Team"
        verbose_name_plural = "Quiz Teams"
    
    def __str__(self):
        return f"{self.team_name} (Mesa {self.table_number or 'N/A'})"
    
    @property
    def final_score(self):
        return self.total_score + self.bonus_points


class GenreVote(models.Model):
    """Voto de un equipo por un género específico"""
    
    team = models.ForeignKey(QuizTeam, on_delete=models.CASCADE)
    genre = models.ForeignKey(QuizGenre, on_delete=models.CASCADE)
    priority = models.IntegerField(default=1, help_text="1 = favorito, 5 = menos favorito")
    
    class Meta:
        unique_together = ['team', 'genre']
        ordering = ['priority']


class QuizQuestion(models.Model):
    """Pregunta individual del quiz"""
    
    session = models.ForeignKey(PubQuizSession, on_delete=models.CASCADE, related_name='questions')
    genre = models.ForeignKey(QuizGenre, on_delete=models.SET_NULL, null=True)
    
    round_number = models.IntegerField()
    question_number = models.IntegerField()
    
    question_text = models.TextField()
    correct_answer = models.CharField(max_length=500)
    
    # Alternativas para respuestas similares
    alternative_answers = models.JSONField(default=list, blank=True)
    
    # Dificultad
    DIFFICULTY_CHOICES = [
        ('easy', 'Easy'),
        ('medium', 'Medium'),
        ('hard', 'Hard'),
    ]
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default='medium')
    
    # Para rondas especiales y tipos de respuesta
    QUESTION_TYPE_CHOICES = [
        ('multiple_choice', 'Multiple Choice'),
        ('written', 'Written Answer'),
        ('picture', 'Picture Round'),
        ('music', 'Music/Audio'),
        ('buzzer', 'Buzzer Question'),
        ('bonus', 'Bonus'),
    ]
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPE_CHOICES, default='multiple_choice')
    
    # Opciones para preguntas de opción múltiple (4 opciones: A, B, C, D)
    options = models.JSONField(
        default=dict, 
        blank=True,
        help_text="For multiple choice: {'A': 'Paris', 'B': 'London', 'C': 'Berlin', 'D': 'Madrid'}"
    )
    correct_option = models.CharField(
        max_length=1, 
        blank=True,
        help_text="For multiple choice: A, B, C, or D"
    )
    
    # Media adjunto (imágenes, audio)
    media_url = models.URLField(blank=True)
    
    # Puntos
    points = models.IntegerField(default=1)
    
    # Metadata
    hints = models.TextField(blank=True)
    fun_fact = models.TextField(blank=True, help_text="Dato curioso después de revelar respuesta")
    
    class Meta:
        ordering = ['round_number', 'question_number']
        unique_together = ['session', 'round_number', 'question_number']
    
    def __str__(self):
        return f"R{self.round_number}Q{self.question_number}: {self.question_text[:50]}"


class TeamAnswer(models.Model):
    """Respuesta de un equipo a una pregunta"""
    
    team = models.ForeignKey(QuizTeam, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(QuizQuestion, on_delete=models.CASCADE, related_name='team_answers')
    
    answer_text = models.CharField(max_length=500)
    is_correct = models.BooleanField(null=True, blank=True)
    points_awarded = models.IntegerField(default=0)
    
    # Para buzzers
    buzz_timestamp = models.DateTimeField(null=True, blank=True)
    buzz_order = models.IntegerField(null=True, blank=True, help_text="1 = primero en presionar")
    
    submitted_at = models.DateTimeField(auto_now_add=True)
    graded_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ['team', 'question']
        ordering = ['question__round_number', 'question__question_number']
    
    def __str__(self):
        return f"{self.team.team_name}: {self.answer_text}"


class BuzzerDevice(models.Model):
    """Dispositivo buzzer BLE para equipos (opcional)"""
    
    team = models.ForeignKey(QuizTeam, on_delete=models.CASCADE, related_name='buzzers')
    device_id = models.CharField(max_length=100, unique=True, help_text="UUID o MAC del buzzer")
    device_name = models.CharField(max_length=100, help_text="Ej: Team1Buzzer")
    
    is_paired = models.BooleanField(default=False)
    last_paired_at = models.DateTimeField(null=True, blank=True)
    
    # Estado de batería
    battery_level = models.IntegerField(null=True, blank=True, help_text="0-100%")
    
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Buzzer Device"
        verbose_name_plural = "Buzzer Devices"
    
    def __str__(self):
        return f"{self.device_name} ({self.team.team_name})"


class QuizRound(models.Model):
    """Información de una ronda específica"""
    
    session = models.ForeignKey(PubQuizSession, on_delete=models.CASCADE, related_name='rounds')
    round_number = models.IntegerField()
    
    genre = models.ForeignKey(QuizGenre, on_delete=models.SET_NULL, null=True)
    round_name = models.CharField(max_length=200)
    
    # Estado
    is_completed = models.BooleanField(default=False)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Configuración especial
    is_buzzer_round = models.BooleanField(default=False)
    is_halftime_before = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ['session', 'round_number']
        ordering = ['round_number']
    
    def __str__(self):
        return f"Round {self.round_number}: {self.round_name}"
