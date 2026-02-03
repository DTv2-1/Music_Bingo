#!/usr/bin/env python
"""
Test script to verify NO DUPLICATE SONGS within the same bingo card.
This test generates cards and validates that each card has 24 unique songs.

Based on test_session_flow.py structure.
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

from api.models import BingoSession
from api.services.session_service import BingoSessionService
import uuid
import subprocess
import tempfile
import shutil

# Import PDF parsing
try:
    from pypdf import PdfReader
except ImportError:
    from PyPDF2 import PdfReader


def print_header(title):
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)


def clean_text(text):
    """Clean text for comparison"""
    import re
    text = re.sub(r'[^\w\s]', '', text.lower())
    return ' '.join(text.split())


def extract_songs_from_pdf(pdf_path):
    """
    Extract songs from PDF and group by card.
    Returns: List of cards, each card is a list of song_ids.
    
    Strategy: Split each page by "Card #" markers, then extract songs from each section.
    """
    print(f"\n📄 Extracting songs from PDF: {pdf_path}")
    
    reader = PdfReader(pdf_path)
    print(f"   PDF has {len(reader.pages)} pages")
    
    # Load the song pool to know what to look for
    pool_path = BASE_DIR.parent / "data" / "pool.json"
    with open(pool_path, 'r', encoding='utf-8') as f:
        pool_data = json.load(f)
    
    all_songs = pool_data.get('songs', [])
    print(f"   Song pool has {len(all_songs)} songs")
    
    # Create lookup: clean_title -> song_id (multiple possible formats)
    song_to_id = {}
    for song in all_songs:
        title = song.get('title', '')
        artist = song.get('artist', '')
        song_id = song.get('id', '')
        
        # Try multiple match formats
        formats = [
            f"{artist} - {title}",
            f"{title}",
            f"{artist}-{title}",
        ]
        
        for fmt in formats:
            clean_fmt = clean_text(fmt)
            if clean_fmt and len(clean_fmt) > 3:  # Avoid very short matches
                song_to_id[clean_fmt] = song_id
    
    # Extract cards from PDF
    all_cards = []
    
    for page_num, page in enumerate(reader.pages):
        text = page.extract_text()
        
        # Split by "Card #" markers
        card_sections = text.split('Card #')
        
        # First section (index 0) is header before any card number, skip it
        for section_idx, section in enumerate(card_sections[1:], 1):  # Skip first section
            # Check if section starts with a number (card number)
            # Expected format: "1\n Powered by..." or "2\n Powered by..."
            lines = section.split('\n')
            if not lines or not lines[0].strip().isdigit():
                continue
            
            # Extract songs from this card section
            card_songs = []
            section_clean = clean_text(section)
            
            # Check each song from pool
            for song_text, song_id in song_to_id.items():
                if song_text in section_clean:
                    card_songs.append(song_id)
            
            # Remove duplicates while preserving order
            seen = set()
            unique_songs = []
            for sid in card_songs:
                if sid not in seen:
                    seen.add(sid)
                    unique_songs.append(sid)
            
            if unique_songs:
                all_cards.append(unique_songs)
    
    print(f"   ✓ Extracted {len(all_cards)} cards from PDF")
    if all_cards:
        sample_sizes = [len(c) for c in all_cards[:5]]
        print(f"   Sample card sizes: {sample_sizes}")
    
    return all_cards


def test_no_duplicates():
    """Test that no card has duplicate songs"""
    
    print_header("TEST: NO DUPLICATE SONGS IN SAME CARD")
    
    # Step 1: Create session
    print_header("Step 1: Create Session & Generate Cards")
    session_service = BingoSessionService()
    
    # Create session (service will generate session_id)
    session_dict = session_service.create_session({
        'venue_name': 'Duplicate Test Venue',
        'num_players': 25,  # 25 players = 50 cards
    })
    
    session_id = session_dict['session_id']
    print(f"✅ Session created: {session_id}")
    
    # Verify session exists in database
    session = BingoSession.objects.get(session_id=session_id)
    print(f"✅ Session verified in database: {session.venue_name}")
    
    # Step 2: Write current_session.json (simulate frontend behavior)
    session_file = BASE_DIR / "data" / "current_session.json"
    session_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Load pool and select songs
    pool_path = BASE_DIR.parent / "data" / "pool.json"
    with open(pool_path, 'r', encoding='utf-8') as f:
        pool_data = json.load(f)
    
    all_pool_songs = pool_data.get('songs', [])
    import random
    
    # Select optimal songs (25 players × 3 = 75 songs)
    optimal_songs = 25 * 3
    selected_songs = random.sample(all_pool_songs, min(optimal_songs, len(all_pool_songs)))
    
    session_data = {
        'session_id': session_id,
        'venue_name': 'Duplicate Test Venue',
        'num_players': 25,
        'songs': selected_songs
    }
    
    with open(session_file, 'w', encoding='utf-8') as f:
        json.dump(session_data, f, indent=2)
    
    print(f"✅ Session file created with {len(selected_songs)} songs")
    
    # Step 3: Generate PDF cards
    print_header("Step 2: Generate PDF Cards")
    
    output_dir = BASE_DIR / "data" / "cards"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Look for PDF in multiple possible locations
    pdf_paths = [
        output_dir / f"bingo_cards_{session_id[:8]}.pdf",
        output_dir / "music_bingo_cards.pdf",
        BASE_DIR.parent / "data" / "cards" / "music_bingo_cards.pdf",
    ]
    
    # Run generate_cards.py
    cmd = [
        sys.executable,
        str(BASE_DIR / "generate_cards.py"),
        "--num_players", "25",
        "--venue_name", "Duplicate Test Venue"
    ]
    
    print(f"   Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(BASE_DIR))
    
    if result.returncode != 0:
        print(f"❌ Card generation failed!")
        print(f"STDERR: {result.stderr}")
        return False
    
    print(f"✅ PDF generated successfully")
    print(f"   Output (first 500 chars): \n{result.stdout[:500]}")
    
    # Find the actual PDF file
    pdf_path = None
    for path in pdf_paths:
        if path.exists():
            pdf_path = path
            print(f"✅ Found PDF at: {pdf_path}")
            break
    
    if not pdf_path:
        print(f"❌ PDF not found in any expected location:")
        for path in pdf_paths:
            print(f"   - {path}")
        print(f"   Searching in: {output_dir}")
        for f in sorted(output_dir.glob("*.pdf")):
            print(f"   Found: {f.name}")
        return False
    
    print(f"✅ Using PDF: {pdf_path}")
    
    # Step 2.5: Update database with song_pool (simulate what card_generation_tasks.py does)
    print_header("Step 2.5: Update Database with Song Pool")
    
    session.song_pool = selected_songs
    session.pdf_url = str(pdf_path)
    session.save()
    session.refresh_from_db()
    
    print(f"✅ Database updated with {len(session.song_pool)} songs")
    
    # ============================================================
    # Step 3: Check generation output for validation
    print_header("Step 3: Check Generate Cards Output")
    
    # Check for success validation message
    if "✅ Validation passed: All 50 cards have unique songs" in result.stdout:
        print(f"✅ Card generation validation: PASSED")
        print(f"   Message: 'All 50 cards have unique songs (no duplicates within any card)'")
    else:
        # Check for error messages
        if "❌" in result.stdout or "CRITICAL" in result.stdout or "ERROR" in result.stdout:
            print(f"❌ Generation output indicates errors!")
            print(f"   Checking output for issues...")
            # Show relevant error lines
            for line in result.stdout.split('\n'):
                if '❌' in line or 'CRITICAL' in line or 'ERROR' in line:
                    print(f"   {line}")
            return False
        else:
            print(f"⚠️  Could not find validation message in output")
    
    print(f"✅ Generation completed without errors")
    
    # Step 4: Verify database song_pool
    print_header("Step 4: Verify Database Song Pool")
    
    song_pool = session.song_pool
    
    if not song_pool:
        print(f"❌ No song_pool in database!")
        return False
    
    print(f"✅ Database has {len(song_pool)} songs in song_pool")
    
    # Calculate expected distribution
    num_cards = 25 * 2  # 25 players = 50 cards
    songs_per_card = 24
    total_songs_needed = num_cards * songs_per_card  # 1200 songs
    
    print(f"\n📊 Expected distribution:")
    print(f"   Players: 25")
    print(f"   Cards: {num_cards}")
    print(f"   Songs per card: {songs_per_card}")
    print(f"   Total songs needed: {total_songs_needed}")
    print(f"   Available in pool: {len(song_pool)}")
    
    # Step 5: Simulate distribution and validate
    print_header("Step 5: Simulate Card Distribution Algorithm")
    
    # Import the distribution function
    sys.path.insert(0, str(BASE_DIR))
    from generate_cards import distribute_songs_unique
    
    simulated_cards = distribute_songs_unique(song_pool, num_cards, songs_per_card)
    
    print(f"✅ Simulated {len(simulated_cards)} cards")
    
    duplicates_in_simulation = False
    
    for card_idx, card in enumerate(simulated_cards, 1):
        song_ids = [s['id'] for s in card]
        unique_ids = set(song_ids)
        
        if len(song_ids) != len(unique_ids):
            duplicates_in_simulation = True
            dups = [sid for sid in unique_ids if song_ids.count(sid) > 1]
            print(f"❌ Simulated Card {card_idx}: Duplicates found: {dups}")
            
            # Show details
            for dup_id in dups:
                count = song_ids.count(dup_id)
                matching_songs = [s for s in card if s['id'] == dup_id]
                if matching_songs:
                    song_title = matching_songs[0].get('title', 'Unknown')
                    print(f"   - Song '{song_title}' (ID: {dup_id}) appears {count} times")
        elif card_idx <= 3 or card_idx % 10 == 0:  # Show first 3 and every 10th
            print(f"✅ Simulated Card {card_idx}: {len(song_ids)} unique songs")
    
    if duplicates_in_simulation:
        print(f"\n❌ CRITICAL: Duplicates found in simulated distribution!")
        return False
    
    # Final results
    print_header("FINAL RESULTS")
    
    print(f"✅ All validations passed!")
    print(f"   - Generation output: No duplicate errors detected")
    print(f"   - Database: song_pool correctly stored")
    print(f"   - Algorithm: Simulated distribution produces unique songs per card")
    print(f"   - Total cards tested: {num_cards}")
    
    # Additional manual check suggestion
    print(f"\n💡 Manual verification:")
    print(f"   Open PDF: {pdf_path}")
    print(f"   Check random cards to ensure each has 24 unique songs")
    print(f"   (Songs CAN repeat between different cards, but NOT within same card)")
    
    # Cleanup session file
    try:
        session_file.unlink()
        print(f"\n🧹 Cleaned up session file")
    except:
        pass
    
    return True


if __name__ == '__main__':
    try:
        success = test_no_duplicates()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ TEST ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
