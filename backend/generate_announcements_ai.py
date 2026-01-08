"""
generate_announcements_ai.py - OpenAI-powered Announcement Generator

Generates personalized DJ announcements for each song in the pool using OpenAI.
This is run ONCE to pre-generate all announcements, then they're used offline during games.

Requirements:
- OpenAI API key in .env (OPENAI_API_KEY)
- data/pool.json with songs
- ~$2-5 cost for 257 songs (one-time)

Output:
- data/announcements_ai.json (3 announcements per song)
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Check for OpenAI
try:
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
except ImportError:
    print("❌ Error: openai package not installed")
    print("Install with: pip install openai")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    print("Make sure OPENAI_API_KEY is set in backend/.env")
    sys.exit(1)

# Paths
BASE_DIR = Path(__file__).parent.parent
POOL_PATH = BASE_DIR / "data" / "pool.json"
OUTPUT_PATH = BASE_DIR / "data" / "announcements_ai.json"


def load_pool() -> List[Dict]:
    """Load song pool"""
    with open(POOL_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data.get('songs', [])


def generate_announcements_for_song(song: Dict) -> Dict[str, str]:
    """
    Generate 3 types of announcements for a song using OpenAI
    
    Returns:
        {
            "decade": "Era/decade context announcement",
            "trivia": "Fun fact/trivia announcement",
            "simple": "Short simple announcement"
        }
    """
    prompt = f"""You are a professional Music Bingo DJ. Generate 3 SHORT announcements for this song:

Song: "{song['title']}" by {song['artist']} ({song['release_year']})
Genre: {song.get('genre', 'Unknown')}

CRITICAL RULES:
1. NEVER mention the song title
2. NEVER mention the artist name
3. Keep each announcement to 1 short sentence (10-15 words max)
4. Give subtle hints about era, genre, or impact WITHOUT spoiling

Generate exactly 3 announcements in this JSON format:
{{
  "decade": "<Announcement about the era/decade, e.g., 'Here's a synth-driven anthem from the electronic 80s'>",
  "trivia": "<Generic fun fact, e.g., 'This track revolutionized music videos'>",
  "simple": "<Very short phrase, e.g., 'Next up' or 'Coming up' or 'Let's keep it going'>"
}}

Return ONLY valid JSON, no markdown, no explanation."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",  # Cheaper model
            messages=[
                {"role": "system", "content": "You are a Music Bingo DJ announcement generator. Output only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            max_tokens=200
        )
        
        content = response.choices[0].message.content.strip()
        
        # Remove markdown code blocks if present
        if content.startswith('```'):
            content = content.split('```')[1]
            if content.startswith('json'):
                content = content[4:]
            content = content.strip()
        
        announcements = json.loads(content)
        
        # Validate structure
        required_keys = ['decade', 'trivia', 'simple']
        if not all(key in announcements for key in required_keys):
            raise ValueError(f"Missing required keys: {required_keys}")
        
        return announcements
        
    except json.JSONDecodeError as e:
        print(f"  ⚠️  JSON parse error: {e}")
        print(f"  Response was: {content}")
        # Return fallback
        return {
            "decade": f"Here's a classic from the {song['release_year'][:3]}0s",
            "trivia": "This one's unforgettable",
            "simple": "Next song"
        }
    except Exception as e:
        print(f"  ⚠️  API error: {e}")
        # Return fallback
        return {
            "decade": f"Coming up from {song['release_year'][:3]}0s",
            "trivia": "You'll recognize this one",
            "simple": "Here we go"
        }


def main():
    print("=" * 70)
    print("MUSIC BINGO - AI ANNOUNCEMENT GENERATOR")
    print("=" * 70)
    print()
    
    # Load songs
    print("📂 Loading song pool...")
    songs = load_pool()
    print(f"✓ Loaded {len(songs)} songs")
    print()
    
    # Estimate cost
    estimated_cost = len(songs) * 0.01  # Rough estimate
    print(f"💰 Estimated cost: ${estimated_cost:.2f}")
    print(f"⏱️  Estimated time: {len(songs) // 2} minutes")
    print()
    
    confirm = input("Continue? (y/n): ").lower()
    if confirm != 'y':
        print("Cancelled.")
        return
    
    print()
    print("🤖 Generating announcements with OpenAI...")
    print("-" * 70)
    
    # Generate announcements
    announcements_db = {}
    errors = 0
    
    for i, song in enumerate(songs, 1):
        song_id = song.get('id', str(i))
        title = song.get('title', 'Unknown')
        artist = song.get('artist', 'Unknown')
        
        try:
            print(f"[{i}/{len(songs)}] {title} - {artist}...", end=' ', flush=True)
            
            announcements = generate_announcements_for_song(song)
            announcements_db[song_id] = announcements
            
            print("✓")
            
            # Show progress every 10 songs
            if i % 10 == 0:
                print(f"  Progress: {i}/{len(songs)} ({i*100//len(songs)}%)")
            
        except KeyboardInterrupt:
            print("\n\n⚠️  Interrupted by user")
            print(f"Generated {i-1}/{len(songs)} announcements so far")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            errors += 1
            # Continue with next song
    
    print()
    print("-" * 70)
    print(f"✓ Generated announcements for {len(announcements_db)}/{len(songs)} songs")
    
    if errors > 0:
        print(f"⚠️  {errors} errors (using fallback announcements)")
    
    # Save to file
    print()
    print(f"💾 Saving to {OUTPUT_PATH}...")
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(announcements_db, f, indent=2, ensure_ascii=False)
    
    file_size_kb = OUTPUT_PATH.stat().st_size / 1024
    
    print(f"✓ Saved successfully")
    print(f"  File size: {file_size_kb:.1f} KB")
    print(f"  Total announcements: {len(announcements_db) * 3}")
    print()
    
    # Show example
    if announcements_db:
        first_song_id = list(announcements_db.keys())[0]
        example = announcements_db[first_song_id]
        first_song = songs[0]
        
        print("📝 Example announcement for first song:")
        print(f"   Song: {first_song['title']} - {first_song['artist']}")
        print(f"   Decade: \"{example['decade']}\"")
        print(f"   Trivia: \"{example['trivia']}\"")
        print(f"   Simple: \"{example['simple']}\"")
    
    print()
    print("=" * 70)
    print("✅ COMPLETE! Announcements ready for use in game.")
    print("=" * 70)
    print()
    print("Next steps:")
    print("1. Commit announcements_ai.json to git")
    print("2. Deploy to server")
    print("3. Game will automatically use AI announcements")


if __name__ == "__main__":
    main()
