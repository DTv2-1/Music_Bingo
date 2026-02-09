"""
Jingle Schedule Management Views

This module provides scheduling system for automated jingle playback:
- create_jingle_schedule: Create/list jingle schedules with time/date constraints
- get_active_jingles: Get currently active jingles based on schedule rules
- update_jingle_schedule: Update existing schedule parameters
- delete_jingle_schedule: Remove jingle schedules

Schedule Features:
- Date ranges (start_date, end_date)
- Time windows (time_start, time_end)
- Day of week selection (Monday-Sunday)
- Repeat patterns (occasional, regular, often)
- Priority system (0-100)
- Enable/disable toggle

Active schedule evaluation considers:
- Current date within date range
- Current time within time window (if specified)
- Current day matches selected days
- Schedule is enabled
- Sorted by priority (highest first)
"""

import logging
from rest_framework.decorators import api_view
from rest_framework.response import Response

from ..services.schedule_service import ScheduleService

logger = logging.getLogger(__name__)


@api_view(['POST', 'GET'])
def create_jingle_schedule(request):
    """
    Create a new jingle schedule or list all schedules
    POST /api/jingle-schedules - Create new schedule
    GET /api/jingle-schedules - List all schedules
    
    POST Body: {
        "jingle_name": "Tuesday Night Taco Promotion",
        "jingle_filename": "jingle_67890.mp3",
        "start_date": "2026-01-14",
        "end_date": "2026-03-31",
        "time_start": "17:00",
        "time_end": "22:00",
        "days_of_week": {
            "monday": false,
            "tuesday": true,
            ...
        },
        "repeat_pattern": "regular",
        "enabled": true,
        "priority": 10
    }
    
    Returns: {
        "success": true,
        "schedule_id": 1,
        "message": "Schedule created successfully"
    }
    """
    logger.info(f'\n{"="*60}')
    logger.info(f'{request.method} /api/jingle-schedules endpoint called')
    logger.info(f'Request method: {request.method}')
    logger.info(f'Request content-type: {request.content_type}')
    
    if request.method == 'GET':
        # List all schedules
        try:
            # Get venue_name from query params
            venue_name = request.GET.get('venue_name')
            session_id = request.GET.get('session_id')
            
            # Use ScheduleService to get schedules
            schedule_service = ScheduleService()
            schedules_queryset = schedule_service.get_schedules(
                venue_name=venue_name,
                session_id=session_id
            )
            
            # Serialize model objects to dicts
            schedules_list = []
            for schedule in schedules_queryset:
                schedules_list.append({
                    'id': schedule.id,
                    'jingle_name': schedule.jingle_name,
                    'jingle_filename': schedule.jingle_filename,
                    'venue_name': schedule.venue_name or '',
                    'session_id': schedule.session_id,
                    'start_date': schedule.start_date.isoformat() if schedule.start_date else None,
                    'end_date': schedule.end_date.isoformat() if schedule.end_date else None,
                    'time_start': schedule.time_start.strftime('%H:%M') if schedule.time_start else None,
                    'time_end': schedule.time_end.strftime('%H:%M') if schedule.time_end else None,
                    'days_of_week': {
                        'monday': schedule.monday,
                        'tuesday': schedule.tuesday,
                        'wednesday': schedule.wednesday,
                        'thursday': schedule.thursday,
                        'friday': schedule.friday,
                        'saturday': schedule.saturday,
                        'sunday': schedule.sunday,
                    },
                    'repeat_pattern': schedule.repeat_pattern,
                    'enabled': schedule.enabled,
                    'priority': schedule.priority,
                    'created_at': schedule.created_at.isoformat() if schedule.created_at else None,
                    'updated_at': schedule.updated_at.isoformat() if schedule.updated_at else None,
                })
            
            logger.info(f'✅ Listed {len(schedules_list)} jingle schedules')
            for schedule in schedules_list:
                logger.info(f"  - {schedule['jingle_name']} (enabled: {schedule['enabled']}, priority: {schedule['priority']})")
            
            return Response({
                'schedules': schedules_list
            })
            
        except Exception as e:
            logger.error(f"Error listing jingle schedules: {e}", exc_info=True)
            return Response({
                'error': str(e)
            }, status=500)
    
    # POST: Create new schedule
    try:
        data = request.data
        
        # Use ScheduleService to create schedule
        schedule_service = ScheduleService()
        result = schedule_service.create_schedule(data)
        
        logger.info(f"Created jingle schedule #{result['schedule_id']}: {data.get('jingle_name')}")
        
        return Response(result, status=201)
        
    except ValueError as e:
        return Response({
            'error': str(e)
        }, status=400)
    except Exception as e:
        logger.error(f"Error creating jingle schedule: {e}", exc_info=True)
        return Response({
            'error': str(e)
        }, status=500)


