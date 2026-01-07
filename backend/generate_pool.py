"""
generate_pool.py - iTunes Search API Integration
Fetches popular songs with 30-second preview URLs for Music Bingo

Requirements:
- Fetch songs from multiple popular playlists/genres
- Ensure EVERY song has a valid previewUrl
- Deduplicate by track ID
- Include: title, artist, preview URL, artwork
- Save to data/pool.json

Target: 250 songs minimum
"""

import requests
import json
import time
from typing import List, Dict, Optional
from pathlib import Path

# Configuration
TARGET_SONG_COUNT = 250
OUTPUT_FILE = Path("data/pool.json")
REQUEST_DELAY = 0.5  # Seconds between requests (be nice to iTunes)

# iTunes Search API Configuration
ITUNES_SEARCH_BASE = "https://itunes.apple.com/search"

# Search strategies to get popular songs
SEARCH_QUERIES = [
    # Top global hits
    {"term": "top hits 2024", "limit": 50},
    {"term": "top hits 2023", "limit": 50},
    {"term": "classic rock hits", "limit": 30},
    {"term": "pop hits", "limit": 30},
    {"term": "dance hits", "limit": 30},
    {"term": "80s hits", "limit": 30},
    {"term": "90s hits", "limit": 30},
    
    # Recognizable artists (UK pub crowd)
    {"term": "Queen greatest hits", "limit": 20},
    {"term": "Beatles", "limit": 20},
    {"term": "ABBA", "limit": 15},
    {"term": "Elton John", "limit": 15},
    {"term": "David Bowie", "limit": 15},
    {"term": "Ed Sheeran", "limit": 15},
    {"term": "Adele", "limit": 15},
    {"term": "Coldplay", "limit": 15},
]


