"""
Centralized configuration for Music Bingo scripts
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
CARDS_DIR = DATA_DIR / "cards"
FRONTEND_DIR = PROJECT_ROOT / "frontend"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
CARDS_DIR.mkdir(exist_ok=True)

# iTunes API
ITUNES_SEARCH_BASE = "https://itunes.apple.com/search"
TARGET_SONG_COUNT = int(os.getenv('ITUNES_TARGET_SONGS', '250'))
ITUNES_COUNTRY = os.getenv('ITUNES_COUNTRY', 'GB')

# Card generation
NUM_CARDS = int(os.getenv('PDF_NUM_CARDS', '50'))
GRID_SIZE = int(os.getenv('PDF_GRID_SIZE', '5'))
PAGE_FORMAT = "A4"

# File paths
POOL_FILE = DATA_DIR / "pool.json"
ANNOUNCEMENTS_FILE = DATA_DIR / "announcements.json"
CARDS_PDF = CARDS_DIR / "music_bingo_cards.pdf"

# Perfect DJ branding
PERFECT_DJ_LOGO = FRONTEND_DIR / "assets" / "logo.png"
PERFECT_DJ_PRIMARY_COLOR = os.getenv('PERFECT_DJ_PRIMARY_COLOR', '#667eea')
PERFECT_DJ_SECONDARY_COLOR = os.getenv('PERFECT_DJ_SECONDARY_COLOR', '#764ba2')
