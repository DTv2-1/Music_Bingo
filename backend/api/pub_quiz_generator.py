"""
Generador de preguntas para Pub Quiz usando IA
Basado en los 50 géneros extraídos de los PDFs
"""

import json
import random
import os
from typing import List, Dict, Any
from openai import OpenAI


# 50 géneros extraídos del PDF 4
QUIZ_GENRES = [
    {"id": 1, "name": "General Knowledge", "icon": "🧠"},
    {"id": 2, "name": "Pop Music", "icon": "🎵"},
    {"id": 3, "name": "Movies & Film", "icon": "🎬"},
    {"id": 4, "name": "Television & Streaming Shows", "icon": "📺"},
    {"id": 5, "name": "80s Nostalgia", "icon": "📼"},
    {"id": 6, "name": "90s Nostalgia", "icon": "💿"},
    {"id": 7, "name": "2000s Throwback", "icon": "📱"},
    {"id": 8, "name": "2010s Pop Culture", "icon": "📲"},
    {"id": 9, "name": "Current Events & News (2025-2026)", "icon": "📰"},
    {"id": 10, "name": "Sports", "icon": "⚽"},
    {"id": 11, "name": "Geography & World Capitals", "icon": "🗺️"},
    {"id": 12, "name": "History", "icon": "📜"},
    {"id": 13, "name": "Science & Inventions", "icon": "🔬"},
    {"id": 14, "name": "Food & Drink", "icon": "🍔"},
    {"id": 15, "name": "Cocktails & Alcohol", "icon": "🍸"},
    {"id": 16, "name": "Celebrities & Gossip", "icon": "⭐"},
    {"id": 17, "name": "Disney & Pixar", "icon": "🏰"},
    {"id": 18, "name": "Harry Potter", "icon": "⚡"},
    {"id": 19, "name": "Superheroes & Marvel/DC", "icon": "🦸"},
    {"id": 20, "name": "Video Games", "icon": "🎮"},
    {"id": 21, "name": "Animals & Nature", "icon": "🦁"},
    {"id": 22, "name": "Mythology & Legends", "icon": "🐉"},
    {"id": 23, "name": "Literature & Books", "icon": "📚"},
    {"id": 24, "name": "Broadway & Musicals", "icon": "🎭"},
    {"id": 25, "name": "Art & Famous Paintings", "icon": "🎨"},
    {"id": 26, "name": "Tech & Gadgets", "icon": "💻"},
    {"id": 27, "name": "AI & Future Tech", "icon": "🤖"},
    {"id": 28, "name": "Memes & Viral Trends", "icon": "😂"},
    {"id": 29, "name": "Picture Round", "icon": "🖼️"},
    {"id": 30, "name": "Music Round (Name That Tune)", "icon": "🎼"},
    {"id": 31, "name": "Connections", "icon": "🔗"},
    {"id": 32, "name": "Anagrams & Wordplay", "icon": "🔤"},
    {"id": 33, "name": "Riddles & Brain Teasers", "icon": "🧩"},
    {"id": 34, "name": "What Happened Next?", "icon": "❓"},
    {"id": 35, "name": "Wrong Answers Only", "icon": "🤣"},
    {"id": 36, "name": "Hidden Theme Rounds", "icon": "🎯"},
    {"id": 37, "name": "Slogans & Brands", "icon": "™️"},
    {"id": 38, "name": "Toys & Games", "icon": "🧸"},
    {"id": 39, "name": "Fashion & Style", "icon": "👗"},
    {"id": 40, "name": "Holidays & Seasonal", "icon": "🎄"},
    {"id": 41, "name": "New York City Trivia", "icon": "🗽"},
    {"id": 42, "name": "Famous Quotes", "icon": "💬"},
    {"id": 43, "name": "True or False", "icon": "✅"},
    {"id": 44, "name": "Rapid Fire / Buzzer Questions", "icon": "⚡"},
    {"id": 45, "name": "70s Disco & Funk", "icon": "🕺"},
    {"id": 46, "name": "Hip-Hop & Rap", "icon": "🎤"},
    {"id": 47, "name": "Classic Rock", "icon": "🎸"},
    {"id": 48, "name": "Country Music", "icon": "🤠"},
    {"id": 49, "name": "Horror Movies", "icon": "👻"},
    {"id": 50, "name": "Space & Astronomy", "icon": "🚀"},
]


