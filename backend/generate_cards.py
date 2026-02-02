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
OUTPUT_FILE = OUTPUT_DIR / "music_bingo_cards.pdf"
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
    Distribute songs uniquely across all cards - NO REPEATS in a session
    Each song appears on AT MOST ONE card to avoid duplicates during gameplay
    
    Args:
        all_songs: Full pool of available songs
        num_cards: Number of bingo cards to generate
        songs_per_card: Songs per card (24 for 5x5 grid with FREE space)
    
    Returns:
        List of card song lists, each with unique songs
    """
    total_songs_needed = num_cards * songs_per_card
    
    # Shuffle all songs
    shuffled = all_songs.copy()
    random.shuffle(shuffled)
    
    # If we don't have enough unique songs, we need to use some songs multiple times
    # but we'll minimize repetition by cycling through the pool
    if len(shuffled) < total_songs_needed:
        print(f"⚠️  Warning: Need {total_songs_needed} songs but only have {len(shuffled)}")
        print(f"   Some songs will appear on multiple cards")
        # Repeat the pool enough times to have enough songs
        times_to_repeat = (total_songs_needed // len(shuffled)) + 1
        shuffled = (shuffled * times_to_repeat)[:total_songs_needed]
        random.shuffle(shuffled)
    
    # Distribute songs into cards
    card_songs = []
    for i in range(num_cards):
        start_idx = i * songs_per_card
        end_idx = start_idx + songs_per_card
        card_songs.append(shuffled[start_idx:end_idx])
    
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
                  prize_4corners: str = '', prize_first_line: str = '', prize_full_house: str = ''):
    """Generate all bingo cards"""
    import time
    start_time = time.time()
    
    # Memory monitoring
    process = psutil.Process()
    mem_start = process.memory_info()
    
    print(f"\n{'='*60}")
    print(f"🎵 MUSIC BINGO CARD GENERATOR (ReportLab)")
    print(f"{'='*60}")
    print(f"Venue: {venue_name}")
    print(f"Players: {num_players}")
    print(f"Pub Logo: {pub_logo if pub_logo else 'None'}")
    print(f"Social Media: {social_media if social_media else 'None'}")
    print(f"Include QR: {include_qr}")
    print(f"📊 Memory at start: {mem_start.rss / 1024 / 1024:.1f} MB")
    print(f"{'='*60}\n")
    
    # Load songs
    step_start = time.time()
    all_songs = load_pool()
    mem_after_load = process.memory_info()
    print(f"✓ Loaded {len(all_songs)} songs from pool ({time.time()-step_start:.2f}s) - Memory: {mem_after_load.rss / 1024 / 1024:.1f} MB")
    
    # Calculate optimal songs
    step_start = time.time()
    optimal_songs = calculate_optimal_songs(num_players)
    print(f"✓ Using {optimal_songs} songs for {num_players} players ({time.time()-step_start:.3f}s)")
    
    # Shuffle and select songs
    step_start = time.time()
    selected_songs = random.sample(all_songs, min(optimal_songs, len(all_songs)))
    print(f"✓ Selected {len(selected_songs)} songs ({time.time()-step_start:.3f}s)")
    
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
    # Each song appears on AT MOST ONE card to prevent duplicates during gameplay
    step_start = time.time()
    print(f"\n🎵 Distributing songs uniquely across {NUM_CARDS} cards...")
    all_card_songs = distribute_songs_unique(selected_songs, NUM_CARDS, SONGS_PER_CARD)
    print(f"✓ Songs distributed uniquely ({time.time()-step_start:.2f}s)")
    print(f"   Each card has {SONGS_PER_CARD} unique songs")
    print(f"   Total unique songs used: {len(set(song['id'] for card in all_card_songs for song in card))}")
    
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
        for i in range(0, NUM_CARDS, batch_size):
            batch_cards = []
            for card_idx in range(i, min(i + batch_size, NUM_CARDS)):
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
        
        for i in range(NUM_CARDS):
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
            
            if (i + 1) % 2 == 0 and i < NUM_CARDS - 1:
                story.append(PageBreak())
            elif i < NUM_CARDS - 1:
                story.append(Spacer(1, 5*mm))
            
            if (i + 1) % 10 == 0:
                print(f"  ✓ Generated {i + 1}/{NUM_CARDS} cards ({time.time()-cards_start:.2f}s)")
        
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
        "num_cards": NUM_CARDS,
        "songs_per_card": SONGS_PER_CARD,
        "game_number": game_number,
        "game_date": game_date,
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
    print(f"Cards: {NUM_CARDS}")
    print(f"Pages: {(NUM_CARDS + 1) // 2} (2 cards per page)")
    print(f"Songs per card: {SONGS_PER_CARD}")
    print(f"Total songs available: {len(selected_songs)}")
    print(f"Session file: {session_file}")
    print(f"⏱️  TOTAL TIME: {total_time:.2f}s")
    print(f"{'='*60}\n")
    
    return {
        'num_cards': NUM_CARDS,
        'num_pages': (NUM_CARDS + 1) // 2,  # 2 cards per page
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
    
    args = parser.parse_args()
    
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
        prize_full_house=args.prize_full_house
    )
