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

# ReportLab imports
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.pdfgen import canvas

# QR Code generation
import qrcode

# Configuration
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
INPUT_POOL = PROJECT_ROOT / "data" / "pool.json"
OUTPUT_DIR = PROJECT_ROOT / "data" / "cards"
OUTPUT_FILE = OUTPUT_DIR / "music_bingo_cards.pdf"
NUM_CARDS = 50
GRID_SIZE = 5  # 5x5 bingo
SONGS_PER_CARD = 24  # 25 cells - 1 FREE

# Perfect DJ Branding
PERFECT_DJ_LOGO = PROJECT_ROOT / "frontend" / "assets" / "perfect-dj-logo.png"
WEBSITE_URL = "www.perfectdj.co.uk"


def calculate_optimal_songs(num_players: int) -> int:
    """Calculate optimal number of songs based on players"""
    base_songs = int(num_players * 3)
    base_songs = max(base_songs, 30)
    base_songs = min(base_songs, 150)
    return base_songs


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
    """Download logo from URL or load from local file"""
    if not url:
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
                     include_qr: bool = False) -> List:
    """Create a single bingo card with ReportLab elements"""
    elements = []
    
    # Styles
    styles = getSampleStyleSheet()
    
    # Header style
    header_style = ParagraphStyle(
        'CustomHeader',
        parent=styles['Heading1'],
        fontSize=20,
        textColor=colors.HexColor('#667eea'),
        alignment=TA_CENTER,
        spaceAfter=5*mm,
    )
    
    # Venue style
    venue_style = ParagraphStyle(
        'Venue',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.HexColor('#4a5568'),
        alignment=TA_CENTER,
        spaceAfter=8*mm,
    )
    
    # --- HEADER SECTION ---
    # Title
    title = Paragraph(f"MUSIC BINGO at {venue_name}", header_style)
    elements.append(title)
    
    subtitle = Paragraph("Mark the song when you hear it play!", venue_style)
    elements.append(subtitle)
    
    # --- PUB LOGO (if provided) ---
    if pub_logo_path:
        try:
            from PIL import Image as PILImage
            
            # Get original dimensions
            pil_img = PILImage.open(pub_logo_path)
            orig_width, orig_height = pil_img.size
            aspect = orig_width / orig_height
            
            # Calculate dimensions with aspect ratio
            max_width = 80
            max_height = 40
            
            if aspect > (max_width / max_height):
                new_width = max_width * mm
                new_height = (max_width / aspect) * mm
            else:
                new_height = max_height * mm
                new_width = (max_height * aspect) * mm
            
            pub_logo = Image(pub_logo_path, width=new_width, height=new_height)
            pub_logo.hAlign = 'CENTER'
            elements.append(pub_logo)
            elements.append(Spacer(1, 5*mm))
        except Exception as e:
            pass  # Skip if error
    
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
                    fontSize=16,
                    textColor=colors.black,
                    alignment=TA_CENTER,
                    leading=14,
                )
                cell_content = Paragraph("<b>FREE</b><br/><font size='8'>www.perfectdj.co.uk</font>", cell_style)
            else:
                song = songs[song_index]
                song_text = format_song_title(song, max_length=40)
                
                cell_style = ParagraphStyle(
                    'SongCell',
                    parent=styles['Normal'],
                    fontSize=8,
                    textColor=colors.black,
                    alignment=TA_CENTER,
                    leading=10,
                )
                cell_content = Paragraph(song_text, cell_style)
                song_index += 1
            
            row_data.append(cell_content)
        grid_data.append(row_data)
    
    # Create table
    col_width = 35*mm
    row_height = 20*mm
    
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
    elements.append(Spacer(1, 5*mm))
    
    # --- FOOTER SECTION ---
    footer_elements = []
    
    # QR Code and social media
    if social_media_url and include_qr:
        qr_buffer = generate_qr_code(social_media_url)
        if qr_buffer:
            try:
                # Create footer table with QR and text side by side
                footer_data = []
                
                qr_img = Image(qr_buffer, width=20*mm, height=20*mm)
                
                social_text_style = ParagraphStyle(
                    'SocialText',
                    parent=styles['Normal'],
                    fontSize=10,
                    alignment=TA_LEFT,
                    leftIndent=5*mm,
                )
                social_text = Paragraph(f"<b>Follow us!</b><br/>{social_media_url}", social_text_style)
                
                footer_data.append([qr_img, social_text])
                
                footer_table = Table(footer_data, colWidths=[25*mm, 150*mm])
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
        fontSize=10,
        textColor=colors.HexColor('#667eea'),
        alignment=TA_CENTER,
    )
    card_text = Paragraph(f"<b>Card #{card_num}</b>", card_style)
    elements.append(Spacer(1, 3*mm))
    elements.append(card_text)
    
    # Perfect DJ footer
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.gray,
        alignment=TA_CENTER,
    )
    footer = Paragraph(f"Powered by Perfect DJ - {WEBSITE_URL}", footer_style)
    elements.append(Spacer(1, 2*mm))
    elements.append(footer)
    
    return elements


