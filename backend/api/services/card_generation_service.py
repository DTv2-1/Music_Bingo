"""
Card Generation Service - Manages bingo card generation
Handles command preparation and validation for card generation
"""

import logging
import base64
import tempfile
from typing import Dict, Any, List, Optional
from pathlib import Path

from ..utils.config import AppConfig, BASE_DIR, DATA_DIR

logger = logging.getLogger(__name__)


class CardGenerationService:
    """
    Service for bingo card generation
    
    Features:
    - Validate generation parameters
    - Prepare generation commands
    - Handle logo data (base64, URLs)
    - Build command line arguments
    """
    
    def __init__(self):
        """Initialize Card Generation Service"""
        self.script_path = BASE_DIR / 'generate_cards.py'
        self.logos_dir = DATA_DIR / 'logos'
    
    def validate_generation_params(self, params: Dict[str, Any]) -> bool:
        """
        Validate card generation parameters
        
        Args:
            params: Generation parameters
            
        Returns:
            bool: True if valid
            
        Raises:
            ValueError: If validation fails
        """
        # Validate venue name
        venue_name = params.get('venue_name', '').strip()
        if not venue_name:
            raise ValueError("Venue name is required")
        
        # Validate num_players
        num_players = int(params.get('num_players', AppConfig.DEFAULT_NUM_PLAYERS))
        if num_players < AppConfig.MIN_PLAYERS or num_players > AppConfig.MAX_PLAYERS:
            raise ValueError(f"Number of players must be between {AppConfig.MIN_PLAYERS} and {AppConfig.MAX_PLAYERS}")
        
        # Validate game_number
        game_number = int(params.get('game_number', 1))
        if game_number < 1:
            raise ValueError("Game number must be positive")
        
        logger.info(f"✅ Parameters validated: {venue_name}, {num_players} players, game #{game_number}")
        return True
    
    def prepare_generation_command(self, params: Dict[str, Any]) -> List[str]:
        """
        Prepare command for card generation script
        
        Args:
            params: Generation parameters
                - venue_name: Venue name
                - num_players: Number of cards to generate
                - game_number: Game number
                - game_date: Optional game date
                - pub_logo: Optional logo (base64 or URL)
                - social_media: Optional social media handle
                - include_qr: Boolean for QR code
                - prize_4corners: Optional prize text
                - prize_first_line: Optional prize text
                - prize_full_house: Optional prize text
                
        Returns:
            list: Command as list of arguments
        """
        # Validate first
        self.validate_generation_params(params)
        
        # Build base command
        cmd = [
            'python3',
            str(self.script_path),
            '--venue_name', params.get('venue_name', ''),
            '--num_players', str(params.get('num_players', AppConfig.DEFAULT_NUM_PLAYERS)),
            '--game_number', str(params.get('game_number', 1))
        ]
        
        # Add game date if provided
        game_date = params.get('game_date')
        if game_date:
            cmd.extend(['--game_date', game_date])
        
        # Handle logo
        pub_logo = params.get('pub_logo')
        if pub_logo:
            logo_path = self.handle_logo_data(pub_logo)
            if logo_path:
                cmd.extend(['--pub_logo', str(logo_path)])
                logger.info(f"Logo prepared: {logo_path}")
        
        # Add social media
        social_media = params.get('social_media')
        if social_media:
            cmd.extend(['--social_media', social_media])
        
        # Add QR code flag (convert boolean to string 'true'/'false')
        include_qr = params.get('include_qr', False)
        cmd.extend(['--include_qr', 'true' if include_qr else 'false'])
        
        # Add prizes
        prize_4corners = params.get('prize_4corners')
        if prize_4corners:
            cmd.extend(['--prize_4corners', prize_4corners])
        
        prize_first_line = params.get('prize_first_line')
        if prize_first_line:
            cmd.extend(['--prize_first_line', prize_first_line])
        
        prize_full_house = params.get('prize_full_house')
        if prize_full_house:
            cmd.extend(['--prize_full_house', prize_full_house])
        
        logger.info(f"Command prepared: {' '.join(cmd[:6])}... ({len(cmd)} args)")
        return cmd
    
    def handle_logo_data(self, logo_data: str) -> Optional[Path]:
        """
        Handle logo data (base64 or URL)
        
        Args:
            logo_data: Logo as base64 data URI or file path
            
        Returns:
            Path: Path to logo file, or None if invalid
        """
        if not logo_data:
            return None
        
        # Check if it's a data URI (base64)
        if logo_data.startswith('data:image/'):
            try:
                # Extract base64 data
                # Format: data:image/png;base64,iVBORw0KG...
                header, encoded = logo_data.split(',', 1)
                image_data = base64.b64decode(encoded)
                
                # Determine file extension from MIME type
                mime_type = header.split(';')[0].split(':')[1]  # e.g., 'image/png'
                extension = mime_type.split('/')[-1]  # e.g., 'png'
                
                # Save to temporary file
                self.logos_dir.mkdir(parents=True, exist_ok=True)
                import time
                timestamp = int(time.time())
                logo_path = self.logos_dir / f'temp_logo_{timestamp}.{extension}'
                
                with open(logo_path, 'wb') as f:
                    f.write(image_data)
                
                logger.info(f"✅ Decoded base64 logo: {len(image_data)} bytes -> {logo_path}")
                return logo_path
                
            except Exception as e:
                logger.error(f"❌ Error decoding logo data: {e}")
                return None
        
        # Check if it's a file path
        logo_path = Path(logo_data)
        if logo_path.exists():
            return logo_path
        
        # Check if it's a relative path from DATA_DIR
        logo_path = DATA_DIR / logo_data.lstrip('/')
        if logo_path.exists():
            return logo_path
        
        logger.warning(f"Logo not found: {logo_data}")
        return None
    
    def get_output_pdf_path(self) -> Path:
        """
        Get the expected output PDF path
        
        Returns:
            Path: Path to generated PDF
        """
        return DATA_DIR / 'cards' / 'music_bingo_cards.pdf'
    
    def cleanup_temp_logo(self, logo_path: Path) -> bool:
        """
        Clean up temporary logo file
        
        Args:
            logo_path: Path to logo file
            
        Returns:
            bool: True if deleted
        """
        if not logo_path or not logo_path.exists():
            return False
        
        # Only delete temp files
        if 'temp_logo_' in logo_path.name:
            try:
                logo_path.unlink()
                logger.info(f"✅ Cleaned up temp logo: {logo_path.name}")
                return True
            except Exception as e:
                logger.error(f"❌ Error deleting temp logo: {e}")
                return False
        
        return False
