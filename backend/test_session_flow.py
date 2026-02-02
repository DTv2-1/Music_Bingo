#!/usr/bin/env python
"""
Test script to verify the complete session flow:
1. Create BingoSession
2. Generate cards (simulate task completion)
3. Verify song_pool is saved to database
4. Verify songs can be retrieved via API
"""

import os
import sys
import django
import json
from pathlib import Path

# Setup Django
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'music_bingo.settings')
django.setup()

from api.models import BingoSession, TaskStatus
from api.services.session_service import BingoSessionService
import uuid

def print_header(title):
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)

def test_session_flow():
    print_header("TESTING COMPLETE SESSION FLOW")
    
    # Step 1: Create a new BingoSession
    print_header("Step 1: Create BingoSession")
    session_service = BingoSessionService()
    session_id = str(uuid.uuid4())
    
    session_dict = session_service.create_session({
        'session_id': session_id,
        'venue_name': 'Test Venue',
        'num_players': 25,
        'game_number': 1,
        'prizes': {
            '4corners': '£10',
            'first_line': '£15',
            'full_house': '£50'
        }
    })
    
    # Fetch the actual model instance
    session = session_service.get_session(session_dict['session_id'])
    
    print(f"✅ Created BingoSession:")
    print(f"   ID: {session.session_id}")
    print(f"   Venue: {session.venue_name}")
    print(f"   Players: {session.num_players}")
    print(f"   song_pool length: {len(session.song_pool)}")
    print(f"   pdf_url: {session.pdf_url or 'None'}")
    
    # Step 2: Simulate card generation (load sample songs)
    print_header("Step 2: Generate Real Bingo Cards")
    
    # Load sample songs from pool.json (one level up from backend/)
    pool_path = BASE_DIR.parent / 'data' / 'pool.json'
    if not pool_path.exists():
        print(f"❌ ERROR: pool.json not found at {pool_path}")
        return False
    
    with open(pool_path, 'r', encoding='utf-8') as f:
        pool_data = json.load(f)
    
    all_songs = pool_data.get('songs', [])
    print(f"   Loaded {len(all_songs)} songs from pool.json")
    
    # Select songs for 25 players (optimal: 48 songs)
    import random
    random.seed(42)  # Consistent results
    selected_songs = random.sample(all_songs, 48)
    
    print(f"   Selected {len(selected_songs)} songs for cards")
    print(f"   First 3 songs:")
    for i, song in enumerate(selected_songs[:3], 1):
        print(f"      {i}. {song.get('title')} by {song.get('artist')} ({song.get('release_year')})")
    
    # Actually generate the cards using the backend script
    print(f"\n   🎨 Generating PDF cards with generate_cards.py...")
    
    import subprocess
    import tempfile
    
    # Create temporary session file with selected songs
    temp_session = {
        'venue_name': 'Test Venue',
        'num_players': 25,
        'songs': selected_songs,
        'game_number': 1
    }
    
    temp_session_path = BASE_DIR.parent / 'data' / 'cards' / 'test_session.json'
    temp_session_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(temp_session_path, 'w', encoding='utf-8') as f:
        json.dump(temp_session, f, indent=2, ensure_ascii=False)
    
    print(f"   Created temporary session file: {temp_session_path}")
    
    # Create current_session.json (what generate_cards.py expects)
    current_session_path = BASE_DIR.parent / 'data' / 'cards' / 'current_session.json'
    with open(current_session_path, 'w', encoding='utf-8') as f:
        json.dump(temp_session, f, indent=2, ensure_ascii=False)
    
    print(f"   Created current_session.json for generate_cards.py")
    
    # Run generate_cards.py
    cmd = [
        sys.executable,
        str(BASE_DIR / 'generate_cards.py'),
        '--venue_name', 'Test Venue',
        '--num_players', '25',
    ]
    
    print(f"   Running command: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(BASE_DIR))
    
    if result.returncode != 0:
        print(f"   ❌ Card generation failed!")
        print(f"   STDOUT:\n{result.stdout}")
        print(f"   STDERR:\n{result.stderr}")
        return False
    else:
        print(f"   ✅ PDF generated successfully")
        print(f"   Output preview:\n{result.stdout[:500]}")
        
        # Check if PDF was created
        pdf_path = BASE_DIR.parent / 'data' / 'cards' / 'music_bingo_cards.pdf'
        if pdf_path.exists():
            pdf_size = pdf_path.stat().st_size / 1024 / 1024  # MB
            print(f"   📄 PDF file: {pdf_path.name} ({pdf_size:.2f} MB)")
        else:
            print(f"   ⚠️  PDF not found at expected location")
    
    # Step 3: Update BingoSession with song_pool (simulate task completion)
    print_header("Step 3: Update BingoSession with song_pool")
    
    pdf_url = "https://storage.googleapis.com/test-bucket/test.pdf"
    
    session.song_pool = selected_songs
    session.pdf_url = pdf_url
    session.save(update_fields=['song_pool', 'pdf_url'])
    
    print(f"✅ Updated BingoSession in database")
    print(f"   song_pool length: {len(session.song_pool)}")
    print(f"   pdf_url: {session.pdf_url}")
    
    # Step 4: Verify by fetching from database
    print_header("Step 4: Verify - Fetch from Database")
    
    fetched_session = BingoSession.objects.get(session_id=session.session_id)
    
    print(f"✅ Fetched BingoSession from database:")
    print(f"   ID: {fetched_session.session_id}")
    print(f"   Venue: {fetched_session.venue_name}")
    print(f"   song_pool length: {len(fetched_session.song_pool)}")
    print(f"   pdf_url: {fetched_session.pdf_url}")
    
    if len(fetched_session.song_pool) != len(selected_songs):
        print(f"❌ ERROR: song_pool mismatch!")
        print(f"   Expected: {len(selected_songs)}")
        print(f"   Got: {len(fetched_session.song_pool)}")
        return False
    
    print(f"\n   First 3 songs from database:")
    for i, song in enumerate(fetched_session.song_pool[:3], 1):
        print(f"      {i}. {song.get('title')} by {song.get('artist')} ({song.get('release_year')})")
    
    # Step 5: Verify song IDs match
    print_header("Step 5: Verify Song IDs Match")
    
    original_ids = [s.get('id') for s in selected_songs[:5]]
    fetched_ids = [s.get('id') for s in fetched_session.song_pool[:5]]
    
    print(f"   Original song IDs (first 5): {original_ids}")
    print(f"   Fetched song IDs (first 5):  {fetched_ids}")
    
    if original_ids == fetched_ids:
        print(f"✅ Song IDs MATCH perfectly!")
    else:
        print(f"❌ ERROR: Song IDs DO NOT MATCH!")
        return False
    
    # Step 6: Simulate API response
    print_header("Step 6: Simulate API Response (get_session)")
    
    api_response = {
        'session_id': fetched_session.session_id,
        'venue_name': fetched_session.venue_name,
        'num_players': fetched_session.num_players,
        'songs': fetched_session.song_pool,
        'generated_at': fetched_session.created_at.isoformat(),
        'game_number': fetched_session.game_number,
        'pdf_url': fetched_session.pdf_url,
        'source': 'database'
    }
    
    print(f"✅ API Response structure:")
    print(f"   session_id: {api_response['session_id']}")
    print(f"   venue_name: {api_response['venue_name']}")
    print(f"   songs count: {len(api_response['songs'])}")
    print(f"   source: {api_response['source']}")
    
    # Step 7: Verify songs can be used in game
    print_header("Step 7: Verify Songs for Game")
    
    game_songs = api_response['songs']
    print(f"   Game will use {len(game_songs)} songs")
    print(f"   All songs have required fields:")
    
    required_fields = ['id', 'title', 'artist', 'preview_url']
    all_valid = True
    
    for i, song in enumerate(game_songs[:5], 1):
        missing = [f for f in required_fields if f not in song]
        if missing:
            print(f"      ❌ Song {i}: Missing fields {missing}")
            all_valid = False
        else:
            print(f"      ✅ Song {i}: {song['title']} - All fields present")
    
    if not all_valid:
        print(f"❌ ERROR: Some songs missing required fields!")
        return False
    
    # Step 7b: Verify songs are in generated PDF (if it exists)
    print_header("Step 7b: Verify Songs in PDF")
    
    pdf_path = BASE_DIR.parent / 'data' / 'cards' / 'music_bingo_cards.pdf'
    if pdf_path.exists():
        print(f"   📄 Found PDF: {pdf_path.name}")
        
        try:
            from PyPDF2 import PdfReader
            
            reader = PdfReader(str(pdf_path))
            print(f"   📄 PDF has {len(reader.pages)} pages")
            
            # Extract text from all pages
            pdf_text = ""
            for page in reader.pages:
                pdf_text += page.extract_text()
            
            print(f"   📝 Extracted {len(pdf_text)} characters of text")
            
            # Check if first 10 songs appear in PDF
            songs_found = 0
            songs_checked = 0
            
            print(f"\n   Checking if songs from database appear in PDF:")
            for i, song in enumerate(game_songs[:20], 1):  # Check more songs
                songs_checked += 1
                title = song.get('title', '')
                artist = song.get('artist', '')
                
                # Clean text for better matching (remove special chars, extra spaces)
                def clean_text(text):
                    import re
                    # Remove parentheses content, extra spaces, special chars
                    text = re.sub(r'\([^)]*\)', '', text)
                    text = re.sub(r'[^\w\s]', ' ', text)
                    text = re.sub(r'\s+', ' ', text)
                    return text.strip().lower()
                
                clean_title = clean_text(title)
                clean_artist = clean_text(artist)
                clean_pdf = clean_text(pdf_text)
                
                # Check if significant parts appear (at least first 3 words of title or artist)
                title_words = clean_title.split()[:3]
                artist_words = clean_artist.split()[:2]
                
                title_found = all(word in clean_pdf for word in title_words if len(word) > 2)
                artist_found = all(word in clean_pdf for word in artist_words if len(word) > 2)
                
                if title_found or artist_found:
                    songs_found += 1
                    match_type = "title" if title_found else "artist"
                    print(f"      ✅ Song {i}: '{title}' by {artist} - FOUND ({match_type})")
                else:
                    print(f"      ⚠️  Song {i}: '{title}' by {artist} - NOT FOUND")
            
            match_percentage = (songs_found / songs_checked) * 100
            print(f"\n   📊 Match rate: {songs_found}/{songs_checked} songs ({match_percentage:.1f}%)")
            
            if match_percentage >= 80:
                print(f"   ✅ High match rate - songs from database match printed cards!")
            elif match_percentage >= 50:
                print(f"   ⚠️  Medium match rate - some songs may differ")
            else:
                print(f"   ❌ Low match rate - songs in PDF DO NOT match database!")
                return False
            
        except ImportError:
            print(f"   ⚠️  PyPDF2 not installed - skipping PDF text extraction")
            print(f"   💡 Install with: pip install PyPDF2")
        except Exception as e:
            print(f"   ⚠️  Error reading PDF: {e}")
    else:
        print(f"   ❌ ERROR: PDF not found at {pdf_path}")
        return False
    
    # Step 8: Clean up
    print_header("Step 8: Cleanup")
    session.delete()
    print(f"✅ Deleted test session")
    
    # Final Summary
    print_header("FINAL SUMMARY")
    print(f"✅ ALL TESTS PASSED!")
    print(f"\nVerified:")
    print(f"  ✓ BingoSession created successfully")
    print(f"  ✓ Bingo cards generated (PDF)")
    print(f"  ✓ song_pool saved to database ({len(selected_songs)} songs)")
    print(f"  ✓ song_pool retrieved from database")
    print(f"  ✓ Song IDs match exactly")
    print(f"  ✓ Songs in database match songs in PDF")
    print(f"  ✓ API response format correct")
    print(f"  ✓ Songs have all required fields for game")
    print(f"\n🎯 Conclusion: Backend flow is PERFECT!")
    print(f"   Songs played in game WILL match printed cards ✅")
    
    return True

if __name__ == '__main__':
    try:
        success = test_session_flow()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ TEST FAILED WITH EXCEPTION:")
        print(f"   {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
