"""
Schedule Input Validators
Validates jingle schedule inputs
"""

from typing import Dict, Any
from datetime import datetime


def validate_schedule_data(data: Dict[str, Any]) -> None:
    """
    Validate schedule creation/update data
    
    Args:
        data: Schedule data dictionary
        
    Raises:
        ValueError: If validation fails
    """
    # Validate required fields for creation
    if 'jingle_name' in data:
        jingle_name = data.get('jingle_name', '').strip()
        if not jingle_name:
            raise ValueError('Jingle name is required')
    
    if 'jingle_filename' in data:
        jingle_filename = data.get('jingle_filename', '').strip()
        if not jingle_filename:
            raise ValueError('Jingle filename is required')
    
    # Validate dates
    if 'start_date' in data:
        start_date = data.get('start_date')
        if not start_date:
            raise ValueError('Start date is required')
        
        try:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
        except ValueError:
            raise ValueError('Invalid start_date format. Use YYYY-MM-DD')
    
    if 'end_date' in data and data.get('end_date'):
        try:
            end_date_obj = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
            
            # Validate end_date is after start_date if both present
            if 'start_date' in data:
                start_date_obj = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
                if end_date_obj < start_date_obj:
                    raise ValueError('End date must be after start date')
        except ValueError as e:
            if 'format' not in str(e):
                raise
            raise ValueError('Invalid end_date format. Use YYYY-MM-DD')
    
    # Validate times
    if 'time_start' in data and data.get('time_start'):
        try:
            datetime.strptime(data['time_start'], '%H:%M').time()
        except ValueError:
            raise ValueError('Invalid time_start format. Use HH:MM')
    
    if 'time_end' in data and data.get('time_end'):
        try:
            time_end = datetime.strptime(data['time_end'], '%H:%M').time()
            
            # Validate time_end is after time_start if both present
            if 'time_start' in data and data.get('time_start'):
                time_start = datetime.strptime(data['time_start'], '%H:%M').time()
                if time_end <= time_start:
                    raise ValueError('End time must be after start time')
        except ValueError as e:
            if 'format' not in str(e):
                raise
            raise ValueError('Invalid time_end format. Use HH:MM')
    
    # Validate days_of_week
    if 'days_of_week' in data:
        days = data['days_of_week']
        if not isinstance(days, dict):
            raise ValueError('days_of_week must be a dictionary')
        
        if not any(days.values()):
            raise ValueError('At least one day of the week must be selected')
    
    # Validate repeat_pattern
    if 'repeat_pattern' in data:
        pattern = data['repeat_pattern']
        if pattern not in ['occasional', 'regular', 'often']:
            raise ValueError('Invalid repeat_pattern. Must be: occasional, regular, or often')
    
    # Validate priority
    if 'priority' in data:
        try:
            priority = int(data['priority'])
            if priority < 0 or priority > 100:
                raise ValueError('Priority must be between 0 and 100')
        except (ValueError, TypeError):
            raise ValueError('Priority must be a valid integer between 0 and 100')


def validate_status_value(status: str) -> None:
    """
    Validate status value
    
    Args:
        status: Status string to validate
        
    Raises:
        ValueError: If status is invalid
    """
    valid_statuses = ['pending', 'active', 'completed', 'cancelled']
    if status not in valid_statuses:
        raise ValueError(f'Invalid status. Must be one of: {", ".join(valid_statuses)}')