def fetch_songs_from_itunes(query: str, limit: int = 50) -> List[Dict]:
    """
    Fetch songs from iTunes Search API
    
    Args:
        query: Search term
        limit: Max results to fetch
        
    Returns:
        List of song dictionaries with previewUrl
    """
    params = {
        "term": query,
        "entity": "song",
        "limit": limit,
        "country": "GB",  # UK catalog for pub audience
        "media": "music"
    }
    
    try:
        response = requests.get(ITUNES_SEARCH_BASE, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Filter songs that have preview URLs
        songs_with_preview = [
            song for song in data.get("results", [])
            if song.get("previewUrl") and song.get("trackName") and song.get("artistName")
        ]
        
        print(f"✓ Fetched {len(songs_with_preview)}/{limit} songs from '{query}'")
        return songs_with_preview
        
    except requests.RequestException as e:
        print(f"✗ Error fetching '{query}': {e}")
        return []


def normalize_song_data(itunes_song: Dict) -> Dict:
    """
    Convert iTunes API response to our simplified format
    
    Args:
        itunes_song: Raw iTunes API song object
        
    Returns:
        Normalized song dict with only needed fields
    """
    return {
        "id": str(itunes_song.get("trackId")),
        "title": itunes_song.get("trackName", "").strip(),
        "artist": itunes_song.get("artistName", "").strip(),
        "preview_url": itunes_song.get("previewUrl"),
        "artwork_url": itunes_song.get("artworkUrl100", "").replace("100x100", "600x600"),
        "duration_ms": itunes_song.get("trackTimeMillis", 0),
        "genre": itunes_song.get("primaryGenreName", "Unknown"),
        "release_year": itunes_song.get("releaseDate", "")[:4] if itunes_song.get("releaseDate") else "Unknown"
    }


def generate_pool() -> List[Dict]:
    """
    Main function to generate song pool
    
    Returns:
        List of 250+ songs with previews
    """
    print(f"🎵 Starting iTunes song pool generation...")
    print(f"Target: {TARGET_SONG_COUNT} songs\n")
    
    all_songs = []
    seen_track_ids = set()
    
    for query_config in SEARCH_QUERIES:
        query = query_config["term"]
        limit = query_config["limit"]
        
        itunes_songs = fetch_songs_from_itunes(query, limit)
        
        # Normalize and deduplicate
        for song in itunes_songs:
            track_id = str(song.get("trackId"))
            
            if track_id not in seen_track_ids:
                seen_track_ids.add(track_id)
                normalized = normalize_song_data(song)
                all_songs.append(normalized)
        
        # Rate limiting - be nice to iTunes
        time.sleep(REQUEST_DELAY)
        
        print(f"Progress: {len(all_songs)}/{TARGET_SONG_COUNT} unique songs\n")
        
        # Stop early if we have enough
        if len(all_songs) >= TARGET_SONG_COUNT:
            break
    
    # Sort by artist then title for easier browsing
    all_songs.sort(key=lambda s: (s["artist"].lower(), s["title"].lower()))
    
    # Detect duplicate artists and mark songs
    all_songs = mark_duplicate_artists(all_songs)
    
    print(f"\n✓ Pool generation complete!")
    print(f"Total songs: {len(all_songs)}")
    print(f"Unique artists: {len(set(s['artist'] for s in all_songs))}")
    duplicate_count = sum(1 for s in all_songs if s.get('has_duplicate_artist'))
    print(f"Songs with duplicate artists: {duplicate_count}")
    
    return all_songs


def mark_duplicate_artists(songs: List[Dict]) -> List[Dict]:
    """
    Detect artists that appear more than once and mark their songs
    
    Args:
        songs: List of song dictionaries
        
    Returns:
        Updated songs list with has_duplicate_artist flag
    """
    from collections import Counter
    
    # Count occurrences of each artist
    artist_counts = Counter(song['artist'] for song in songs)
    
    # Mark songs where artist appears more than once
    for song in songs:
        song['has_duplicate_artist'] = artist_counts[song['artist']] > 1
    
    # Show stats
    duplicate_artists = [artist for artist, count in artist_counts.items() if count > 1]
    if duplicate_artists:
        print(f"\n📊 Artists with multiple songs ({len(duplicate_artists)}):")
        for artist in sorted(duplicate_artists)[:10]:  # Show first 10
            count = artist_counts[artist]
            print(f"  - {artist}: {count} songs")
        if len(duplicate_artists) > 10:
            print(f"  ... and {len(duplicate_artists) - 10} more")
    
    return songs


def save_pool(songs: List[Dict], output_path: Path):
    """Save song pool to JSON file"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump({
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_songs": len(songs),
            "songs": songs
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Pool saved to: {output_path}")
    print(f"File size: {output_path.stat().st_size / 1024:.1f} KB")


def validate_pool(pool_path: Path) -> bool:
    """
    Validate that pool file exists and has enough songs
    
    Returns:
        True if valid, False otherwise
    """
    if not pool_path.exists():
        print(f"✗ Pool file not found: {pool_path}")
        return False
    
    with open(pool_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    songs = data.get("songs", [])
    
    if len(songs) < TARGET_SONG_COUNT:
        print(f"✗ Pool has only {len(songs)} songs (need {TARGET_SONG_COUNT})")
        return False
    
    # Check that all songs have required fields
    for i, song in enumerate(songs[:10]):  # Check first 10
        required = ["id", "title", "artist", "preview_url"]
        missing = [field for field in required if not song.get(field)]
        if missing:
            print(f"✗ Song {i} missing fields: {missing}")
            return False
    
    print(f"✓ Pool validation passed: {len(songs)} songs")
    return True


if __name__ == "__main__":
    print("=" * 60)
    print("MUSIC BINGO - SONG POOL GENERATOR")
    print("Using: iTunes Search API (free)")
    print("=" * 60)
    print()
    
    # Generate pool
    songs = generate_pool()
    
    # Save to file
    save_pool(songs, OUTPUT_FILE)
    
    # Validate
    validate_pool(OUTPUT_FILE)
    
    print("\n" + "=" * 60)
    print("NEXT STEP: Run generate_cards.py to create bingo cards")
    print("=" * 60)