class PubQuizGenerator:
    """Generador de preguntas para Pub Quiz"""
    
    def __init__(self):
        self.genres = QUIZ_GENRES
    
    def get_all_genres(self) -> List[Dict]:
        """Retorna todos los géneros disponibles"""
        return self.genres
    
    def select_genres_by_votes(self, genre_votes: Dict[int, int], num_rounds: int = 6) -> List[Dict]:
        """
        Selecciona géneros basado en votación de equipos
        
        Args:
            genre_votes: Dict con {genre_id: vote_count}
            num_rounds: Número de rondas a generar
            
        Returns:
            Lista de géneros seleccionados
        """
        # Ordenar por votos
        sorted_genres = sorted(genre_votes.items(), key=lambda x: x[1], reverse=True)
        
        # Tomar los top votados
        selected_ids = [genre_id for genre_id, _ in sorted_genres[:num_rounds]]
        
        # Siempre incluir General Knowledge si no está
        if 1 not in selected_ids and num_rounds > 0:
            selected_ids[0] = 1
        
        # Obtener géneros completos
        selected = [g for g in self.genres if g['id'] in selected_ids]
        
        # Rellenar con random si faltan
        while len(selected) < num_rounds:
            random_genre = random.choice(self.genres)
            if random_genre not in selected:
                selected.append(random_genre)
        
        return selected[:num_rounds]
    
    def generate_ai_prompt_for_questions(
        self, 
        genre: Dict, 
        num_questions: int = 10,
        difficulty_mix: bool = True
    ) -> str:
        """
        Genera el prompt para que una IA genere preguntas
        
        Args:
            genre: Diccionario con info del género
            num_questions: Cantidad de preguntas
            difficulty_mix: Si debe mezclar dificultades
            
        Returns:
            Prompt para IA
        """
        difficulty_instruction = ""
        if difficulty_mix:
            difficulty_instruction = """
Mix difficulty levels:
- 3-4 easy questions (warm-up, broad knowledge)
- 4-5 medium questions (main challenge)
- 2-3 hard questions (expert level)
"""
        
        prompt = f"""Generate {num_questions} pub quiz questions for the genre: "{genre['name']}"

Requirements:
- Questions should be clear, concise, and fun
- Avoid multiple choice - encourage team discussion
- Include interesting fun facts for each answer
- Questions should work well when read aloud (TTS-friendly)
- Keep answers relatively short (1-5 words ideal)
- Make questions engaging for a bar/pub atmosphere
{difficulty_instruction}

Output format (JSON):
[
  {{
    "question": "Question text here",
    "answer": "Correct answer",
    "alternative_answers": ["Alternative 1", "Alternative 2"],
    "difficulty": "easy|medium|hard",
    "fun_fact": "Interesting fact about the answer",
    "hints": "Optional hint if teams are stuck"
  }}
]

Genre Context: {genre['name']}
Icon: {genre['icon']}

Generate exactly {num_questions} questions now.
"""
        return prompt
    
    def create_quiz_structure(
        self, 
        selected_genres: List[Dict],
        questions_per_round: int = 10,
        include_halftime: bool = True,
        include_buzzer_round: bool = False
    ) -> Dict[str, Any]:
        """
        Crea la estructura completa del quiz
        
        Returns:
            Diccionario con la estructura del quiz
        """
        rounds = []
        
        for i, genre in enumerate(selected_genres, 1):
            round_data = {
                "round_number": i,
                "genre": genre,
                "round_name": f"Round {i}: {genre['name']}",
                "questions_per_round": questions_per_round,
                "is_halftime_before": False,
                "is_buzzer_round": False,
            }
            
            # Halftime después de la mitad de rondas
            if include_halftime and i == len(selected_genres) // 2:
                round_data["is_halftime_before"] = True
            
            rounds.append(round_data)
        
        # Ronda final de buzzers si está habilitado
        if include_buzzer_round:
            buzzer_round = {
                "round_number": len(rounds) + 1,
                "genre": {"id": 44, "name": "Rapid Fire / Buzzer Questions", "icon": "⚡"},
                "round_name": "FINAL ROUND: Buzzer Challenge",
                "questions_per_round": 5,  # Menos preguntas, más rápidas
                "is_halftime_before": False,
                "is_buzzer_round": True,
            }
            rounds.append(buzzer_round)
        
        return {
            "total_rounds": len(rounds),
            "total_questions": sum(r["questions_per_round"] for r in rounds),
            "estimated_duration_minutes": len(rounds) * 15 + (15 if include_halftime else 0),
            "rounds": rounds,
        }
    
    def generate_sample_questions(self, genre_name: str, count: int = 10, question_types: dict = None) -> List[Dict]:
        """
        Genera preguntas usando OpenAI GPT-4
        question_types: {'multiple_choice': 0.7, 'written': 0.3}
        """
        # Default to 70% multiple choice, 30% written
        if question_types is None:
            question_types = {'multiple_choice': 0.7, 'written': 0.3}
        
        # Calculate how many of each type
        num_mc = int(count * question_types.get('multiple_choice', 0.7))
        num_written = count - num_mc
        
        questions = []
        
        # Generate multiple choice questions
        if num_mc > 0:
            mc_questions = self._generate_openai_questions(
                genre_name, 
                num_mc, 
                'multiple_choice'
            )
            questions.extend(mc_questions)
        
        # Generate written questions
        if num_written > 0:
            written_questions = self._generate_openai_questions(
                genre_name, 
                num_written, 
                'written'
            )
            questions.extend(written_questions)
        
        # Shuffle and assign question numbers
        random.shuffle(questions)
        for i, q in enumerate(questions, 1):
            q['question_number'] = i
        
        return questions
    
    def _generate_openai_questions(self, genre_name: str, count: int, question_type: str) -> List[Dict]:
        """
        Generate questions using OpenAI API
        """
        api_key = os.getenv('OPENAI_API_KEY', '')
        
        if not api_key:
            # Fallback to sample questions if no API key
            return self._get_fallback_questions(genre_name, count, question_type)
        
        try:
            # Initialize OpenAI client
            client = OpenAI(api_key=api_key)
            
            if question_type == 'multiple_choice':
                prompt = f"""Generate {count} multiple choice trivia questions about {genre_name}.

For each question, provide:
- A clear, engaging question
- 4 answer options (A, B, C, D)
- The correct answer letter
- A fun fact related to the answer
- Difficulty level (easy, medium, or hard)

Make questions diverse, interesting, and appropriate for a pub quiz audience.
Mix difficulty levels naturally.

Return ONLY a valid JSON array with this exact structure:
[
  {{
    "question": "Question text here?",
    "options": {{"A": "Option 1", "B": "Option 2", "C": "Option 3", "D": "Option 4"}},
    "correct_option": "A",
    "answer": "Correct answer text",
    "difficulty": "easy",
    "fun_fact": "Interesting fact about the answer"
  }}
]"""
            else:  # written
                prompt = f"""Generate {count} written answer trivia questions about {genre_name}.

For each question, provide:
- A clear, engaging question that requires a specific written answer
- The correct answer
- 2-4 alternative acceptable answers (variations, abbreviations, etc.)
- A fun fact related to the answer
- Difficulty level (easy, medium, or hard)

Make questions diverse, interesting, and appropriate for a pub quiz audience.
Mix difficulty levels naturally.

Return ONLY a valid JSON array with this exact structure:
[
  {{
    "question": "Question text here?",
    "answer": "Correct answer",
    "alternative_answers": ["Alt 1", "Alt 2"],
    "difficulty": "easy",
    "fun_fact": "Interesting fact about the answer"
  }}
]"""

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a professional pub quiz question writer. Generate only valid JSON. No markdown, no code blocks, just pure JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.8,
                max_tokens=2000
            )
            
            # Parse response
            content = response.choices[0].message.content.strip()
            
            # Remove markdown code blocks if present
            if content.startswith('```'):
                content = content.split('```')[1]
                if content.startswith('json'):
                    content = content[4:]
                content = content.strip()
            
            questions = json.loads(content)
            
            # Add question_type to each question
            for q in questions:
                q['question_type'] = question_type
                if question_type == 'written':
                    q['options'] = {}
                    q['correct_option'] = ''
            
            return questions
            
        except Exception as e:
            print(f"Error generating OpenAI questions: {e}")
            # Fallback to sample questions
            return self._get_fallback_questions(genre_name, count, question_type)
    
    def _get_fallback_questions(self, genre_name: str, count: int, question_type: str) -> List[Dict]:
        """
        Fallback sample questions if OpenAI fails
        """
        samples_mc = {
            "General Knowledge": [
                {
                    "question": "What is the capital of France?",
                    "answer": "Paris",
                    "options": {"A": "Paris", "B": "London", "C": "Berlin", "D": "Madrid"},
                    "correct_option": "A",
                    "question_type": "multiple_choice",
                    "alternative_answers": [],
                    "difficulty": "easy",
                    "fun_fact": "Paris is known as the City of Light",
                    "hints": "City of Light"
                },
                {
                    "question": "Which planet is known as the Red Planet?",
                    "answer": "Mars",
                    "options": {"A": "Venus", "B": "Mars", "C": "Jupiter", "D": "Saturn"},
                    "correct_option": "B",
                    "question_type": "multiple_choice",
                    "difficulty": "easy",
                    "fun_fact": "Mars appears red because of iron oxide on its surface",
                    "hints": "Fourth planet from the Sun"
                },
            ],
            "Pop Music": [
                {
                    "question": "Who sang 'Thriller'?",
                    "answer": "Michael Jackson",
                    "options": {"A": "Prince", "B": "Michael Jackson", "C": "Madonna", "D": "Stevie Wonder"},
                    "correct_option": "B",
                    "question_type": "multiple_choice",
                    "alternative_answers": ["MJ"],
                    "difficulty": "easy",
                    "fun_fact": "Thriller is the best-selling album of all time",
                    "hints": "King of Pop"
                },
            ],
        }
        
        samples_written = {
            "General Knowledge": [
                {
                    "question": "Name any European capital city",
                    "answer": "Various (Paris, London, Berlin, etc.)",
                    "question_type": "written",
                    "alternative_answers": ["Paris", "London", "Berlin", "Madrid", "Rome"],
                    "difficulty": "easy",
                    "fun_fact": "Europe has over 40 capital cities",
                    "hints": "Think of major European cities"
                },
            ],
            "Pop Music": [
                {
                    "question": "Name a Beatles song",
                    "answer": "Various Beatles songs",
                    "question_type": "written",
                    "alternative_answers": ["Hey Jude", "Let It Be", "Yesterday", "Help"],
                    "difficulty": "easy",
                    "fun_fact": "The Beatles have the most number-one hits in history",
                    "hints": "They were from Liverpool"
                },
            ],
        }
        
        base_questions_mc = samples_mc.get(genre_name, samples_mc["General Knowledge"])
        base_questions_written = samples_written.get(genre_name, samples_written["General Knowledge"])
        
        # Return questions of the requested type
        if question_type == 'multiple_choice':
            questions = []
            for i in range(count):
                q = base_questions_mc[i % len(base_questions_mc)].copy()
                questions.append(q)
        else:  # written
            questions = []
            for i in range(count):
                q = base_questions_written[i % len(base_questions_written)].copy()
                questions.append(q)
        
        return questions


def initialize_genres_in_db():
    """
    Función helper para inicializar los 50 géneros en la base de datos
    """
    from .pub_quiz_models import QuizGenre
    
    for i, genre_data in enumerate(QUIZ_GENRES, 1):
        QuizGenre.objects.get_or_create(
            name=genre_data["name"],
            defaults={
                "description": f"Quiz questions about {genre_data['name']}",
                "icon": genre_data["icon"],
                "order": i,
                "is_active": True,
            }
        )
    
    print(f"✅ Initialized {len(QUIZ_GENRES)} quiz genres")


if __name__ == "__main__":
    # Test
    generator = PubQuizGenerator()
    
    # Simular votación
    votes = {1: 10, 2: 8, 6: 7, 10: 5, 30: 4, 17: 3}
    
    selected = generator.select_genres_by_votes(votes, num_rounds=6)
    print("Selected genres:", [g["name"] for g in selected])
    
    structure = generator.create_quiz_structure(selected, include_buzzer_round=True)
    print(json.dumps(structure, indent=2))
