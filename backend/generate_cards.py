"""
generate_cards.py - Professional Bingo Card PDF Generator with ReportLab
Creates printable 5x5 bingo cards with pub branding, logos, and QR codes

Features:
- High-quality pub logo placement
- QR codes for social media
- Professional typography and layout
- 50 unique cards per game
- A4 portrait format
- Perfect DJ branding
"""

import json
import random
import os
import sys
import argparse
from pathlib import Path
from typing import List, Dict, Set, Optional
import requests
from io import BytesIO
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor
import tempfile
import psutil

# ReportLab imports
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.pdfgen import canvas

# QR Code generation
import qrcode

# PDF Merging
try:
    from pypdf import PdfWriter, PdfReader
except ImportError:
    from PyPDF2 import PdfWriter, PdfReader

# Configuration
SCRIPT_DIR = Path(__file__).parent
# In Docker, everything is in /app/, locally need parent
PROJECT_ROOT = SCRIPT_DIR.parent if (SCRIPT_DIR.parent / "data").exists() else SCRIPT_DIR
INPUT_POOL = PROJECT_ROOT / "data" / "pool.json"
OUTPUT_DIR = PROJECT_ROOT / "data" / "cards"
# OUTPUT_FILE is now generated dynamically per session (see generate_cards function)
NUM_CARDS = 50  # Back to 50 with Professional XS resources
GRID_SIZE = 5  # 5x5 bingo
SONGS_PER_CARD = 24  # 25 cells - 1 FREE

# Perfect DJ Branding - Check multiple possible locations (PDF version)
PERFECT_DJ_LOGO_PATHS = [
    PROJECT_ROOT / "frontend" / "assets" / "perfect-dj-logo-pdf.png",  # Local dev (PDF version)
    PROJECT_ROOT / "frontend" / "assets" / "perfect-dj-logo.png",      # Fallback
    PROJECT_ROOT / "assets" / "perfect-dj-logo.png",                   # Docker if copied
    Path("/app/frontend/assets/perfect-dj-logo-pdf.png"),             # Docker absolute
    Path("/app/frontend/assets/perfect-dj-logo.png"),                 # Docker fallback
]
WEBSITE_URL = "www.perfectdj.co.uk"


def calculate_optimal_songs(num_players: int) -> int:
    """Calculate optimal number of songs based on players"""
    base_songs = int(num_players * 3)
    base_songs = max(base_songs, 30)
    base_songs = min(base_songs, 150)
    return base_songs


