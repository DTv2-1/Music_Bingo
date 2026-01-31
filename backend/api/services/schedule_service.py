"""
Schedule Service - Manages jingle scheduling logic
Handles schedule creation, validation, and active schedule evaluation
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, date, time as dt_time
from django.db.models import Q

from ..models import JingleSchedule, BingoSession
from ..utils.config import AppConfig

logger = logging.getLogger(__name__)


class ScheduleService:
    """
    Service for managing jingle schedules
    
    Features:
    - Create and validate schedules
    - Evaluate active schedules based on current date/time
    - Filter by venue and session
    - Priority-based ordering
    """
    
    def __init__(self):
        """Initialize Schedule Service"""
        pass
    
    def create_schedule(self, schedule_data: Dict[str, Any]) -> JingleSchedule:
        """
        Create a new jingle schedule with validation
        
        Args:
            schedule_data: Dictionary with schedule information
                - jingle_name: Name of the jingle
                - jingle_filename: Filename of jingle
                - venue_name: Optional venue filter
                - session_id: Optional session filter
                - start_date: Start date (YYYY-MM-DD)
                - end_date: Optional end date
                - time_start: Optional start time (HH:MM)
                - time_end: Optional end time (HH:MM)
                - days_of_week: Dict of weekday booleans
                - repeat_pattern: 'occasional', 'regular', or 'often'
                - enabled: Boolean
                - priority: 0-100
                
        Returns:
            JingleSchedule: Created schedule instance
            
        Raises:
            ValueError: If validation fails
        """
        # Validate required fields
        jingle_name = schedule_data.get('jingle_name', '').strip()
        if not jingle_name:
            raise ValueError("Jingle name is required")
        
        jingle_filename = schedule_data.get('jingle_filename', '').strip()
        if not jingle_filename:
            raise ValueError("Jingle filename is required")
        
        # Parse dates
        start_date_str = schedule_data.get('start_date')
        if not start_date_str:
            raise ValueError("Start date is required")
        
        try:
            start_date_obj = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        except ValueError:
            raise ValueError("Invalid start_date format. Use YYYY-MM-DD")
        
        # Parse end date if provided
        end_date_obj = None
        end_date_str = schedule_data.get('end_date')
        if end_date_str:
            try:
                end_date_obj = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            except ValueError:
                raise ValueError("Invalid end_date format. Use YYYY-MM-DD")
            
            if end_date_obj < start_date_obj:
                raise ValueError("End date must be after start date")
        
        # Parse times
        time_start_obj = self._parse_time(schedule_data.get('time_start'))
        time_end_obj = self._parse_time(schedule_data.get('time_end'))
        
        if time_start_obj and time_end_obj and time_end_obj <= time_start_obj:
            raise ValueError("End time must be after start time")
        
        # Validate days of week
        days_of_week = schedule_data.get('days_of_week', {})
        if not any(days_of_week.values()):
            raise ValueError("At least one day of the week must be selected")
        
        # Validate repeat pattern
        repeat_pattern = schedule_data.get('repeat_pattern', 'regular')
        if repeat_pattern not in ['occasional', 'regular', 'often']:
            raise ValueError("Invalid repeat_pattern. Must be: occasional, regular, or often")
        
        # Validate priority
        priority = int(schedule_data.get('priority', 0))
        if priority < AppConfig.MIN_PRIORITY or priority > AppConfig.MAX_PRIORITY:
            raise ValueError(f"Priority must be between {AppConfig.MIN_PRIORITY} and {AppConfig.MAX_PRIORITY}")
        
        # Get venue and session
        venue_name = schedule_data.get('venue_name', '').strip() or None
        session_id = schedule_data.get('session_id')
        session_instance = None
        
        if session_id:
            try:
                session_instance = BingoSession.objects.get(session_id=session_id)
            except BingoSession.DoesNotExist:
                raise ValueError(f"Session not found: {session_id}")
        
        # Create schedule
        schedule = JingleSchedule.objects.create(
            jingle_name=jingle_name,
            jingle_filename=jingle_filename,
            venue_name=venue_name,
            session=session_instance,
            start_date=start_date_obj,
            end_date=end_date_obj,
            time_start=time_start_obj,
            time_end=time_end_obj,
            monday=days_of_week.get('monday', False),
            tuesday=days_of_week.get('tuesday', False),
            wednesday=days_of_week.get('wednesday', False),
            thursday=days_of_week.get('thursday', False),
            friday=days_of_week.get('friday', False),
            saturday=days_of_week.get('saturday', False),
            sunday=days_of_week.get('sunday', False),
            repeat_pattern=repeat_pattern,
            enabled=schedule_data.get('enabled', True),
            priority=priority
        )
        
        logger.info(f"✅ Created schedule #{schedule.id}: {jingle_name}")
        return schedule
    
    def update_schedule(self, schedule_id: int, update_data: Dict[str, Any]) -> JingleSchedule:
        """
        Update an existing schedule
        
        Args:
            schedule_id: ID of schedule to update
            update_data: Dictionary with fields to update
            
        Returns:
            JingleSchedule: Updated schedule
            
        Raises:
            ValueError: If validation fails
        """
        try:
            schedule = JingleSchedule.objects.get(id=schedule_id)
        except JingleSchedule.DoesNotExist:
            raise ValueError(f"Schedule not found: {schedule_id}")
        
        # Update fields if provided
        if 'jingle_name' in update_data:
            schedule.jingle_name = update_data['jingle_name'].strip()
        
        if 'jingle_filename' in update_data:
            schedule.jingle_filename = update_data['jingle_filename'].strip()
        
        if 'start_date' in update_data:
            schedule.start_date = datetime.strptime(update_data['start_date'], '%Y-%m-%d').date()
        
        if 'end_date' in update_data:
            if update_data['end_date']:
                schedule.end_date = datetime.strptime(update_data['end_date'], '%Y-%m-%d').date()
            else:
                schedule.end_date = None
        
        if 'time_start' in update_data:
            schedule.time_start = self._parse_time(update_data['time_start'])
        
        if 'time_end' in update_data:
            schedule.time_end = self._parse_time(update_data['time_end'])
        
        if 'days_of_week' in update_data:
            days = update_data['days_of_week']
            schedule.monday = days.get('monday', schedule.monday)
            schedule.tuesday = days.get('tuesday', schedule.tuesday)
            schedule.wednesday = days.get('wednesday', schedule.wednesday)
            schedule.thursday = days.get('thursday', schedule.thursday)
            schedule.friday = days.get('friday', schedule.friday)
            schedule.saturday = days.get('saturday', schedule.saturday)
            schedule.sunday = days.get('sunday', schedule.sunday)
        
        if 'repeat_pattern' in update_data:
            pattern = update_data['repeat_pattern']
            if pattern not in ['occasional', 'regular', 'often']:
                raise ValueError("Invalid repeat_pattern")
            schedule.repeat_pattern = pattern
        
        if 'enabled' in update_data:
            schedule.enabled = bool(update_data['enabled'])
        
        if 'priority' in update_data:
            priority = int(update_data['priority'])
            if priority < AppConfig.MIN_PRIORITY or priority > AppConfig.MAX_PRIORITY:
                raise ValueError(f"Priority must be between {AppConfig.MIN_PRIORITY} and {AppConfig.MAX_PRIORITY}")
            schedule.priority = priority
        
        schedule.save()
        logger.info(f"✅ Updated schedule #{schedule_id}")
        return schedule
    
    def delete_schedule(self, schedule_id: int) -> bool:
        """
        Delete a schedule
        
        Args:
            schedule_id: ID of schedule to delete
            
        Returns:
            bool: True if deleted
        """
        try:
            schedule = JingleSchedule.objects.get(id=schedule_id)
            schedule_name = schedule.jingle_name
            schedule.delete()
            logger.info(f"✅ Deleted schedule #{schedule_id}: {schedule_name}")
            return True
        except JingleSchedule.DoesNotExist:
            logger.warning(f"Schedule not found: {schedule_id}")
            return False
    
    def get_schedules(
        self,
        venue_name: Optional[str] = None,
        session_id: Optional[str] = None,
        enabled_only: bool = False
    ) -> List[JingleSchedule]:
        """
        Get schedules filtered by venue and/or session
        
        Priority order: session > venue > global
        
        Args:
            venue_name: Filter by venue
            session_id: Filter by session
            enabled_only: Only return enabled schedules
            
        Returns:
            list: Filtered schedules ordered by priority
        """
        query = JingleSchedule.objects.all()
        
        if enabled_only:
            query = query.filter(enabled=True)
        
        # Filter by session (highest priority) > venue > global
        if session_id:
            query = query.filter(
                Q(session__session_id=session_id) |
                Q(session__isnull=True, venue_name=venue_name) |
                Q(session__isnull=True, venue_name__isnull=True) |
                Q(session__isnull=True, venue_name='')
            )
        elif venue_name:
            query = query.filter(
                Q(session__venue_name=venue_name) |
                Q(session__isnull=True, venue_name=venue_name) |
                Q(session__isnull=True, venue_name__isnull=True) |
                Q(session__isnull=True, venue_name='')
            )
        
        return query.order_by('-priority', '-created_at')
    
    def get_active_schedules(
        self,
        venue_name: Optional[str] = None,
        session_id: Optional[str] = None,
        current_datetime: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get schedules that are currently active
        
        Args:
            venue_name: Filter by venue
            session_id: Filter by session
            current_datetime: Override current time (for testing)
            
        Returns:
            list: Active schedules with metadata
        """
        if current_datetime is None:
            current_datetime = datetime.now()
        
        # Get filtered schedules
        all_schedules = self.get_schedules(
            venue_name=venue_name,
            session_id=session_id,
            enabled_only=True
        )
        
        # Filter to active schedules
        active_schedules = []
        for schedule in all_schedules:
            if self.is_schedule_active(schedule, current_datetime):
                active_schedules.append({
                    'id': schedule.id,
                    'jingle_name': schedule.jingle_name,
                    'jingle_filename': schedule.jingle_filename,
                    'interval': self._get_interval_from_pattern(schedule.repeat_pattern),
                    'priority': schedule.priority,
                    'repeat_pattern': schedule.repeat_pattern
                })
        
        logger.info(f"Found {len(active_schedules)} active schedules (total: {len(all_schedules)})")
        return active_schedules
    
    def is_schedule_active(
        self,
        schedule: JingleSchedule,
        current_datetime: Optional[datetime] = None
    ) -> bool:
        """
        Check if a schedule is currently active
        
        Args:
            schedule: Schedule to check
            current_datetime: Override current time (for testing)
            
        Returns:
            bool: True if schedule should be active now
        """
        if not schedule.enabled:
            return False
        
        if current_datetime is None:
            current_datetime = datetime.now()
        
        current_date = current_datetime.date()
        current_time = current_datetime.time()
        current_weekday = current_datetime.weekday()  # 0=Monday, 6=Sunday
        
        # Check date range
        if current_date < schedule.start_date:
            return False
        
        if schedule.end_date and current_date > schedule.end_date:
            return False
        
        # Check time range
        if schedule.time_start and current_time < schedule.time_start:
            return False
        
        if schedule.time_end and current_time > schedule.time_end:
            return False
        
        # Check day of week
        day_checks = [
            schedule.monday,
            schedule.tuesday,
            schedule.wednesday,
            schedule.thursday,
            schedule.friday,
            schedule.saturday,
            schedule.sunday
        ]
        
        if not day_checks[current_weekday]:
            return False
        
        return True
    
    def _parse_time(self, time_str: Optional[str]) -> Optional[dt_time]:
        """Parse time string to time object"""
        if not time_str:
            return None
        
        try:
            return datetime.strptime(time_str, '%H:%M').time()
        except ValueError:
            raise ValueError(f"Invalid time format: {time_str}. Use HH:MM")
    
    def _get_interval_from_pattern(self, pattern: str) -> int:
        """
        Convert repeat pattern to interval number
        
        Args:
            pattern: 'occasional', 'regular', or 'often'
            
        Returns:
            int: Number of rounds between jingles
        """
        intervals = {
            'occasional': 8,  # Every 8 rounds
            'regular': 5,     # Every 5 rounds
            'often': 3        # Every 3 rounds
        }
        return intervals.get(pattern, 5)
