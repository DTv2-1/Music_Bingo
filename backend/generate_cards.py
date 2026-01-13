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
# In Docker, everything is in /app/, so no need to go to parent
PROJECT_ROOT = SCRIPT_DIR
INPUT_POOL = PROJECT_ROOT / "data" / "pool.json"
OUTPUT_DIR = PROJECT_ROOT / "data" / "cards"
OUTPUT_FILE = OUTPUT_DIR / "music_bingo_cards.pdf"
NUM_CARDS = 50  # Back to 50 with Professional XS resources
GRID_SIZE = 5  # 5x5 bingo
SONGS_PER_CARD = 24  # 25 cells - 1 FREE

# Perfect DJ Branding - Check multiple possible locations
PERFECT_DJ_LOGO_PATHS = [
    PROJECT_ROOT / "frontend" / "assets" / "perfect-dj-logo.png",  # Local dev
    PROJECT_ROOT / "assets" / "perfect-dj-logo.png",  # Docker if copied
    Path("/app/frontend/assets/perfect-dj-logo.png"),  # Docker absolute
]
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
                     include_qr: bool = False, game_number: int = 1, game_date: str = None,
                     qr_buffer: BytesIO = None) -> List:
    """Create a single bingo card with ReportLab elements"""
    elements = []
    
    # Styles
    styles = getSampleStyleSheet()
    
    # Header style - LARGER title as requested
    header_style = ParagraphStyle(
        'CustomHeader',
        parent=styles['Heading1'],
        fontSize=18,  # Reduced from 24 to 18 to save space
        textColor=colors.HexColor('#667eea'),
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
    
    # --- HEADER SECTION WITH LOGO ON TOP LEFT ---
    if pub_logo_path:
        try:
            from PIL import Image as PILImage
            
            # Get original dimensions
            pil_img = PILImage.open(pub_logo_path)
            orig_width, orig_height = pil_img.size
            aspect = orig_width / orig_height
            
            # LARGER logo as requested (on top left)
            max_width = 40  # Reduced from 50 to 40
            max_height = 20  # Reduced from 25 to 20
            
            if aspect > (max_width / max_height):
                new_width = max_width * mm
                new_height = (max_width / aspect) * mm
            else:
                new_height = max_height * mm
                new_width = (max_height * aspect) * mm
            
            pub_logo = Image(pub_logo_path, width=new_width, height=new_height)
            
            # Perfect DJ logo on right
            perfect_dj_logo = None
            try:
                # Try multiple paths for Docker compatibility
                for logo_path in PERFECT_DJ_LOGO_PATHS:
                    if logo_path.exists():
                        perfect_dj_logo = Image(str(logo_path), width=20*mm, height=20*mm)
                        break
            except Exception as e:
                print(f"Warning: Could not load Perfect DJ logo: {e}")
                pass
            
            # Create header table with logos on left and right
            if perfect_dj_logo:
                # Ajustado para mover el título más a la izquierda
                header_table = Table([[pub_logo, Paragraph(f"<b>MUSIC BINGO</b><br/><font size='8'>{venue_name}</font>", header_style), perfect_dj_logo]], 
                                    colWidths=[30*mm, 90*mm, 30*mm])  # 30mm izq + 30mm der = balanceado
                header_table.setStyle(TableStyle([
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('ALIGN', (0, 0), (0, 0), 'LEFT'),
                    ('ALIGN', (1, 0), (1, 0), 'CENTER'),
                    ('ALIGN', (2, 0), (2, 0), 'RIGHT'),
                ]))
            else:
                header_table = Table([[pub_logo, Paragraph(f"<b>MUSIC BINGO</b><br/><font size='8'>{venue_name}</font>", header_style)]], 
                                    colWidths=[45*mm, 115*mm])  # Adjusted
                header_table.setStyle(TableStyle([
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('ALIGN', (0, 0), (0, 0), 'LEFT'),
                    ('ALIGN', (1, 0), (1, 0), 'CENTER'),
                ]))
            
            elements.append(header_table)
            elements.append(Spacer(1, 1*mm))  # Reduced from 2mm to 1mm
        except Exception as e:
            print(f"Error adding pub logo: {e}")
            # Fallback to text-only title
            title = Paragraph(f"<b>MUSIC BINGO</b><br/><font size='10'>{venue_name}</font>", header_style)
            elements.append(title)
    else:
        # No pub logo - just title
        title = Paragraph(f"<b>MUSIC BINGO</b><br/><font size='10'>{venue_name}</font>", header_style)
        elements.append(title)
    
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
                cell_content = Paragraph("<b>FREE</b><br/><font size='7'>www.perfectdj.co.uk</font>", cell_style)
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
    
    # Single line with all three prizes
    prizes_data = [
        [
            Paragraph("<b>All 4 Corners:</b>", prizes_detail_style),
            Paragraph("__________", prizes_detail_style),
            Paragraph("<b>First Line:</b>", prizes_detail_style),
            Paragraph("__________", prizes_detail_style),
            Paragraph("<b>Full House:</b>", prizes_detail_style),
            Paragraph("__________", prizes_detail_style)
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
    elements.append(Spacer(1, 0.5*mm))
    
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
        textColor=colors.HexColor('#667eea'),
        alignment=TA_CENTER,
    )
    card_text = Paragraph(f"<b>Card #{card_num}</b>", card_style)
    elements.append(Spacer(1, 0.3*mm))  # Reduced from 0.5mm
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
    elements.append(Spacer(1, 0.3*mm))  # Reduced from 0.5mm
    elements.append(footer)
    
    return elements


def generate_batch_pdf(batch_data):
    """Generate a PDF batch with 10 cards - runs in parallel"""
    batch_num, cards_range, selected_songs, venue_name, pub_logo_path, social_media, include_qr, game_number, game_date, qr_buffer_data = batch_data
    
    # Create temp file for this batch
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf', prefix=f'batch_{batch_num}_')
    temp_path = temp_file.name
    temp_file.close()
    
    doc = SimpleDocTemplate(
        temp_path,
        pagesize=A4,
        leftMargin=10*mm,  # Reduced from 15mm
        rightMargin=10*mm,  # Reduced from 15mm
        topMargin=8*mm,  # Reduced from 10mm
        bottomMargin=8*mm,  # Reduced from 10mm
    )
    
    # Reconstruct QR buffer if data provided
    qr_buffer_cache = None
    if qr_buffer_data:
        qr_buffer_cache = BytesIO(qr_buffer_data)
    
    story = []
    for idx, card_num in enumerate(cards_range):
        # Shuffle songs for this card
        card_songs = random.sample(selected_songs, SONGS_PER_CARD)
        
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
            qr_buffer_cache
        )
        
        story.extend(card_elements)
        
        # Add page break after every 2 cards (except for the last card in batch)
        if (idx + 1) % 2 == 0 and idx < len(cards_range) - 1:
            story.append(PageBreak())
        # Add spacer between cards on same page
        elif idx < len(cards_range) - 1:
            story.append(Spacer(1, 5*mm))
    
    doc.build(story)
    return temp_path


def generate_cards(venue_name: str = "Music Bingo", num_players: int = 25,
                  pub_logo: str = None, social_media: str = None, include_qr: bool = False,
                  game_number: int = 1, game_date: str = None):
    """Generate all bingo cards"""
    import time
    start_time = time.time()
    
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
    step_start = time.time()
    all_songs = load_pool()
    print(f"✓ Loaded {len(all_songs)} songs from pool ({time.time()-step_start:.2f}s)")
    
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
                
                print(f"✓ Loaded pub logo ({time.time()-step_start:.2f}s)")
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
            print(f"✓ Generated QR code ({time.time()-step_start:.2f}s)")
    
    # Check if parallel processing is beneficial
    # MEMORY-OPTIMIZED: Limit workers to avoid OOM on App Platform
    num_cpus = mp.cpu_count()
    use_parallel = True  # Always use parallel - it's faster
    
    if use_parallel:
        # **PARALLEL GENERATION** - MEMORY-OPTIMIZED for cloud deployment
        print(f"\n📄 Generating PDF cards in parallel (MEMORY-OPTIMIZED)...")
        parallel_start = time.time()
        
        batch_size = 10  # 10 cards per batch
        # MEMORY OPTIMIZATION: Limit to 2 workers to avoid OOM (exit code 128)
        # App Platform has memory limits - using all cores causes out-of-memory crashes
        num_workers = min(2, num_cpus)  # Maximum 2 workers to stay within memory limits
        print(f"   Using {num_workers} parallel workers (CPUs: {num_cpus}) - MEMORY-SAFE MODE")
        
        # Prepare batch data
        batches = []
        for i in range(0, NUM_CARDS, batch_size):
            cards_range = list(range(i + 1, min(i + batch_size + 1, NUM_CARDS + 1)))
            batches.append((
                i // batch_size,
                cards_range,
                selected_songs,
                venue_name,
                pub_logo_path,
                social_media,
                include_qr,
                game_number,
                game_date,
                qr_buffer_data
            ))
        
        # Generate PDFs in parallel
        with ProcessPoolExecutor(max_workers=num_workers) as executor:
            temp_pdfs = list(executor.map(generate_batch_pdf, batches))
        
        print(f"  ✓ All batches generated ({time.time()-parallel_start:.2f}s)")
        
        # Merge all PDFs
        print(f"\n📝 Merging PDF batches...")
        merge_start = time.time()
        
        merger = PdfWriter()
        for pdf_path in temp_pdfs:
            reader = PdfReader(pdf_path)
            for page in reader.pages:
                merger.add_page(page)
        
        with open(str(OUTPUT_FILE), 'wb') as output_file:
            merger.write(output_file)
        
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
            card_songs = random.sample(selected_songs, SONGS_PER_CARD)
            
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
    
    print(f"\n{'='*60}")
    print(f"✅ SUCCESS!")
    print(f"{'='*60}")
    print(f"Generated: {OUTPUT_FILE}")
    print(f"Cards: {NUM_CARDS}")
    print(f"Pages: {(NUM_CARDS + 1) // 2} (2 cards per page)")
    print(f"Songs per card: {SONGS_PER_CARD}")
    print(f"Total songs available: {len(selected_songs)}")
    print(f"⏱️  TOTAL TIME: {total_time:.2f}s")
    print(f"{'='*60}\n")
    
    return {
        'num_cards': NUM_CARDS,
        'num_pages': (NUM_CARDS + 1) // 2,  # 2 cards per page
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
    parser.add_argument('--game_number', type=int, default=1, help='Game number (for multiple games)')
    parser.add_argument('--game_date', default=None, help='Game date (default: today)')
    
    args = parser.parse_args()
    
    generate_cards(
        venue_name=args.venue_name,
        num_players=args.num_players,
        pub_logo=args.pub_logo,
        social_media=args.social_media,
        include_qr=args.include_qr,
        game_number=args.game_number,
        game_date=args.game_date
    )
