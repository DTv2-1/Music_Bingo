"""
Session Service - Manages bingo session lifecycle
Handles session creation, status updates, and queries
"""

import logging
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime

from django.utils import timezone

from ..models import BingoSession
from ..utils.config import AppConfig

logger = logging.getLogger(__name__)


class BingoSessionService:
    """
    Service for managing bingo sessions
    
    Features:
    - Create and configure sessions
    - Update session status and state
    - Query sessions by venue
    - Validate status transitions
    """
    
    # Valid status values
    VALID_STATUSES = ['pending', 'active', 'completed', 'cancelled']
    
    # Valid status transitions
    STATUS_TRANSITIONS = {
        'pending': ['active', 'cancelled'],
        'active': ['completed', 'cancelled'],
        'completed': [],  # Terminal state
        'cancelled': []   # Terminal state
    }
    
    def __init__(self):
        """Initialize Session Service"""
        pass
    
    def create_session(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new bingo session
        
        Args:
            session_data: Dictionary with session information
                - venue_name: Venue name
                - host_name: Optional host name
                - num_players: Number of players (default: 25)
                - voice_id: ElevenLabs voice ID
                - decades: List of decade strings
                - logo_url: Optional logo URL or data URI
                - social_media: Optional social media handle
                - include_qr: Boolean for QR code
                - prizes: Dictionary of prize information
                
        Returns:
            dict: Created session as dictionary
            
        Raises:
            ValueError: If validation fails
        """
        # Generate unique session ID
        session_id = str(uuid.uuid4())
        
        # Validate and extract data
        venue_name = session_data.get('venue_name', '').strip()
        if not venue_name:
            raise ValueError("Venue name is required")
        
        num_players = int(session_data.get('num_players', AppConfig.DEFAULT_NUM_PLAYERS))
        if num_players < AppConfig.MIN_PLAYERS or num_players > AppConfig.MAX_PLAYERS:
            raise ValueError(f"Number of players must be between {AppConfig.MIN_PLAYERS} and {AppConfig.MAX_PLAYERS}")
        
        # Get logo URL
        logo_url = session_data.get('logo_url', '')
        decades = session_data.get('decades', ['1960s', '1970s', '1980s', '1990s'])
        genres = session_data.get('genres', [])
        
        logger.info(f"Creating session for '{venue_name}' with logo length: {len(logo_url) if logo_url else 0}")
        logger.info(f"   Session filters - Decades: {decades}, Genres: {genres if genres else 'All'}")
        
        # Create session
        session = BingoSession.objects.create(
            session_id=session_id,
            venue_name=venue_name,
            host_name=session_data.get('host_name', ''),
            num_players=num_players,
            voice_id=session_data.get('voice_id', AppConfig.ELEVENLABS_VOICE_ID),
            decades=decades,
            genres=genres,
            logo_url=logo_url,
            social_media=session_data.get('social_media', ''),
            include_qr=session_data.get('include_qr', False),
            prizes=session_data.get('prizes', {}),
            status='pending'
        )
        
        logger.info(f"✅ Created session {session_id} for {venue_name}")
        logger.info(f"   Stored decades: {session.decades}")
        logger.info(f"   Stored genres: {session.genres}")
        return self._session_to_dict(session)
    
    def get_session(self, session_id: str) -> BingoSession:
        """
        Get a session by ID
        
        Args:
            session_id: Session ID
            
        Returns:
            BingoSession: Session instance
            
        Raises:
            ValueError: If session not found
        """
        try:
            return BingoSession.objects.get(session_id=session_id)
        except BingoSession.DoesNotExist:
            raise ValueError(f"Session not found: {session_id}")
    
    def update_session(self, session_id: str, update_data: Dict[str, Any]) -> BingoSession:
        """
        Update session data
        
        Args:
            session_id: Session ID
            update_data: Fields to update
            
        Returns:
            BingoSession: Updated session
        """
        session = self.get_session(session_id)
        
        # Update allowed fields
        if 'songs_played' in update_data:
            session.songs_played = update_data['songs_played']
        
        if 'current_song_index' in update_data:
            session.current_song_index = update_data['current_song_index']
        
        if 'status' in update_data:
            new_status = update_data['status']
            self.validate_status_transition(session.status, new_status)
            session.status = new_status
            
            # Update timestamps based on status
            if new_status == 'active' and not session.started_at:
                session.started_at = timezone.now()
            elif new_status in ['completed', 'cancelled'] and not session.completed_at:
                session.completed_at = timezone.now()
        
        session.save()
        logger.info(f"✅ Updated session {session_id}")
        return session
    
    def update_session_status(self, session_id: str, new_status: str) -> dict:
        """
        Update session status with validation
        
        Args:
            session_id: Session ID
            new_status: New status value
            
        Returns:
            dict: Updated session as dictionary
            
        Raises:
            ValueError: If status transition invalid
        """
        if new_status not in self.VALID_STATUSES:
            raise ValueError(f"Invalid status. Must be one of: {self.VALID_STATUSES}")
        
        session = self.get_session(session_id)
        self.validate_status_transition(session.status, new_status)
        
        session.status = new_status
        
        # Update timestamps
        if new_status == 'active' and not session.started_at:
            session.started_at = timezone.now()
        elif new_status in ['completed', 'cancelled'] and not session.completed_at:
            session.completed_at = timezone.now()
        
        session.save(update_fields=['status', 'started_at', 'completed_at'])
        
        logger.info(f"✅ Updated session {session_id} status to {new_status}")
        return self._session_to_dict(session)
    
    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session
        
        Args:
            session_id: Session ID
            
        Returns:
            bool: True if deleted
        """
        try:
            session = self.get_session(session_id)
            session.delete()
            logger.info(f"✅ Deleted session {session_id}")
            return True
        except ValueError:
            logger.warning(f"Session not found: {session_id}")
            return False
    
    def get_sessions_by_venue(self, venue_name: str) -> List[Dict[str, Any]]:
        """
        Get all sessions for a venue
        
        Args:
            venue_name: Venue name
            
        Returns:
            list: Sessions as dictionaries ordered by creation date (newest first)
        """
        sessions = BingoSession.objects.filter(
            venue_name=venue_name
        ).order_by('-created_at')
        
        return [self._session_to_dict(session) for session in sessions]
    
    def get_all_sessions(self) -> List[Dict[str, Any]]:
        """
        Get all sessions
        
        Returns:
            list: All sessions as dictionaries ordered by creation date (newest first)
        """
        sessions = BingoSession.objects.all().order_by('-created_at')
        return [self._session_to_dict(session) for session in sessions]
    
    def _session_to_dict(self, session: BingoSession) -> Dict[str, Any]:
        """
        Convert BingoSession model to dictionary
        
        Args:
            session: BingoSession model instance
            
        Returns:
            dict: Serializable dictionary
        """
        return {
            'session_id': session.session_id,
            'venue_name': session.venue_name,
            'host_name': session.host_name,
            'num_players': session.num_players,
            'voice_id': session.voice_id,
            'decades': session.decades,
            'logo_url': session.logo_url,
            'social_media': session.social_media,
            'include_qr': session.include_qr,
            'prizes': session.prizes,
            'songs_played': session.songs_played,
            'current_song_index': session.current_song_index,
            'status': session.status,
            'created_at': session.created_at.isoformat() if session.created_at else None,
            'started_at': session.started_at.isoformat() if session.started_at else None,
            'completed_at': session.completed_at.isoformat() if session.completed_at else None,
        }
    
    def validate_status_transition(self, current_status: str, new_status: str) -> bool:
        """
        Validate if status transition is allowed
        
        Args:
            current_status: Current session status
            new_status: Proposed new status
            
        Returns:
            bool: True if valid
            
        Raises:
            ValueError: If transition not allowed
        """
        if current_status == new_status:
            return True  # No change
        
        allowed_transitions = self.STATUS_TRANSITIONS.get(current_status, [])
        
        if new_status not in allowed_transitions:
            raise ValueError(
                f"Invalid status transition: {current_status} -> {new_status}. "
                f"Allowed transitions from {current_status}: {allowed_transitions}"
            )
        
        return True
    
    def get_session_summary(self, session: BingoSession) -> Dict[str, Any]:
        """
        Get a summary dictionary of session information
        
        Args:
            session: BingoSession instance
            
        Returns:
            dict: Session summary
        """
        return {
            'session_id': session.session_id,
            'venue_name': session.venue_name,
            'host_name': session.host_name,
            'num_players': session.num_players,
            'voice_id': session.voice_id,
            'decades': session.decades,
            'logo_url': session.logo_url,
            'social_media': session.social_media,
            'include_qr': session.include_qr,
            'prizes': session.prizes,
            'songs_played': session.songs_played,
            'current_song_index': session.current_song_index,
            'status': session.status,
            'created_at': session.created_at.isoformat(),
            'started_at': session.started_at.isoformat() if session.started_at else None,
            'completed_at': session.completed_at.isoformat() if session.completed_at else None
        }
