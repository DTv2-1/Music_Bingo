"""
test_pool.py - Unit tests for song pool generation
"""
import json
from pathlib import Path


def test_pool_has_minimum_songs():
    """Test that pool.json contains at least 250 songs"""
    with open("data/pool.json") as f:
        data = json.load(f)
    assert len(data["songs"]) >= 250, f"Pool has only {len(data['songs'])} songs, need at least 250"


def test_all_songs_have_preview_urls():
    """Test that all songs have valid preview URLs"""
    with open("data/pool.json") as f:
        data = json.load(f)
    for song in data["songs"]:
        assert "preview_url" in song, f"Song {song.get('title', 'Unknown')} missing preview_url"
        assert song["preview_url"].startswith("http"), f"Invalid preview URL for {song.get('title', 'Unknown')}"


def test_no_duplicate_songs():
    """Test that there are no duplicate songs in the pool"""
    with open("data/pool.json") as f:
        data = json.load(f)
    song_ids = [s["id"] for s in data["songs"]]
    assert len(song_ids) == len(set(song_ids)), "Found duplicate songs in pool"


def test_all_songs_have_required_fields():
    """Test that all songs have the required fields"""
    required_fields = ["id", "title", "artist", "preview_url", "artwork_url", "genre"]
    with open("data/pool.json") as f:
        data = json.load(f)
    for song in data["songs"]:
        for field in required_fields:
            assert field in song, f"Song {song.get('title', 'Unknown')} missing field: {field}"


if __name__ == "__main__":
    import sys
    
    try:
        test_pool_has_minimum_songs()
        print("✓ Test passed: Pool has minimum songs")
        
        test_all_songs_have_preview_urls()
        print("✓ Test passed: All songs have preview URLs")
        
        test_no_duplicate_songs()
        print("✓ Test passed: No duplicate songs")
        
        test_all_songs_have_required_fields()
        print("✓ Test passed: All songs have required fields")
        
        print("\n✅ All tests passed!")
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error running tests: {e}")
        sys.exit(1)