def generate_cards(venue_name: str = "Music Bingo", num_players: int = 25,
                  pub_logo: str = None, social_media: str = None, include_qr: bool = False):
    """Generate all bingo cards"""
    
    print(f"\n{'='*60}")
    print(f"🎵 MUSIC BINGO CARD GENERATOR (ReportLab)")
    print(f"{'='*60}")
    print(f"Venue: {venue_name}")
    print(f"Players: {num_players}")
    print(f"Pub Logo: {pub_logo if pub_logo else 'None'}")
    print(f"Social Media: {social_media if social_media else 'None'}")
    print(f"Include QR: {include_qr}")
    print(f"{'='*60}\n")
    
    # Load songs
    all_songs = load_pool()
    print(f"✓ Loaded {len(all_songs)} songs from pool")
    
    # Calculate optimal songs
    optimal_songs = calculate_optimal_songs(num_players)
    print(f"✓ Using {optimal_songs} songs for {num_players} players")
    
    # Shuffle and select songs
    selected_songs = random.sample(all_songs, min(optimal_songs, len(all_songs)))
    print(f"✓ Selected {len(selected_songs)} songs")
    
    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Load pub logo once (if provided) and save as temp file
    pub_logo_path = None
    if pub_logo:
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
                
                print(f"✓ Loaded pub logo")
            except Exception as e:
                print(f"Error processing logo: {e}")
    
    # Create PDF
    print(f"\n📄 Generating PDF cards...")
    
    doc = SimpleDocTemplate(
        str(OUTPUT_FILE),
        pagesize=A4,
        leftMargin=15*mm,
        rightMargin=15*mm,
        topMargin=15*mm,
        bottomMargin=15*mm,
    )
    
    story = []
    
    # Generate cards
    for i in range(NUM_CARDS):
        # Shuffle songs for this card
        card_songs = random.sample(selected_songs, SONGS_PER_CARD)
        
        # Create card
        card_elements = create_bingo_card(
            card_songs,
            i + 1,
            venue_name,
            pub_logo_path,
            social_media,
            include_qr
        )
        
        story.extend(card_elements)
        
        # Add page break except for last card
        if i < NUM_CARDS - 1:
            from reportlab.platypus import PageBreak
            story.append(PageBreak())
        
        if (i + 1) % 10 == 0:
            print(f"  ✓ Generated {i + 1}/{NUM_CARDS} cards")
    
    # Build PDF
    print(f"\n📝 Building PDF document...")
    print(f"   Total flowables in story: {len(story)}")
    print(f"   Starting PDF build (this may take a moment)...")
    
    doc.build(story)
    
    # Cleanup temp logo file
    if pub_logo_path:
        try:
            import os
            os.unlink(pub_logo_path)
        except:
            pass
    
    print(f"\n{'='*60}")
    print(f"✅ SUCCESS!")
    print(f"{'='*60}")
    print(f"Generated: {OUTPUT_FILE}")
    print(f"Cards: {NUM_CARDS}")
    print(f"Pages: {NUM_CARDS}")
    print(f"Songs per card: {SONGS_PER_CARD}")
    print(f"Total songs available: {len(selected_songs)}")
    print(f"{'='*60}\n")
    
    return {
        'num_cards': NUM_CARDS,
        'num_pages': NUM_CARDS,
        'songs_per_card': SONGS_PER_CARD,
        'total_songs': len(selected_songs)
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate Music Bingo cards with branding')
    parser.add_argument('--venue_name', default='Music Bingo', help='Name of the venue')
    parser.add_argument('--num_players', type=int, default=25, help='Number of players')
    parser.add_argument('--pub_logo', default=None, help='URL or path to pub logo image')
    parser.add_argument('--social_media', default=None, help='Social media URL to encode in QR code')
    parser.add_argument('--include_qr', type=lambda x: x.lower() == 'true', default=False, 
                       help='Whether to include QR code (true/false)')
    
    args = parser.parse_args()
    
    generate_cards(
        venue_name=args.venue_name,
        num_players=args.num_players,
        pub_logo=args.pub_logo,
        social_media=args.social_media,
        include_qr=args.include_qr
    )
