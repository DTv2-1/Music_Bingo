"""Quick test to verify BingoCell rendering with large grey numbers and artist/title on separate lines"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from generate_cards import BingoCell

# Sample songs: (number, artist, title)
songs = [
    (5, 'Bruno Mars', 'Finesse (Remix) [feat. Cardi B]'),
    (33, 'Young the Giant', 'Mind Over Matter'),
    (51, 'Young the Giant', 'Cough Syrup'),
    (68, 'VIOLIN COVERS', '3D'),
    (20, 'Sean Paul', 'Temperature'),
    (12, 'Jake Owen', 'Alone with You'),
    (7, 'Frankie Goes to Hollywood', 'Relax'),
    (44, 'Regard', 'Ride It'),
    (89, 'Phil Collins', 'In the Air Tonight'),
    (3, 'Queen', 'Bohemian Rhapsody'),
    (15, 'Percy Sledge', 'When a Man Loves a Woman'),
    (61, '', 'Too Many Fish In the Sea'),
    # FREE goes here (row 2, col 2)
    (72, 'Red Hot Chili Peppers', 'Dani California'),
    (45, 'Donovan', 'Season of the Witch'),
    (88, 'Earth, Wind & Fire', 'September'),
    (19, 'Paul Russell', 'Lil Boo Thang'),
    (37, 'Jason Mraz', "I Won't Give Up"),
    (55, 'The Rolling Stones', 'Sympathy For The Devil'),
    (90, 'John Denver', 'Take Me Home, Country Roads'),
    (8, 'The Outfield', 'Your Love'),
    (23, 'Wendy Rene', 'Give You What I Got'),
    (42, 'P!nk', 'Try'),
    (66, 'Five Special', 'Why Leave Us Alone'),
    (14, 'The Killers', 'Mr. Brightside'),
]

col_width = 32*mm
row_height = 12*mm
styles = getSampleStyleSheet()

grid_data = []
song_idx = 0
for row in range(5):
    row_data = []
    for col in range(5):
        if row == 2 and col == 2:
            cell_style = ParagraphStyle('FreeCell', parent=styles['Normal'], fontSize=14, textColor=colors.black, alignment=TA_CENTER, leading=12)
            cell_content = Paragraph('<b>FREE</b>', cell_style)
        else:
            num, artist, title = songs[song_idx]
            cell_content = BingoCell(bingo_number=num, artist=artist, title=title, cell_width=col_width, cell_height=row_height)
            song_idx += 1
        row_data.append(cell_content)
    grid_data.append(row_data)

table = Table(grid_data, colWidths=[col_width]*5, rowHeights=[row_height]*5)
table.setStyle(TableStyle([
    ('GRID', (0,0), (-1,-1), 1.5, colors.black),
    ('BACKGROUND', (0,0), (-1,-1), colors.white),
    ('BACKGROUND', (2,2), (2,2), colors.lightgrey),
    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ('ALIGN', (0,0), (-1,-1), 'CENTER'),
    ('LEFTPADDING', (0,0), (-1,-1), 0),
    ('RIGHTPADDING', (0,0), (-1,-1), 0),
    ('TOPPADDING', (0,0), (-1,-1), 0),
    ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ('LEFTPADDING', (2,2), (2,2), 5),
    ('RIGHTPADDING', (2,2), (2,2), 5),
    ('TOPPADDING', (2,2), (2,2), 5),
    ('BOTTOMPADDING', (2,2), (2,2), 5),
]))

doc = SimpleDocTemplate('/tmp/test_bingo_full.pdf', pagesize=A4, leftMargin=10*mm, rightMargin=10*mm, topMargin=8*mm, bottomMargin=5*mm)
doc.build([Spacer(1, 20*mm), table])
print('✅ Full 5x5 test PDF generated at /tmp/test_bingo_full.pdf')
