"""
regenerate_fallbacks.py - Regenerate failed AI announcements

Identifies and regenerates announcements that used fallback phrases.
"""

import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List
from dotenv import load_dotenv

# Load environment
load_dotenv()

try:
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
except ImportError:
    print("❌ Error: openai package not installed")
    sys.exit(1)

# Paths
BASE_DIR = Path(__file__).parent.parent
POOL_PATH = BASE_DIR / "data" / "pool.json"
OUTPUT_PATH = BASE_DIR / "data" / "announcements_ai.json"

# Fallback phrases to detect
FALLBACK_PHRASES = [
    "Here's a classic from the",
    "Coming up from",
    "This one's unforgettable",
    "You'll recognize this one",
    "Next song",
    "Here we go"
]


def load_pool() -> List[Dict]:
    """Load song pool"""
    with open(POOL_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data.get('songs', [])


def load_announcements() -> Dict:
    """Load existing announcements"""
    with open(OUTPUT_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def is_fallback(announcement: Dict) -> bool:
    """Check if announcement contains fallback phrases"""
    content = str(announcement.values())
    return any(phrase in content for phrase in FALLBACK_PHRASES)


def generate_announcements_for_song(song: Dict, retry: int = 1) -> Dict[str, str]:
    """Generate announcements with retry logic"""
    
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

    for attempt in range(retry):
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a Music Bingo DJ announcement generator. Output only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.9,  # Higher temperature for more variety
                max_tokens=200
            )
            
            content = response.choices[0].message.content.strip()
            
            # Remove markdown code blocks if present
            if content.startswith('```'):
                lines = content.split('\n')
                content = '\n'.join(lines[1:-1]) if len(lines) > 2 else content
                if content.startswith('json'):
                    content = content[4:].strip()
            
            # Remove any remaining backticks
            content = content.strip('`').strip()
            
            announcements = json.loads(content)
            
            # Validate structure
            required_keys = ['decade', 'trivia', 'simple']
            if all(key in announcements for key in required_keys):
                return announcements
            
            print(f"  ⚠️  Attempt {attempt + 1}: Missing keys, retrying...")
            time.sleep(1)
            
        except json.JSONDecodeError as e:
            print(f"  ⚠️  Attempt {attempt + 1}: JSON error, retrying...")
            time.sleep(1)
        except Exception as e:
            print(f"  ⚠️  Attempt {attempt + 1}: {e}, retrying...")
            time.sleep(1)
    
    # Final fallback
    return {
        "decade": f"Here's a hit from {song['release_year']}",
        "trivia": "This one's a crowd favorite",
        "simple": "Coming right up"
    }


def main():
    print("=" * 70)
    print("MUSIC BINGO - REGENERATE FALLBACK ANNOUNCEMENTS")
    print("=" * 70)
    print()
    
    # Load data
    print("📂 Loading data...")
    songs = load_pool()
    announcements = load_announcements()
    
    # Find songs with fallback announcements
    songs_dict = {song['id']: song for song in songs}
    to_regenerate = []
    
    for song_id, ann in announcements.items():
        if is_fallback(ann):
            if song_id in songs_dict:
                to_regenerate.append((song_id, songs_dict[song_id]))
    
    print(f"✓ Loaded {len(songs)} songs")
    print(f"✓ Found {len(to_regenerate)} announcements with fallbacks")
    print()
    
    if not to_regenerate:
        print("🎉 All announcements are perfect! Nothing to regenerate.")
        return
    
    # Show which songs will be regenerated
    print("🔄 Songs to regenerate:")
    for song_id, song in to_regenerate:
        print(f"  • {song['title']} - {song['artist']}")
    print()
    
    estimated_cost = len(to_regenerate) * 0.01
    print(f"💰 Estimated cost: ${estimated_cost:.2f}")
    print(f"⏱️  Estimated time: {len(to_regenerate) // 2} minutes")
    print()
    
    confirm = input("Continue? (y/n): ").lower()
    if confirm != 'y':
        print("Cancelled.")
        return
    
    print()
    print("🤖 Regenerating announcements with OpenAI...")
    print("-" * 70)
    
    # Regenerate
    success = 0
    for i, (song_id, song) in enumerate(to_regenerate, 1):
        title = song.get('title', 'Unknown')
        artist = song.get('artist', 'Unknown')
        
        print(f"[{i}/{len(to_regenerate)}] {title} - {artist}...", end=' ', flush=True)
        
        try:
            new_ann = generate_announcements_for_song(song, retry=3)
            
            # Verify it's not a fallback
            if not is_fallback(new_ann):
                announcements[song_id] = new_ann
                success += 1
                print("✓")
            else:
                print("⚠️  Still fallback")
            
            # Small delay to avoid rate limits
            time.sleep(0.5)
            
        except KeyboardInterrupt:
            print("\n\n⚠️  Interrupted by user")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print()
    print("-" * 70)
    print(f"✓ Successfully regenerated {success}/{len(to_regenerate)} announcements")
    
    # Save updated file
    print()
    print(f"💾 Saving to {OUTPUT_PATH}...")
    
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(announcements, f, indent=2, ensure_ascii=False)
    
    file_size_kb = OUTPUT_PATH.stat().st_size / 1024
    
    print(f"✓ Saved successfully")
    print(f"  File size: {file_size_kb:.1f} KB")
    print(f"  Total announcements: {len(announcements) * 3}")
    print()
    
    # Check remaining fallbacks
    remaining = sum(1 for ann in announcements.values() if is_fallback(ann))
    
    if remaining == 0:
        print("🎉 All announcements are now AI-generated!")
    else:
        print(f"⚠️  {remaining} announcements still using fallbacks")
        print("   You can run this script again to retry those.")
    
    print()
    print("=" * 70)
    print("✅ COMPLETE!")
    print("=" * 70)


if __name__ == "__main__":
    main()
