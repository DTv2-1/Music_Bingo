"""
generate_cards.py - Bingo Card PDF Generator
Creates printable 5x5 bingo cards with Perfect DJ branding

Requirements:
- 50 unique cards (no duplicates)
- A4 portrait (210mm x 297mm)
- 5x5 grid with FREE center square
- Songs: "Artist - Title" or just "Title" if too long
- Professional typography (fits within cells)
- Optional: Perfect DJ logo at top
- Output: data/cards/music_bingo_cards.pdf

Card winning patterns supported:
- Any horizontal line (5 in a row)
- Any vertical line (5 in a column)
- Diagonal lines (2 options)
- Four corners
- Full house (entire card)
"""

import json
import random
from pathlib import Path
from typing import List, Dict, Set
from fpdf import FPDF

# Configuration
INPUT_POOL = Path("data/pool.json")
OUTPUT_DIR = Path("data/cards")
OUTPUT_FILE = OUTPUT_DIR / "music_bingo_cards.pdf"
NUM_CARDS = 50
GRID_SIZE = 5  # 5x5 bingo
LOGO_PATH = Path("frontend/assets/logo.png")  # Optional

# A4 dimensions in mm
PAGE_WIDTH = 210
PAGE_HEIGHT = 297

# Card layout for 2 cards per page (in mm)
CARD_MARGIN_TOP = 10
CARD_MARGIN_SIDE = 10
CARD_SPACING = 8  # Space between two cards on same page
CARD_WIDTH = PAGE_WIDTH - (2 * CARD_MARGIN_SIDE)
CARD_HEIGHT = (PAGE_HEIGHT - (2 * CARD_MARGIN_TOP) - CARD_SPACING) / 2  # Split page in half

# Grid calculations
CELL_WIDTH = CARD_WIDTH / GRID_SIZE
CELL_HEIGHT = (CARD_HEIGHT - 30) / GRID_SIZE  # Leave space for header and footer


class BingoCardPDF(FPDF):
    """Custom FPDF class for bingo cards with Perfect DJ branding"""
    
    def __init__(self):
        super().__init__(orientation='P', unit='mm', format='A4')
        self.set_auto_page_break(False)
        
    def header(self):
        """No page header - we'll draw headers per card"""
        pass