@api_view(['GET'])
def get_active_jingles(request):
    """
    Get all currently active jingle schedules
    GET /api/jingle-schedules/active
    
    Evaluates each schedule based on:
    - enabled flag
    - current date within date range
    - current time within time range (if specified)
    - current day of week matches selected days
    
    Returns schedules sorted by priority (highest first)
    
    Returns: {
        "active_jingles": [
            {
                "id": 1,
                "jingle_name": "Tuesday Night Taco Promotion",
                "jingle_filename": "jingle_67890.mp3",
                "interval": 6,
                "priority": 10
            }
        ]
    }
    """
    logger.info(f'\n{"="*60}')
    logger.info('📥 GET /api/jingle-schedules/active - Get active jingles endpoint called')
    logger.info(f'Request method: {request.method}')
    logger.info(f'Request path: {request.path}')
    try:
        # Get venue_name from query params
        venue_name = request.GET.get('venue_name')
        session_id = request.GET.get('session_id')
        
        # Use ScheduleService to get active schedules
        schedule_service = ScheduleService()
        active_schedules = schedule_service.get_active_schedules(
            venue_name=venue_name,
            session_id=session_id
        )
        
        logger.info(f'✅ Found {len(active_schedules)} active jingle schedules')
        for schedule in active_schedules:
            logger.info(f"  - {schedule['jingle_name']} (interval: {schedule['interval']}, priority: {schedule['priority']})")
        
        return Response({
            'active_jingles': active_schedules
        })
        
    except Exception as e:
        logger.error(f"Error getting active jingles: {e}", exc_info=True)
        return Response({
            'error': str(e)
        }, status=500)


