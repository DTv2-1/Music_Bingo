"""
Karafun Business API Client
Handles integration with Karafun Business API for device and session management
"""

import logging
import requests
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class KarafunAPIClient:
    """Client for Karafun Business API"""
    
    BASE_URL = "https://api.business.karafun.com"
    
    def __init__(self, api_token: str):
        """
        Initialize Karafun API client
        
        Args:
            api_token: Bearer token for authentication
        """
        self.api_token = api_token
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }
    
    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        Make HTTP request to Karafun API
        
        Args:
            method: HTTP method (GET, POST, PATCH, DELETE)
            endpoint: API endpoint path
            **kwargs: Additional arguments for requests
            
        Returns:
            JSON response data
            
        Raises:
            requests.HTTPError: If request fails
        """
        url = f"{self.BASE_URL}{endpoint}"
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=self.headers,
                **kwargs
            )
            response.raise_for_status()
            
            # Return empty dict for 204 No Content
            if response.status_code == 204:
                return {}
                
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Karafun API request failed: {method} {url} - {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            raise
    
    # ============================================================
    # DEVICE ENDPOINTS
    # ============================================================
    
    def list_devices(self) -> List[Dict[str, Any]]:
        """
        Get list of all devices
        
        Returns:
            List of device objects with id, name, active status, etc.
        """
        logger.info("📱 Fetching Karafun devices list")
        devices = self._request("GET", "/device/list")
        logger.info(f"   Found {len(devices)} devices")
        return devices
    
    def edit_device(
        self, 
        device_id: int, 
        name: Optional[str] = None,
        parental_control: Optional[bool] = None,
        show_quiz: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Edit device settings
        
        Args:
            device_id: The device ID
            name: New device name (optional)
            parental_control: Enable/disable parental control (optional)
            show_quiz: Enable/disable quiz (optional)
            
        Returns:
            Updated device object
        """
        logger.info(f"✏️ Editing Karafun device {device_id}")
        
        data = {}
        if name is not None:
            data['name'] = name
        if parental_control is not None:
            data['parental_control'] = parental_control
        if show_quiz is not None:
            data['show_quiz'] = show_quiz
        
        return self._request("PATCH", f"/device/{device_id}/", json=data)
    
    # ============================================================
    # SESSION ENDPOINTS
    # ============================================================
    
    def get_sessions(
        self,
        start_at_timestamp: Optional[str] = None,
        end_at_timestamp: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get sessions between two dates
        
        Args:
            start_at_timestamp: Start date in ISO 8601 format (e.g. '2025-03-30T01:00:00+01:00')
            end_at_timestamp: End date in ISO 8601 format (e.g. '2025-03-30T03:00:00+02:00')
            
        Returns:
            List of session objects
        """
        logger.info("📋 Fetching Karafun sessions")
        
        params = {}
        if start_at_timestamp:
            params['start_at_timestamp'] = start_at_timestamp
        if end_at_timestamp:
            params['end_at_timestamp'] = end_at_timestamp
        
        sessions = self._request("GET", "/session/", params=params)
        logger.info(f"   Found {len(sessions)} sessions")
        return sessions
    
    def create_session(
        self,
        device_id: int,
        start_at_timestamp: str,
        end_at_timestamp: str,
        locale: str = "en",
        customer_firstname: Optional[str] = None,
        comment: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new Karafun session
        
        Args:
            device_id: The device ID to use
            start_at_timestamp: Session start in ISO 8601 format
            end_at_timestamp: Session end in ISO 8601 format
            locale: Session locale (default: 'en')
            customer_firstname: Customer first name (optional)
            comment: Session comment (optional)
            
        Returns:
            Created session object with ID
        """
        logger.info(f"🎤 Creating Karafun session on device {device_id}")
        
        data = {
            "device_id": device_id,
            "start_at_timestamp": start_at_timestamp,
            "end_at_timestamp": end_at_timestamp,
            "locale": locale
        }
        
        if customer_firstname:
            data['customer_firstname'] = customer_firstname
        if comment:
            data['comment'] = comment
        
        session = self._request("POST", "/session/", json=data)
        logger.info(f"   ✅ Created session {session.get('id')}")
        return session
    
    def get_session(self, session_id: int) -> Dict[str, Any]:
        """
        Get specific session information
        
        Args:
            session_id: The session ID
            
        Returns:
            Session object
        """
        logger.info(f"🔍 Fetching Karafun session {session_id}")
        return self._request("GET", f"/session/{session_id}/")
    
    def edit_session(
        self,
        session_id: int,
        device_id: Optional[int] = None,
        start_at_timestamp: Optional[str] = None,
        end_at_timestamp: Optional[str] = None,
        locale: Optional[str] = None,
        customer_firstname: Optional[str] = None,
        comment: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Edit an existing session
        
        Args:
            session_id: The session ID to edit
            (other args same as create_session, all optional)
            
        Returns:
            Updated session object
        """
        logger.info(f"✏️ Editing Karafun session {session_id}")
        
        data = {}
        if device_id is not None:
            data['device_id'] = device_id
        if start_at_timestamp is not None:
            data['start_at_timestamp'] = start_at_timestamp
        if end_at_timestamp is not None:
            data['end_at_timestamp'] = end_at_timestamp
        if locale is not None:
            data['locale'] = locale
        if customer_firstname is not None:
            data['customer_firstname'] = customer_firstname
        if comment is not None:
            data['comment'] = comment
        
        return self._request("PATCH", f"/session/{session_id}/", json=data)
    
    def delete_session(self, session_id: int) -> None:
        """
        Delete a session
        
        Args:
            session_id: The session ID to delete
        """
        logger.info(f"🗑️ Deleting Karafun session {session_id}")
        self._request("DELETE", f"/session/{session_id}/")
        logger.info("   ✅ Session deleted")


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_karafun_client() -> Optional[KarafunAPIClient]:
    """
    Get configured Karafun API client
    
    Returns:
        KarafunAPIClient instance or None if not configured
    """
    from django.conf import settings
    
    token = getattr(settings, 'KARAFUN_API_TOKEN', None)
    if not token:
        logger.warning("⚠️ KARAFUN_API_TOKEN not configured in settings")
        return None
    
    return KarafunAPIClient(token)