def load_song_pool(pool_path: Path) -> List[Dict]:
    """Load songs from pool.json"""
    with open(pool_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    songs = data.get("songs", [])
    
    if len(songs) < 24:  # Need at least 24 (25 - 1 FREE)
        raise ValueError(f"Pool has only {len(songs)} songs, need at least 24")
    
    print(f"✓ Loaded {len(songs)} songs from pool")
    return songs


def format_song_for_card(song: Dict, max_length: int = 35) -> str:
    """
    Format song as "Artist - Title" or just "Title" if too long
    
    Args:
        song: Song dict with title and artist
        max_length: Max characters before truncating
        
    Returns:
        Formatted string that fits in bingo cell
    """
    artist = song["artist"]
    title = song["title"]
    
    # Replace smart quotes and special characters with ASCII equivalents
    replacements = {
        '\u2019': "'",  # Right single quotation mark
        '\u2018': "'",  # Left single quotation mark
        '\u201c': '"',  # Left double quotation mark
        '\u201d': '"',  # Right double quotation mark
        '\u2013': '-',  # En dash
        '\u2014': '-',  # Em dash
        '\u2026': '...',  # Ellipsis
    }
    
    for old, new in replacements.items():
        artist = artist.replace(old, new)
        title = title.replace(old, new)
    
    # Try full format first
    full_format = f"{artist} - {title}"
    
    if len(full_format) <= max_length:
        return full_format
    
    # Try title only
    if len(title) <= max_length:
        return title
    
    # Try abbreviated artist
    artist_parts = artist.split()
    short_artist = artist_parts[0] if artist_parts else artist
    short_format = f"{short_artist} - {title}"
    
    if len(short_format) <= max_length:
        return short_format
    
    # Last resort: truncate title
    available_for_title = max_length - len(short_artist) - 3
    truncated_title = title[:available_for_title] + "..."
    return f"{short_artist} - {truncated_title}"


def generate_card_songs(all_songs: List[Dict], used_combinations: Set[frozenset]) -> List[str]:
    """
    Generate 24 unique songs for one card (25th is FREE)
    Ensures this exact combination hasn't been used before
    
    Args:
        all_songs: Pool of available songs
        used_combinations: Set of frozensets tracking used card combinations
        
    Returns:
        List of 24 formatted song strings
    """
    max_attempts = 100
    
    for attempt in range(max_attempts):
        # Randomly select 24 songs
        selected_songs = random.sample(all_songs, 24)
        song_ids = frozenset(s["id"] for s in selected_songs)
        
        # Check if this combination is unique
        if song_ids not in used_combinations:
            used_combinations.add(song_ids)
            
            # Format songs for display
            formatted = [format_song_for_card(song) for song in selected_songs]
            
            # Shuffle the order
            random.shuffle(formatted)
            
            return formatted
    
    # If we can't find unique combination (unlikely with 250+ songs)
    # Just return a random selection
    print(f"⚠ Warning: Could not find unique combination after {max_attempts} attempts")
    selected = random.sample(all_songs, 24)
    formatted = [format_song_for_card(song) for song in selected]
    random.shuffle(formatted)
    return formatted


def create_bingo_card(pdf: BingoCardPDF, songs: List[str], card_number: int, y_offset: float):
    """
    Draw one bingo card on current page
    
    Args:
        pdf: FPDF object
        songs: List of 24 formatted song strings
        card_number: Card number (1-50)
        y_offset: Vertical offset for this card (top or bottom of page)
    """
    # Insert FREE in center (position 12 in 0-indexed 24-item list)
    grid_songs = songs[:12] + ["FREE"] + songs[12:]
    
    # Starting position
    start_x = CARD_MARGIN_SIDE
    start_y = y_offset
    
    # Card header
    header_height = 15
    pdf.set_fill_color(102, 126, 234)  # Purple background
    pdf.rect(start_x, start_y, CARD_WIDTH, header_height, 'F')
    
    pdf.set_font('Helvetica', 'B', 16)
    pdf.set_text_color(255, 255, 255)  # White text
    pdf.set_xy(start_x, start_y + 3)
    pdf.cell(CARD_WIDTH, 8, 'MUSIC BINGO', align='C')
    
    pdf.set_font('Helvetica', '', 7)
    pdf.set_xy(start_x, start_y + 10)
    pdf.cell(CARD_WIDTH, 3, 'Mark the song when you hear it play!', align='C')
    
    # Reset text color
    pdf.set_text_color(0, 0, 0)
    
    # Adjust grid start to be below header
    grid_start_y = start_y + header_height + 2
    
    # Draw grid
    for row in range(GRID_SIZE):
        for col in range(GRID_SIZE):
            x = start_x + (col * CELL_WIDTH)
            y = grid_start_y + (row * CELL_HEIGHT)
            
            # Alternating background colors for visual interest
            if (row + col) % 2 == 0:
                pdf.set_fill_color(245, 245, 255)  # Very light blue
            else:
                pdf.set_fill_color(255, 250, 245)  # Very light orange
            
            # Cell with colored background
            pdf.rect(x, y, CELL_WIDTH, CELL_HEIGHT, 'FD')
            
            # Colored border
            pdf.set_draw_color(102, 126, 234)  # Purple border
            pdf.set_line_width(0.3)
            pdf.rect(x, y, CELL_WIDTH, CELL_HEIGHT)
            
            # Song text
            song_index = row * GRID_SIZE + col
            song_text = grid_songs[song_index]
            
            # Special formatting for FREE cell
            if song_text == "FREE":
                # Gold/yellow background for FREE
                pdf.set_fill_color(255, 215, 0)  # Gold
                pdf.rect(x, y, CELL_WIDTH, CELL_HEIGHT, 'F')
                pdf.set_draw_color(102, 126, 234)  # Purple border
                pdf.rect(x, y, CELL_WIDTH, CELL_HEIGHT)
                
                pdf.set_font('Helvetica', 'B', 20)
                pdf.set_text_color(139, 0, 139)  # Dark magenta
                pdf.set_xy(x, y + (CELL_HEIGHT / 2) - 3)
                pdf.cell(CELL_WIDTH, 6, song_text, align='C')
            else:
                # Dynamic font sizing based on text length
                if len(song_text) > 30:
                    font_size = 5
                    line_height = 2
                elif len(song_text) > 20:
                    font_size = 6
                    line_height = 2.5
                else:
                    font_size = 7
                    line_height = 3
                
                pdf.set_font('Helvetica', '', font_size)
                pdf.set_text_color(0, 0, 0)  # Black
                
                # Multi-line text if needed
                words = song_text.split()
                lines = []
                current_line = []
                
                for word in words:
                    test_line = ' '.join(current_line + [word])
                    # Rough estimate: each char is ~2mm at size 8
                    if len(test_line) * (font_size / 4) < (CELL_WIDTH - 4):
                        current_line.append(word)
                    else:
                        if current_line:
                            lines.append(' '.join(current_line))
                        current_line = [word]
                
                if current_line:
                    lines.append(' '.join(current_line))
                
                # Limit to 3 lines max
                lines = lines[:3]
                
                # Center text vertically
                total_height = len(lines) * line_height
                start_y_text = y + (CELL_HEIGHT - total_height) / 2
                
                for i, line in enumerate(lines):
                    pdf.set_xy(x + 2, start_y_text + (i * line_height))
                    pdf.cell(CELL_WIDTH - 4, line_height, line, align='C')
    
    # Perfect DJ footer (between grid and card number)
    footer_start_y = grid_start_y + (GRID_SIZE * CELL_HEIGHT) + 1
    pdf.set_font('Helvetica', 'I', 6)
    pdf.set_text_color(102, 126, 234)  # Purple text
    pdf.set_xy(CARD_MARGIN_SIDE, footer_start_y)
    pdf.cell(CARD_WIDTH, 3, 'Powered by Perfect DJ - perfectdj.co.uk', align='C')
    
    # Card number at bottom with colored background
    card_num_y = footer_start_y + 4
    pdf.set_fill_color(102, 126, 234)  # Purple background
    pdf.rect(CARD_MARGIN_SIDE, card_num_y, CARD_WIDTH, 6, 'F')
    
    pdf.set_font('Helvetica', 'B', 8)
    pdf.set_text_color(255, 255, 255)  # White text
    pdf.set_xy(CARD_MARGIN_SIDE, card_num_y + 1)
    pdf.cell(CARD_WIDTH, 4, f'Card #{card_number}', align='C')


def generate_cards(songs: List[Dict], num_cards: int, output_path: Path):
    """
    Generate PDF with all bingo cards (2 per page)
    
    Args:
        songs: Pool of songs
        num_cards: Number of cards to generate
        output_path: Where to save PDF
    """
    print(f"\n🎴 Generating {num_cards} bingo cards (2 per page)...")
    
    pdf = BingoCardPDF()
    used_combinations = set()
    
    for i in range(1, num_cards + 1):
        # Add new page for every 2 cards (or first card)
        if i == 1 or i % 2 == 1:
            pdf.add_page()
        
        # Generate unique songs for this card
        card_songs = generate_card_songs(songs, used_combinations)
        
        # Determine position (top or bottom of page)
        if i % 2 == 1:
            # Odd card number - top of page
            y_offset = CARD_MARGIN_TOP
        else:
            # Even card number - bottom of page
            y_offset = CARD_MARGIN_TOP + CARD_HEIGHT + CARD_SPACING
        
        # Draw the card
        create_bingo_card(pdf, card_songs, i, y_offset)
        
        if i % 10 == 0:
            print(f"  Generated {i}/{num_cards} cards...")
    
    # Save PDF
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(output_path))
    
    file_size_mb = output_path.stat().st_size / (1024 * 1024)
    num_pages = (num_cards + 1) // 2  # 2 cards per page, round up
    
    print(f"\n✓ PDF generated successfully!")
    print(f"  File: {output_path}")
    print(f"  Size: {file_size_mb:.2f} MB")
    print(f"  Cards: {num_cards}")
    print(f"  Pages: {num_pages} (2 cards per page)")
    print(f"\n💡 Print on A4 paper (portrait) for best results")
    print(f"💡 Cut along the middle to separate the two cards")


if __name__ == "__main__":
    print("=" * 60)
    print("MUSIC BINGO - CARD GENERATOR")
    print("=" * 60)
    print()
    
    # Load song pool
    songs = load_song_pool(INPUT_POOL)
    
    # Generate cards
    generate_cards(songs, NUM_CARDS, OUTPUT_FILE)
    
    print("\n" + "=" * 60)
    print("NEXT STEP: Open frontend/game.html to play")
    print("=" * 60)
