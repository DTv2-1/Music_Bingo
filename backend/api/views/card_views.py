"""
Card Generation Views

This module handles bingo card generation and logo management:
- generate_cards_async: Asynchronously generate PDF bingo cards with custom branding
- upload_logo: Handle venue logo uploads for card customization

Card generation supports:
- Custom venue names and branding
- Prize configuration (4 corners, first line, full house)
- QR code integration for social media
- Multiple players per session
- Background processing with progress tracking
- PDF caching to avoid regenerating identical cards
"""

import json
import logging
import uuid
import time
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from rest_framework.response import Response

from ..models import TaskStatus
from ..services.card_generation_service import CardGenerationService
from ..tasks import run_card_generation_task

logger = logging.getLogger(__name__)

# Get paths from config
from ..utils.config import BASE_DIR, DATA_DIR


@api_view(['POST'])
def generate_cards_async(request):
    """
    Generate cards asynchronously with caching support
    
    Checks if identical cards were generated before and returns cached PDF URL
    if parameters match. Otherwise, generates new cards.
    """
    try:
        data = request.data
        venue_name = data.get('venue_name', 'Music Bingo')
        num_players = data.get('num_players', 25)
        pub_logo = data.get('pub_logo')
        social_media = data.get('social_media')
        include_qr = data.get('include_qr', False)
        game_number = data.get('game_number', 1)
        game_date = data.get('game_date')
        
        # Get prizes
        prize_4corners = data.get('prize_4corners', '')
        prize_first_line = data.get('prize_first_line', '')
        prize_full_house = data.get('prize_full_house', '')
        
        logger.info(f"Starting async card generation: {num_players} cards for '{venue_name}'")
        
        # *** CHECK CACHE: Load existing session to see if we can reuse it ***
        session_path = DATA_DIR / 'cards' / 'current_session.json'
        cached_pdf_url = None
        should_regenerate = True
        
        if session_path.exists():
            try:
                with open(session_path, 'r', encoding='utf-8') as f:
                    existing_session = json.load(f)
                
                # Check if parameters match existing session
                params_match = (
                    existing_session.get('venue_name') == venue_name and
                    existing_session.get('num_players') == num_players and
                    existing_session.get('game_number') == game_number and
                    existing_session.get('prize_4corners') == prize_4corners and
                    existing_session.get('prize_first_line') == prize_first_line and
                    existing_session.get('prize_full_house') == prize_full_house
                )
                
                # If params match AND we have a cached PDF URL, reuse it
                if params_match and existing_session.get('pdf_url'):
                    cached_pdf_url = existing_session.get('pdf_url')
                    logger.info(f"✅ CACHE HIT: Reusing existing PDF from session")
                    logger.info(f"   PDF URL: {cached_pdf_url}")
                    should_regenerate = False
                else:
                    logger.info(f"⚠️  CACHE MISS: Parameters changed or no PDF URL, regenerating...")
                    if not params_match:
                        logger.info(f"   Params changed: venue={existing_session.get('venue_name')}→{venue_name}, "
                                  f"players={existing_session.get('num_players')}→{num_players}")
            except Exception as e:
                logger.warning(f"Could not load existing session for cache check: {e}")
        
        # If we have a cached PDF, return it immediately without regenerating
        if not should_regenerate and cached_pdf_url:
            task_id = str(uuid.uuid4())
            task = TaskStatus.objects.create(
                task_id=task_id,
                task_type='card_generation',
                status='completed',
                progress=100,
                result={
                    'success': True,
                    'pdf_url': cached_pdf_url,
                    'cached': True,
                    'message': 'Using cached PDF from previous generation'
                },
                completed_at=timezone.now(),
                metadata={
                    'venue_name': venue_name,
                    'num_players': num_players,
                    'game_number': game_number,
                    'cached': True
                }
            )
            
            return Response({
                'task_id': task_id,
                'status': 'completed',
                'cached': True,
                'pdf_url': cached_pdf_url,
                'message': 'Using cached PDF - no regeneration needed'
            }, status=200)
        
        logger.info(f"  pub_logo: {pub_logo[:100] if pub_logo else 'None'}...")
        logger.info(f"  pub_logo type: {type(pub_logo)}, length: {len(pub_logo) if pub_logo else 0}")
        logger.info(f"  social_media: {social_media}, include_qr: {include_qr}")
        logger.info(f"  prizes: {prize_4corners}, {prize_first_line}, {prize_full_house}")
        
        task_id = str(uuid.uuid4())
        
        # Create task in database
        task = TaskStatus.objects.create(
            task_id=task_id,
            task_type='card_generation',
            status='pending',
            progress=0,
            metadata={
                'venue_name': venue_name,
                'num_players': num_players,
                'game_number': game_number
            }
        )
        
        # Use CardGenerationService to prepare command
        card_service = CardGenerationService()
        cmd = card_service.prepare_generation_command({
            'venue_name': venue_name,
            'num_players': num_players,
            'game_number': game_number,
            'game_date': game_date,
            'pub_logo': pub_logo,
            'social_media': social_media,
            'include_qr': include_qr,
            'prize_4corners': prize_4corners,
            'prize_first_line': prize_first_line,
            'prize_full_house': prize_full_house
        })
        
        # Run task in background using task module
        run_card_generation_task(task_id, task, cmd, BASE_DIR)
        
        return Response({'task_id': task_id, 'status': 'pending'}, status=202)
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@csrf_exempt
def upload_logo(request):
    """Upload pub logo"""
    try:
        logger.info(f"upload_logo called - FILES: {list(request.FILES.keys())}")
        logger.info(f"upload_logo - DATA_DIR: {DATA_DIR}")
        
        if 'logo' not in request.FILES:
            logger.warning("No 'logo' file in request.FILES")
            return Response({'error': 'No file provided'}, status=400)
        
        file = request.FILES['logo']
        logger.info(f"File received: name={file.name}, size={file.size}")
        
        if not file.name:
            return Response({'error': 'No file selected'}, status=400)
        
        allowed_extensions = {'png', 'jpg', 'jpeg', 'svg', 'gif', 'webp'}
        file_ext = file.name.rsplit('.', 1)[1].lower() if '.' in file.name else ''
        
        if file_ext not in allowed_extensions:
            return Response({'error': f'Invalid file type. Allowed: {", ".join(allowed_extensions)}'}, status=400)
        
        logos_dir = DATA_DIR / 'logos'
        logger.info(f"Creating logos dir: {logos_dir}")
        logos_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = int(time.time())
        safe_filename = f'pub_logo_{timestamp}.{file_ext}'
        file_path = logos_dir / safe_filename
        
        logger.info(f"Saving file to: {file_path}")
        with open(file_path, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)
        
        logo_url = f'/data/logos/{safe_filename}'
        logger.info(f"File saved successfully: {file_path}, URL: {logo_url}")
        
        return Response({
            'success': True,
            'url': logo_url,
            'filename': safe_filename
        })
        
    except Exception as e:
        logger.error(f"Error uploading logo: {e}", exc_info=True)
        return Response({'error': str(e)}, status=500)