def distribute_songs_unique(all_songs: List[Dict], num_cards: int, songs_per_card: int) -> List[List[Dict]]:
    """
    Distribute songs uniquely across all cards - NO DUPLICATE SONGS WITHIN A SINGLE CARD
    Each card must have completely unique songs (no song appears twice on same card)
    
    CRITICAL: This function GUARANTEES that each card has exactly songs_per_card UNIQUE songs.
    
    Args:
        all_songs: Full pool of available songs
        num_cards: Number of bingo cards to generate
        songs_per_card: Songs per card (24 for 5x5 grid with FREE space)
    
    Returns:
        List of card song lists, each with UNIQUE songs (no duplicates within a card)
    """
    total_songs_needed = num_cards * songs_per_card
    
    # Validate we have enough songs to create cards with unique songs
    if len(all_songs) < songs_per_card:
        raise ValueError(f"Cannot create cards: need {songs_per_card} unique songs per card but only have {len(all_songs)}")
    
    # Create an infinite pool by repeating songs
    print(f"⚠️  Warning: Need {total_songs_needed} songs but only have {len(all_songs)}")
    print(f"   Songs will appear on multiple cards (but NEVER twice on same card)")
    
    # Calculate how many times we need to repeat the pool
    times_to_repeat = (total_songs_needed // len(all_songs)) + 2  # +2 for safety margin
    
    # Create extended pool with deep copies
    extended_pool = []
    for repeat_idx in range(times_to_repeat):
        for song in all_songs:
            song_copy = song.copy()
            # Add a unique marker so we can track which "copy" this is
            song_copy['_copy_index'] = repeat_idx
            extended_pool.append(song_copy)
    
    # Shuffle the extended pool
    random.shuffle(extended_pool)
    
    # Distribute songs to cards
    card_songs = []
    pool_index = 0
    
    for card_idx in range(num_cards):
        card = []
        used_song_ids = set()
        attempts = 0
        max_attempts = len(extended_pool) * 2
        
        while len(card) < songs_per_card and attempts < max_attempts:
            # Wrap around if we reach the end of the pool
            if pool_index >= len(extended_pool):
                pool_index = 0
                random.shuffle(extended_pool)  # Re-shuffle for variety
            
            song = extended_pool[pool_index]
            song_id = song.get('id')
            
            # Check if this song ID is already in the current card
            if song_id not in used_song_ids:
                # Add to card
                card.append(song)
                used_song_ids.add(song_id)
                # Remove from pool to avoid using again
                extended_pool.pop(pool_index)
            else:
                # Skip this song, move to next
                pool_index += 1
            
            attempts += 1
        
        # Validate we got enough songs
        if len(card) != songs_per_card:
            raise ValueError(f"CRITICAL: Card {card_idx + 1} only has {len(card)} songs (expected {songs_per_card}). This should never happen!")
        
        # Validate no duplicates
        card_ids = [s.get('id') for s in card]
        if len(card_ids) != len(set(card_ids)):
            raise ValueError(f"CRITICAL: Card {card_idx + 1} has duplicate song IDs! This should never happen!")
        
        card_songs.append(card)
    
    return card_songs


def load_pool() -> List[Dict]:
    """Load song pool from JSON"""
    with open(INPUT_POOL, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data.get('songs', [])


def format_song_title(song: Dict, max_length: int = 45) -> str:
    """Format song title to fit in cell"""
    title = song.get('title', 'Unknown')
    artist = song.get('artist', '')
    
    # Try full format first
    full = f"{artist} - {title}" if artist else title
    
    if len(full) <= max_length:
        return full
    
    # Try title only
    if len(title) <= max_length:
        return title
    
    # Truncate title
    return title[:max_length-3] + "..."


def generate_qr_code(url: str, size: int = 150) -> Optional[BytesIO]:
    """Generate QR code image as BytesIO"""
    if not url:
        return None
    
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=2,
        )
        qr.add_data(url)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Save to BytesIO
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        return buffer
    except Exception as e:
        print(f"Error generating QR code: {e}")
        return None


def download_logo(url: str) -> Optional[BytesIO]:
    """Download logo from URL, data URI, or local file"""
    if not url:
        return None
    
    # Handle data URI (base64 encoded images)
    if url.startswith('data:'):
        try:
            import base64
            print(f"🔍 Detected data URI in download_logo")
            # Extract base64 data from data URI
            # Format: data:image/png;base64,iVBORw0KG...
            header, encoded = url.split(',', 1)
            image_data = base64.b64decode(encoded)
            print(f"✅ Decoded base64 logo: {len(image_data)} bytes")
            return BytesIO(image_data)
        except Exception as e:
            print(f"Error decoding data URI logo: {e}")
            return None
    
    # Check if it's a local file path
    if not url.startswith('http'):
        try:
            # If path starts with /data/, it's relative to project root
            if url.startswith('/data/'):
                url = str(PROJECT_ROOT / url.lstrip('/'))
            
            with open(url, 'rb') as f:
                return BytesIO(f.read())
        except Exception as e:
            print(f"Error loading local logo: {e}")
            return None
    
    # Download from URL
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return BytesIO(response.content)
    except Exception as e:
        print(f"Error downloading logo: {e}")
    
    return None


def get_logo_with_aspect_ratio(logo_buffer: BytesIO, max_width: float = 40, max_height: float = 20) -> Optional[Image]:
    """Create ReportLab Image with preserved aspect ratio"""
    try:
        from PIL import Image as PILImage
        
        # Open image to get dimensions
        pil_img = PILImage.open(logo_buffer)
        orig_width, orig_height = pil_img.size
        
        # Convert to RGB if necessary (removes transparency issues)
        if pil_img.mode in ('RGBA', 'LA', 'P'):
            # Create white background
            background = PILImage.new('RGB', pil_img.size, (255, 255, 255))
            if pil_img.mode == 'P':
                pil_img = pil_img.convert('RGBA')
            if 'A' in pil_img.mode:
                background.paste(pil_img, mask=pil_img.split()[-1])
            else:
                background.paste(pil_img)
            pil_img = background
        elif pil_img.mode != 'RGB':
            pil_img = pil_img.convert('RGB')
        
        # Calculate aspect ratio
        aspect = orig_width / orig_height
        
        # Calculate new dimensions maintaining aspect ratio
        if aspect > (max_width / max_height):
            # Width is the limiting factor
            new_width = max_width * mm
            new_height = (max_width / aspect) * mm
        else:
            # Height is the limiting factor
            new_height = max_height * mm
            new_width = (max_height * aspect) * mm
        
        # Save to new buffer as RGB JPEG (much faster)
        output_buffer = BytesIO()
        pil_img.save(output_buffer, format='JPEG', quality=95)
        output_buffer.seek(0)
        
        # Create ReportLab Image with correct dimensions
        rl_image = Image(output_buffer, width=new_width, height=new_height)
        rl_image.hAlign = 'CENTER'
        
        return rl_image
    except Exception as e:
        print(f"Error processing logo aspect ratio: {e}")
        return None


def create_bingo_card(songs: List[Dict], card_num: int, venue_name: str, 
                     pub_logo_path: str = None, social_media_url: str = None, 
                     include_qr: bool = False, game_number: int = 1, game_date: str = None,
                     qr_buffer: BytesIO = None, 
                     prize_4corners: str = '', prize_first_line: str = '', prize_full_house: str = '') -> List:
    """Create a single bingo card with ReportLab elements"""
    
    # CRITICAL: Validate song count
    expected_songs = 24  # 5x5 grid - 1 FREE space
    if len(songs) != expected_songs:
        raise ValueError(f"Card {card_num}: Expected {expected_songs} songs but got {len(songs)}")
    
    elements = []
    
    # Styles
    styles = getSampleStyleSheet()
    
    # Header style - LARGER title as requested
    header_style = ParagraphStyle(
        'CustomHeader',
        parent=styles['Heading1'],
        fontSize=18,  # Reduced from 24 to 18 to save space
        textColor=colors.black,  # Black for B&W printing
        alignment=TA_CENTER,
        spaceAfter=2*mm,  # Reduced from 3mm to 2mm
        fontName='Helvetica-Bold',
    )
    
    # Venue style
    venue_style = ParagraphStyle(
        'Venue',
        parent=styles['Normal'],
        fontSize=8,  # Reduced from 10 to 8
        textColor=colors.HexColor('#4a5568'),
        alignment=TA_CENTER,
        spaceAfter=1*mm,  # Reduced
    )
    
    # Date and game number style
    date_style = ParagraphStyle(
        'DateGame',
        parent=styles['Normal'],
        fontSize=7,  # Reduced from 9 to 7
        textColor=colors.HexColor('#4a5568'),
        alignment=TA_CENTER,
        spaceAfter=2*mm,  # Reduced from 3mm to 2mm
    )
    
    # --- HEADER SECTION WITH LOGOS ---
    # Always try to load Perfect DJ logo first
    perfect_dj_logo = None
    try:
        for logo_path in PERFECT_DJ_LOGO_PATHS:
            if logo_path.exists():
                perfect_dj_logo = Image(str(logo_path), width=20*mm, height=20*mm)
                print(f"✅ Loaded Perfect DJ logo from: {logo_path}")
                break
    except Exception as e:
        print(f"⚠️ Warning: Could not load Perfect DJ logo: {e}")
    
    # Load pub logo if provided
    pub_logo = None
    if pub_logo_path:
        try:
            from PIL import Image as PILImage
            import base64
            import io
            
            # Handle data URI (base64 encoded images)
            if pub_logo_path.startswith('data:'):
                print(f"🔍 Detected data URI for pub logo")
                # Extract base64 data from data URI
                # Format: data:image/png;base64,iVBORw0KG...
                header, encoded = pub_logo_path.split(',', 1)
                image_data = base64.b64decode(encoded)
                pil_img = PILImage.open(io.BytesIO(image_data))
                print(f"✅ Decoded base64 pub logo: {pil_img.format} {pil_img.size}")
            else:
                # Handle file path or URL
                pil_img = PILImage.open(pub_logo_path)
                print(f"✅ Opened pub logo from path: {pub_logo_path}")
            
            # Get original dimensions
            orig_width, orig_height = pil_img.size
            aspect = orig_width / orig_height
            
            # Logo size
            max_width = 35  # Logo width
            max_height = 18  # Logo height
            
            if aspect > (max_width / max_height):
                new_width = max_width * mm
                new_height = (max_width / aspect) * mm
            else:
                new_height = max_height * mm
                new_width = (max_height * aspect) * mm
            
            # For data URIs, create temporary BytesIO object for ReportLab
            if pub_logo_path.startswith('data:'):
                # ReportLab Image can accept a PIL Image or file path
                # We need to convert PIL Image to something ReportLab can use
                img_buffer = io.BytesIO()
                pil_img.save(img_buffer, format='PNG')
                img_buffer.seek(0)
                pub_logo = Image(img_buffer, width=new_width, height=new_height)
            else:
                pub_logo = Image(pub_logo_path, width=new_width, height=new_height)
            
            print(f"✅ Successfully loaded pub logo with dimensions: {new_width/mm:.1f}mm x {new_height/mm:.1f}mm")
        except Exception as e:
            print(f"⚠️ Error loading pub logo: {e}")
            import traceback
            traceback.print_exc()
    
    # Create header table based on available logos
    if pub_logo and perfect_dj_logo:
        # Both logos: pub left, title center, Perfect DJ right
        header_table = Table(
            [[pub_logo, Paragraph(f"<b>MUSIC BINGO</b><br/><font size='8'>{venue_name}</font>", header_style), perfect_dj_logo]], 
            colWidths=[40*mm, 110*mm, 40*mm]
        )
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (1, 0), 'CENTER'),
            ('ALIGN', (2, 0), (2, 0), 'RIGHT'),
        ]))
    elif pub_logo:
        # Only pub logo: left side, title center
        header_table = Table(
            [[pub_logo, Paragraph(f"<b>MUSIC BINGO</b><br/><font size='8'>{venue_name}</font>", header_style), '']], 
            colWidths=[40*mm, 110*mm, 40*mm]
        )
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (1, 0), 'CENTER'),
        ]))
    elif perfect_dj_logo:
        # Only Perfect DJ logo: right side, title center
        header_table = Table(
            [['', Paragraph(f"<b>MUSIC BINGO</b><br/><font size='8'>{venue_name}</font>", header_style), perfect_dj_logo]], 
            colWidths=[40*mm, 110*mm, 40*mm]
        )
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (1, 0), (1, 0), 'CENTER'),
            ('ALIGN', (2, 0), (2, 0), 'RIGHT'),
        ]))
    else:
        # No logos at all: just centered title
        header_table = Table(
            [['', Paragraph(f"<b>MUSIC BINGO</b><br/><font size='10'>{venue_name}</font>", header_style), '']], 
            colWidths=[40*mm, 110*mm, 40*mm]
        )
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (1, 0), (1, 0), 'CENTER'),
        ]))
    
    elements.append(header_table)
    elements.append(Spacer(1, 1*mm))
    
    # Date and game number
    if not game_date:
        from datetime import datetime
        game_date = datetime.now().strftime("%A, %B %d, %Y")
    
    date_text = Paragraph(f"<b>{game_date}</b> • Game #{game_number}", date_style)
    elements.append(date_text)
    elements.append(Spacer(1, 1*mm))  # Reduced from 2mm to 1mm
    
    # --- BINGO GRID ---
    # Create 5x5 grid data
    grid_data = []
    song_index = 0
    
    for row in range(GRID_SIZE):
        row_data = []
        for col in range(GRID_SIZE):
            # Center cell is FREE
            if row == 2 and col == 2:
                cell_style = ParagraphStyle(
                    'FreeCell',
                    parent=styles['Normal'],
                    fontSize=14,
                    textColor=colors.black,
                    alignment=TA_CENTER,
                    leading=12,
                )
                cell_content = Paragraph("<b>FREE</b>", cell_style)
            else:
                song = songs[song_index]
                song_text = format_song_title(song, max_length=40)
                
                cell_style = ParagraphStyle(
                    'SongCell',
                    parent=styles['Normal'],
                    fontSize=8,  # Increased from 7 to 8 (larger cells = more space)
                    textColor=colors.black,
                    alignment=TA_CENTER,
                    leading=9,  # Increased from 7 to 9
                )
                cell_content = Paragraph(song_text, cell_style)
                song_index += 1
            
            row_data.append(cell_content)
        grid_data.append(row_data)
    
    # Create table - LARGER to use more space
    col_width = 32*mm  # Increased from 28mm to 32mm
    row_height = 12*mm  # Increased from 10mm to 12mm
    
    table = Table(grid_data, colWidths=[col_width]*GRID_SIZE, rowHeights=[row_height]*GRID_SIZE)
    
    # Table styling - Black on white for best printing
    table.setStyle(TableStyle([
        # Black grid lines
        ('GRID', (0, 0), (-1, -1), 1.5, colors.black),
        
        # All cells white background
        ('BACKGROUND', (0, 0), (-1, -1), colors.white),
        
        # FREE cell - light gray background to distinguish it
        ('BACKGROUND', (2, 2), (2, 2), colors.lightgrey),
        
        # All cells
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    
    elements.append(table)
    elements.append(Spacer(1, 1*mm))  # Reduced from 2mm
    
    # --- PRIZES SECTION - LARGER and with editable fields ---
    prizes_header_style = ParagraphStyle(
        'PrizesHeader',
        parent=styles['Normal'],
        fontSize=9,  # Reduced from 11 to 9
        textColor=colors.black,
        alignment=TA_CENTER,
        leading=11,  # Reduced
        fontName='Helvetica-Bold',
    )
    
    prizes_detail_style = ParagraphStyle(
        'PrizesDetail',
        parent=styles['Normal'],
        fontSize=7,
        textColor=colors.black,
        alignment=TA_LEFT,
        leading=9,
    )
    
    # Prizes header and single-line format
    prizes_header = Paragraph("<b>🏆 PRIZES TONIGHT 🏆</b>", prizes_header_style)
    elements.append(prizes_header)
    elements.append(Spacer(1, 0.5*mm))
    
    # Single line with all three prizes (use provided values or underscores)
    prizes_data = [
        [
            Paragraph("<b>All 4 Corners:</b>", prizes_detail_style),
            Paragraph(prize_4corners or "__________", prizes_detail_style),
            Paragraph("<b>First Line:</b>", prizes_detail_style),
            Paragraph(prize_first_line or "__________", prizes_detail_style),
            Paragraph("<b>Full House:</b>", prizes_detail_style),
            Paragraph(prize_full_house or "__________", prizes_detail_style)
        ]
    ]
    
    prizes_table = Table(prizes_data, colWidths=[23*mm, 20*mm, 18*mm, 20*mm, 19*mm, 20*mm])
    prizes_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('LEFTPADDING', (0, 0), (-1, -1), 1),
        ('RIGHTPADDING', (0, 0), (-1, -1), 1),
        ('TOPPADDING', (0, 0), (-1, -1), 0.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0.5),
    ]))
    
    elements.append(prizes_table)
    elements.append(Spacer(1, 0.3*mm))  # Optimized
    
    # --- FOOTER SECTION ---
    footer_elements = []
    
    # QR Code and social media (use cached QR buffer if provided)
    if social_media_url and include_qr and qr_buffer:
        try:
            # Create footer table with QR and text side by side
            footer_data = []
            
            # Reuse the cached QR buffer
            qr_img = Image(qr_buffer, width=18*mm, height=18*mm)  # Reduced from 20mm
            
            social_text_style = ParagraphStyle(
                'SocialText',
                parent=styles['Normal'],
                fontSize=8,  # Reduced from 9
                alignment=TA_LEFT,
                leftIndent=3*mm,  # Reduced from 5mm
                leading=9,  # Reduced from 11
            )
            social_text = Paragraph(f"<b>Join Our Social Media To Play &amp; Claim Your Prize!</b><br/>{social_media_url}", social_text_style)
            
            footer_data.append([qr_img, social_text])
            
            footer_table = Table(footer_data, colWidths=[22*mm, 118*mm])  # Adjusted - more compact
            footer_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ALIGN', (0, 0), (0, 0), 'CENTER'),
            ]))
            
            elements.append(footer_table)
        except Exception as e:
            print(f"Error adding QR code: {e}")
    
    # Card number
    card_style = ParagraphStyle(
        'CardNumber',
        parent=styles['Normal'],
        fontSize=7,
        textColor=colors.black,  # Black for B&W printing
        alignment=TA_CENTER,
    )
    card_text = Paragraph(f"<b>Card #{card_num}</b>", card_style)
    elements.append(Spacer(1, 0.2*mm))  # Optimized
    elements.append(card_text)
    
    # Perfect DJ footer
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=5,
        textColor=colors.gray,
        alignment=TA_CENTER,
    )
    footer = Paragraph(f"Powered by Perfect DJ - {WEBSITE_URL}", footer_style)
    elements.append(Spacer(1, 0.1*mm))  # Optimized
    elements.append(footer)
    
    return elements