@api_view(['PUT'])
def update_jingle_schedule(request, schedule_id):
    """
    Update an existing jingle schedule
    PUT /api/jingle-schedules/<schedule_id>
    
    Body: {
        "enabled": false,
        "priority": 5,
        "end_date": "2026-06-30",
        ... (any fields to update)
    }
    
    Returns: {
        "success": true,
        "message": "Schedule updated successfully"
    }
    """
    try:
        from ..models import JingleSchedule
        from datetime import datetime
        from ..utils.config import DATA_DIR
        
        # Get schedule by ID
        try:
            schedule = JingleSchedule.objects.get(id=schedule_id)
        except JingleSchedule.DoesNotExist:
            return Response({
                'error': f'Schedule with id {schedule_id} not found'
            }, status=404)
        
        data = request.data
        
        # Update fields if provided
        if 'jingle_name' in data:
            schedule.jingle_name = data['jingle_name'].strip()
        
        if 'jingle_filename' in data:
            jingle_filename = data['jingle_filename'].strip()
            # Optionally verify file exists
            jingles_dir = DATA_DIR / 'jingles'
            jingle_path = jingles_dir / jingle_filename
            if not jingle_path.exists():
                logger.warning(f'Jingle file not found at {jingle_path}, but continuing anyway')
            schedule.jingle_filename = jingle_filename
        
        if 'start_date' in data:
            try:
                schedule.start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
            except ValueError:
                return Response({
                    'error': 'Invalid start_date format. Use YYYY-MM-DD'
                }, status=400)
        
        if 'end_date' in data:
            if data['end_date']:
                try:
                    end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
                    if end_date < schedule.start_date:
                        return Response({
                            'error': 'End date must be after start date'
                        }, status=400)
                    schedule.end_date = end_date
                except ValueError:
                    return Response({
                        'error': 'Invalid end_date format. Use YYYY-MM-DD'
                    }, status=400)
            else:
                schedule.end_date = None
        
        if 'time_start' in data:
            if data['time_start']:
                try:
                    schedule.time_start = datetime.strptime(data['time_start'], '%H:%M').time()
                except ValueError:
                    return Response({
                        'error': 'Invalid time_start format. Use HH:MM'
                    }, status=400)
            else:
                schedule.time_start = None
        
        if 'time_end' in data:
            if data['time_end']:
                try:
                    schedule.time_end = datetime.strptime(data['time_end'], '%H:%M').time()
                except ValueError:
                    return Response({
                        'error': 'Invalid time_end format. Use HH:MM'
                    }, status=400)
            else:
                schedule.time_end = None
        
        # Validate time_end is after time_start
        if schedule.time_start and schedule.time_end and schedule.time_end <= schedule.time_start:
            return Response({
                'error': 'End time must be after start time'
            }, status=400)
        
        if 'days_of_week' in data:
            days = data['days_of_week']
            schedule.monday = days.get('monday', schedule.monday)
            schedule.tuesday = days.get('tuesday', schedule.tuesday)
            schedule.wednesday = days.get('wednesday', schedule.wednesday)
            schedule.thursday = days.get('thursday', schedule.thursday)
            schedule.friday = days.get('friday', schedule.friday)
            schedule.saturday = days.get('saturday', schedule.saturday)
            schedule.sunday = days.get('sunday', schedule.sunday)
            
            # Validate at least one day selected
            if not any([schedule.monday, schedule.tuesday, schedule.wednesday, 
                       schedule.thursday, schedule.friday, schedule.saturday, schedule.sunday]):
                return Response({
                    'error': 'At least one day of the week must be selected'
                }, status=400)
        
        if 'repeat_pattern' in data:
            pattern = data['repeat_pattern']
            if pattern not in ['occasional', 'regular', 'often']:
                return Response({
                    'error': 'Invalid repeat_pattern. Must be: occasional, regular, or often'
                }, status=400)
            schedule.repeat_pattern = pattern
        
        if 'enabled' in data:
            schedule.enabled = bool(data['enabled'])
        
        if 'priority' in data:
            priority = int(data['priority'])
            if priority < 0 or priority > 100:
                return Response({
                    'error': 'Priority must be between 0 and 100'
                }, status=400)
            schedule.priority = priority
        
        # Save changes
        schedule.save()
        
        logger.info(f"Updated jingle schedule #{schedule.id}: {schedule.jingle_name}")
        
        return Response({
            'success': True,
            'message': 'Schedule updated successfully'
        })
        
    except Exception as e:
        logger.error(f"Error updating jingle schedule: {e}", exc_info=True)
        return Response({
            'error': str(e)
        }, status=500)


@api_view(['DELETE'])
def delete_jingle_schedule(request, schedule_id):
    """
    Delete a jingle schedule
    DELETE /api/jingle-schedules/<schedule_id>
    
    Returns: {
        "success": true,
        "message": "Schedule deleted successfully"
    }
    """
    try:
        # Use ScheduleService to delete schedule
        schedule_service = ScheduleService()
        result = schedule_service.delete_schedule(schedule_id)
        
        logger.info(f"Deleted jingle schedule #{schedule_id}")
        
        return Response(result)
        
    except ValueError as e:
        return Response({
            'error': str(e)
        }, status=404)
    except Exception as e:
        logger.error(f"Error deleting jingle schedule: {e}", exc_info=True)
        return Response({
            'error': str(e)
        }, status=500)