def generate_batch_pdf(batch_data):
    """Generate a PDF batch with 10 cards - runs in parallel"""
    batch_num, cards_data, venue_name, pub_logo_path, social_media, include_qr, game_number, game_date, qr_buffer_data, prize_4corners, prize_first_line, prize_full_house = batch_data
    
    # Create temp file for this batch
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf', prefix=f'batch_{batch_num}_')
    temp_path = temp_file.name
    temp_file.close()
    
    doc = SimpleDocTemplate(
        temp_path,
        pagesize=A4,
        leftMargin=10*mm,
        rightMargin=10*mm,
        topMargin=8*mm,
        bottomMargin=5*mm,  # Optimized from 8mm
    )
    
    # Reconstruct QR buffer if data provided
    qr_buffer_cache = None
    if qr_buffer_data:
        qr_buffer_cache = BytesIO(qr_buffer_data)
    
    story = []
    for idx, (card_num, card_songs) in enumerate(cards_data):
        # Songs are already assigned uniquely - NO random.sample needed!
        
        # Create card
        card_elements = create_bingo_card(
            card_songs,
            card_num,
            venue_name,
            pub_logo_path,
            social_media,
            include_qr,
            game_number,
            game_date,
            qr_buffer_cache,
            prize_4corners,
            prize_first_line,
            prize_full_house
        )
        
        story.extend(card_elements)
        
        # Add page break after every 2 cards (except for the last card in batch)
        if (idx + 1) % 2 == 0 and idx < len(cards_data) - 1:
            story.append(PageBreak())
        # Add spacer between cards on same page
        elif idx < len(cards_data) - 1:
            story.append(Spacer(1, 5*mm))
    
    doc.build(story)
    return temp_path


def generate_cards(venue_name: str = "Music Bingo", num_players: int = 25,
                  pub_logo: str = None, social_media: str = None, include_qr: bool = False,
                  game_number: int = 1, game_date: str = None,
                  prize_4corners: str = '', prize_first_line: str = '', prize_full_house: str = '',
                  voice_id: str = 'JBFqnCBsd6RMkjVDRZzb', decades: List[str] = None,
                  session_id: str = None):
    """Generate all bingo cards"""
    import time
    start_time = time.time()
    
    # 🔍 DEBUG: Log function parameters
    print(f"\n🔍 [DEBUG] generate_cards() called with:")
    print(f"   venue_name: {venue_name} (type: {type(venue_name)})")
    print(f"   num_players: {num_players} (type: {type(num_players)})")
    print(f"   voice_id: {voice_id}")
    print(f"   decades: {decades}")
    print(f"   pub_logo: {pub_logo if pub_logo else 'None'}")
    print(f"   Expected num_cards: {num_players * 2}")
    
    # Generate unique PDF filename per session
    if session_id:
        OUTPUT_FILE = OUTPUT_DIR / f"music_bingo_cards_{session_id}.pdf"
    else:
        OUTPUT_FILE = OUTPUT_DIR / "music_bingo_cards.pdf"
    
    print(f"📄 PDF will be saved to: {OUTPUT_FILE.name}")
    
    # Memory monitoring
    process = psutil.Process()
    mem_start = process.memory_info()
    
    print(f"\n{'='*60}")
    print(f"🎵 MUSIC BINGO CARD GENERATOR (ReportLab)")
    print(f"{'='*60}")
    print(f"Venue: {venue_name}")
    print(f"Players: {num_players}")
    print(f"Voice ID: {voice_id}")
    print(f"Decades: {decades if decades else 'All'}")
    print(f"Pub Logo: {pub_logo if pub_logo else 'None'}")
    print(f"Social Media: {social_media if social_media else 'None'}")
    print(f"Include QR: {include_qr}")
    print(f"📊 Memory at start: {mem_start.rss / 1024 / 1024:.1f} MB")
    print(f"{'='*60}\n")
    
    # Load songs - check if current_session.json exists with pre-selected songs
    step_start = time.time()
    session_file = OUTPUT_DIR / "current_session.json"
    selected_songs = None
    
    if session_file.exists():
        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                session_data = json.load(f)
                if 'songs' in session_data and len(session_data['songs']) > 0:
                    selected_songs = session_data['songs']
                    print(f"✓ Loaded {len(selected_songs)} pre-selected songs from current_session.json ({time.time()-step_start:.2f}s)")
                    print(f"   🎯 Using EXACT songs from session to match database")
        except Exception as e:
            print(f"⚠️  Error loading session file: {e}")
            print(f"   Falling back to random song selection")
    
    # If no session file or no songs in it, select randomly
    if selected_songs is None:
        all_songs = load_pool()
        mem_after_load = process.memory_info()
        print(f"✓ Loaded {len(all_songs)} songs from pool ({time.time()-step_start:.2f}s) - Memory: {mem_after_load.rss / 1024 / 1024:.1f} MB")
        
        # Filter by decades if specified
        if decades:
            filtered_songs = []
            for song in all_songs:
                song_year = song.get('year')
                if song_year:
                    # Determine decade from year
                    song_decade = f"{(song_year // 10) * 10}s"
                    if song_decade in decades:
                        filtered_songs.append(song)
            
            print(f"✓ Filtered to {len(filtered_songs)} songs from decades {decades}")
            all_songs = filtered_songs
            
            if len(all_songs) == 0:
                print("⚠️  WARNING: No songs found for selected decades, using all songs")
                all_songs = load_pool()
        
        # Calculate optimal songs
        step_start = time.time()
        optimal_songs = calculate_optimal_songs(num_players)
        print(f"✓ Using {optimal_songs} songs for {num_players} players ({time.time()-step_start:.3f}s)")
        
        # Shuffle and select songs with randomization based on timestamp
        # This ensures different song selection for each session
        step_start = time.time()
        import hashlib
        import uuid
        
        # Create a UNIQUE seed using UUID + timestamp + venue + game number + random component
        # This ensures maximum randomness even for rapid successive generations
        unique_id = str(uuid.uuid4())
        random_component = random.random()
        seed_str = f"{time.time()}-{unique_id}-{venue_name}-{game_number}-{num_players}-{random_component}"
        seed_hash = int(hashlib.md5(seed_str.encode()).hexdigest()[:8], 16)
        random.seed(seed_hash)
        
        # Shuffle the entire pool MULTIPLE times for better randomization
        shuffled_pool = all_songs.copy()
        for _ in range(3):  # Shuffle 3 times
            random.shuffle(shuffled_pool)
        
        # Then select from shuffled pool
        selected_songs = shuffled_pool[:min(optimal_songs, len(shuffled_pool))]
        
        print(f"✓ Selected {len(selected_songs)} songs with seed {seed_hash} ({time.time()-step_start:.3f}s)")
        print(f"   Unique ID: {unique_id[:8]}...")
        print(f"   First 5 songs: {[s['title'] for s in selected_songs[:5]]}")
    
    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Load pub logo once (if provided) and save as temp file
    pub_logo_path = None
    if pub_logo:
        step_start = time.time()
        logo_buffer = download_logo(pub_logo)
        if logo_buffer:
            try:
                from PIL import Image as PILImage
                import tempfile
                
                # Convert to RGB
                pil_img = PILImage.open(logo_buffer)
                if pil_img.mode in ('RGBA', 'LA', 'P'):
                    background = PILImage.new('RGB', pil_img.size, (255, 255, 255))
                    if pil_img.mode == 'P':
                        pil_img = pil_img.convert('RGBA')
                    if 'A' in pil_img.mode:
                        background.paste(pil_img, mask=pil_img.split()[-1])
                    else:
                        background.paste(pil_img)
                    pil_img = background
                elif pil_img.mode != 'RGB':
                    pil_img = pil_img.convert('RGB')
                
                # Save as temporary JPEG
                temp_logo = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
                pil_img.save(temp_logo.name, format='JPEG', quality=95)
                pub_logo_path = temp_logo.name
                temp_logo.close()
                
                mem_after_logo = process.memory_info()
                print(f"✓ Loaded pub logo ({time.time()-step_start:.2f}s) - Memory: {mem_after_logo.rss / 1024 / 1024:.1f} MB")
            except Exception as e:
                print(f"Error processing logo: {e}")
    
    # Generate QR code once (if needed) to avoid regenerating 50 times
    qr_buffer_cache = None
    qr_buffer_data = None
    if include_qr and social_media:
        step_start = time.time()
        qr_buffer_cache = generate_qr_code(social_media)
        if qr_buffer_cache:
            qr_buffer_data = qr_buffer_cache.getvalue()  # Get bytes for serialization
            mem_after_qr = process.memory_info()
            print(f"✓ Generated QR code ({time.time()-step_start:.2f}s) - Memory: {mem_after_qr.rss / 1024 / 1024:.1f} MB")
    
    # *** DISTRIBUTE SONGS UNIQUELY ACROSS ALL CARDS ***
    # Calculate number of cards based on num_players (2 cards per player)
    num_cards = num_players * 2
    step_start = time.time()
    print(f"\n🎵 Distributing songs uniquely across {num_cards} cards...")
    all_card_songs = distribute_songs_unique(selected_songs, num_cards, SONGS_PER_CARD)
    print(f"✓ Songs distributed uniquely ({time.time()-step_start:.2f}s)")
    print(f"   Each card has {SONGS_PER_CARD} unique songs")
    print(f"   Total unique songs used: {len(set(song['id'] for card in all_card_songs for song in card))}")
    
    # *** CRITICAL VALIDATION: Check for duplicate songs within each card ***
    print(f"\n🔍 Validating cards for duplicates...")
    duplicates_found = False
    for card_idx, card in enumerate(all_card_songs):
        song_ids = [s.get('id', s.get('title')) for s in card]
        unique_ids = set(song_ids)
        if len(song_ids) != len(unique_ids):
            duplicates_found = True
            duplicates = [sid for sid in song_ids if song_ids.count(sid) > 1]
            print(f"❌ ERROR: Card {card_idx + 1} has DUPLICATE songs:")
            for dup in set(duplicates):
                count = song_ids.count(dup)
                print(f"   - '{dup}' appears {count} times")
    
    if duplicates_found:
        raise ValueError("CRITICAL ERROR: Duplicate songs found within cards! Cannot generate PDF.")
    
    print(f"✅ Validation passed: All {num_cards} cards have unique songs (no duplicates within any card)")
    
    # Check if parallel processing is beneficial
    # MEMORY-OPTIMIZED: Limit workers to avoid OOM on App Platform
    num_cpus = mp.cpu_count()
    use_parallel = True  # Always use parallel - it's faster
    
    if use_parallel:
        # **PARALLEL GENERATION** - MEMORY-OPTIMIZED for cloud deployment
        print(f"\n📄 Generating PDF cards in parallel (MEMORY-OPTIMIZED)...")
        print(f"PROGRESS: 0")  # Structured progress for backend parsing
        parallel_start = time.time()
        
        batch_size = 10  # 10 cards per batch
        # MEMORY OPTIMIZATION: Limit to 2 workers to avoid OOM (exit code 128)
        # App Platform has memory limits - using all cores causes out-of-memory crashes
        num_workers = min(2, num_cpus)  # Maximum 2 workers to stay within memory limits
        print(f"   Using {num_workers} parallel workers (CPUs: {num_cpus}) - MEMORY-SAFE MODE")
        
        # Prepare batch data with pre-assigned songs
        batches = []
        for i in range(0, num_cards, batch_size):
            batch_cards = []
            for card_idx in range(i, min(i + batch_size, num_cards)):
                card_num = card_idx + 1
                card_songs = all_card_songs[card_idx]
                batch_cards.append((card_num, card_songs))
            
            batches.append((
                i // batch_size,
                batch_cards,  # Now includes (card_num, songs) tuples
                venue_name,
                pub_logo_path,
                social_media,
                include_qr,
                game_number,
                game_date,
                qr_buffer_data,
                prize_4corners,
                prize_first_line,
                prize_full_house
            ))
        
        # Generate PDFs in parallel with progress tracking
        with ProcessPoolExecutor(max_workers=num_workers) as executor:
            temp_pdfs = []
            futures = [executor.submit(generate_batch_pdf, batch) for batch in batches]
            
            for i, future in enumerate(futures):
                try:
                    result = future.result(timeout=60)
                    temp_pdfs.append(result)
                    progress = (i + 1) / len(futures) * 90  # Reserve 10% for merging
                    mem_info = process.memory_info()
                    print(f"PROGRESS: {progress:.0f}")  # Structured progress
                    print(f"  📊 Progress: {progress:.0f}% ({i+1}/{len(futures)} batches) - Memory: {mem_info.rss / 1024 / 1024:.1f} MB")
                except Exception as e:
                    print(f"  ❌ Batch {i} failed: {e}")
                    raise
        
        print(f"  ✓ All batches generated ({time.time()-parallel_start:.2f}s)")
        mem_info = process.memory_info()
        print(f"  📈 Final memory: {mem_info.rss / 1024 / 1024:.1f} MB")
        
        # Merge all PDFs
        print(f"\n📝 Merging PDF batches...")
        print(f"PROGRESS: 90")  # Structured progress for merging stage
        merge_start = time.time()
        
        merger = PdfWriter()
        for pdf_path in temp_pdfs:
            reader = PdfReader(pdf_path)
            for page in reader.pages:
                merger.add_page(page)
        
        with open(str(OUTPUT_FILE), 'wb') as output_file:
            merger.write(output_file)
        
        print(f"PROGRESS: 100")  # Completed
        print(f"   ✓ PDF merged ({time.time()-merge_start:.2f}s)")
        
        # Cleanup temp files
        for pdf_path in temp_pdfs:
            try:
                os.unlink(pdf_path)
            except:
                pass
    else:
        # **SEQUENTIAL GENERATION** - Single core optimization
        print(f"\n📄 Generating PDF cards (single-core mode)...")
        print(f"   CPUs: {num_cpus} - Using sequential generation")
        
        doc = SimpleDocTemplate(
            str(OUTPUT_FILE),
            pagesize=A4,
            leftMargin=10*mm,  # Same as batch mode
            rightMargin=10*mm,
            topMargin=8*mm,
            bottomMargin=8*mm,
        )
        
        story = []
        cards_start = time.time()
        
        for i in range(num_cards):
            # Use pre-assigned unique songs instead of random.sample
            card_songs = all_card_songs[i]
            
            card_elements = create_bingo_card(
                card_songs,
                i + 1,
                venue_name,
                pub_logo_path,
                social_media,
                include_qr,
                game_number,
                game_date,
                qr_buffer_cache
            )
            
            story.extend(card_elements)
            
            if (i + 1) % 2 == 0 and i < num_cards - 1:
                story.append(PageBreak())
            elif i < num_cards - 1:
                story.append(Spacer(1, 5*mm))
            
            if (i + 1) % 10 == 0:
                print(f"  ✓ Generated {i + 1}/{num_cards} cards ({time.time()-cards_start:.2f}s)")
        
        print(f"\n📝 Building PDF document...")
        build_start = time.time()
        doc.build(story)
        print(f"   ✓ PDF built ({time.time()-build_start:.2f}s)")
    
    # Cleanup temp logo file
    if pub_logo_path:
        try:
            import os
            os.unlink(pub_logo_path)
        except:
            pass
    
    total_time = time.time() - start_time
    
    # *** CRITICAL: Save session file with exact songs used ***
    # This ensures the game plays THE SAME songs that are printed on cards
    session_file = OUTPUT_DIR / "current_session.json"
    session_data = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "venue_name": venue_name,
        "num_players": num_players,
        "num_cards": num_cards,
        "songs_per_card": SONGS_PER_CARD,
        "game_number": game_number,
        "game_date": game_date,
        "prize_4corners": prize_4corners,
        "prize_first_line": prize_first_line,
        "prize_full_house": prize_full_house,
        "voice_id": voice_id,  # For TTS announcements
        "decades": decades if decades else [],  # For filtering songs
        "pdf_file": str(OUTPUT_FILE),  # Local PDF path
        "songs": selected_songs  # The EXACT songs used in the cards
    }
    
    with open(session_file, 'w', encoding='utf-8') as f:
        json.dump(session_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Session file saved: {session_file}")
    print(f"   ⚠️  IMPORTANT: Use this session file when starting the game!")
    print(f"   This ensures songs played match the printed cards.")
    
    print(f"\n{'='*60}")
    print(f"✅ SUCCESS!")
    print(f"{'='*60}")
    print(f"Generated: {OUTPUT_FILE}")
    print(f"Cards: {num_cards}")
    print(f"Pages: {(num_cards + 1) // 2} (2 cards per page)")
    print(f"Songs per card: {SONGS_PER_CARD}")
    print(f"Total songs available: {len(selected_songs)}")
    print(f"Session file: {session_file}")
    print(f"⏱️  TOTAL TIME: {total_time:.2f}s")
    print(f"{'='*60}\n")
    
    return {
        'num_cards': num_cards,
        'num_pages': (num_cards + 1) // 2,  # 2 cards per page
        'songs_per_card': SONGS_PER_CARD,
        'total_songs': len(selected_songs),
        'session_file': str(session_file)
    }


if __name__ == '__main__':
    import psutil
    
    # Log system resources at start
    process = psutil.Process()
    mem_info = process.memory_info()
    print(f"\n🔧 SYSTEM INFO:")
    print(f"   PID: {process.pid}")
    print(f"   Memory RSS: {mem_info.rss / 1024 / 1024:.1f} MB")
    print(f"   CPU Count: {mp.cpu_count()}")
    try:
        vm = psutil.virtual_memory()
        print(f"   Available Memory: {vm.available / 1024 / 1024:.1f} MB")
        print(f"   Total Memory: {vm.total / 1024 / 1024:.1f} MB")
    except:
        pass
    
    parser = argparse.ArgumentParser(description='Generate Music Bingo cards with branding')
    parser.add_argument('--venue_name', default='Music Bingo', help='Name of the venue')
    parser.add_argument('--num_players', type=int, default=25, help='Number of players')
    parser.add_argument('--pub_logo', default=None, help='URL or path to pub logo image')
    parser.add_argument('--social_media', default=None, help='Social media URL to encode in QR code')
    parser.add_argument('--include_qr', type=lambda x: x.lower() == 'true', default=False, 
                       help='Whether to include QR code (true/false)')
    parser.add_argument('--game_number', type=int, default=1, help='Game number (for multiple games)')
    parser.add_argument('--game_date', default=None, help='Game date (default: today)')
    parser.add_argument('--prize_4corners', default='', help='Prize for All 4 Corners')
    parser.add_argument('--prize_first_line', default='', help='Prize for First Line')
    parser.add_argument('--prize_full_house', default='', help='Prize for Full House')
    parser.add_argument('--voice_id', default='JBFqnCBsd6RMkjVDRZzb', help='Voice ID for TTS')
    parser.add_argument('--decades', default=None, help='Comma-separated list of decades to filter (e.g., 1980s,1990s,2000s)')
    parser.add_argument('--session_id', default=None, help='Unique session ID for PDF filename')
    
    args = parser.parse_args()
    
    # Parse decades if provided
    decades_list = None
    if args.decades:
        decades_list = [d.strip() for d in args.decades.split(',')]
        print(f"📅 Filtering songs by decades: {decades_list}")
    
    generate_cards(
        venue_name=args.venue_name,
        num_players=args.num_players,
        pub_logo=args.pub_logo,
        social_media=args.social_media,
        include_qr=args.include_qr,
        game_number=args.game_number,
        game_date=args.game_date,
        prize_4corners=args.prize_4corners,
        prize_first_line=args.prize_first_line,
        prize_full_house=args.prize_full_house,
        voice_id=args.voice_id,
        decades=decades_list,
        session_id=args.session_id
    )
        game_number=args.game_number,
        game_date=args.game_date,
        prize_4corners=args.prize_4corners,
        prize_first_line=args.prize_first_line,
        prize_full_house=args.prize_full_house,
        voice_id=args.voice_id,
        decades=decades_list
    )
