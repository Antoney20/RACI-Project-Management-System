from django.utils import timezone
from datetime import datetime, timedelta
from .models import CalendarEvent, PublicHoliday, LeaveRequest, Project, Milestones


def sync_leave_to_calendar(leave_request):
    """Create/update calendar event for approved leave"""
    if leave_request.status != 'approved':
        # Delete calendar event if exists
        CalendarEvent.objects.filter(leave_request=leave_request).delete()
        return
    
    # Create or update calendar event
    CalendarEvent.objects.update_or_create(
        leave_request=leave_request,
        defaults={
            'title': f"{leave_request.user.get_full_name()} - {leave_request.get_leave_type_display()}",
            'description': leave_request.reason or '',
            'event_type': 'leave',
            'start_date': leave_request.start_date,
            'end_date': leave_request.end_date,
            'all_day': True,
            'user': leave_request.user,
            'is_public': True,  # Everyone can see who's on leave
            'color': '#FF6B6B',
        }
    )


def sync_project_deadline_to_calendar(project):
    """Create/update calendar event for project deadline"""
    if not project.end_date:
        CalendarEvent.objects.filter(project=project, event_type='project_deadline').delete()
        return
    
    CalendarEvent.objects.update_or_create(
        project=project,
        event_type='project_deadline',
        defaults={
            'title': f"Project Deadline: {project.name}",
            'description': project.description or '',
            'start_date': project.end_date,
            'end_date': project.end_date,
            'all_day': True,
            'is_public': True,
            'color': '#4ECDC4',
        }
    )


def sync_milestone_to_calendar(milestone):
    """Create/update calendar event for milestone"""
    if not milestone.due_date:
        CalendarEvent.objects.filter(milestone=milestone).delete()
        return
    
    CalendarEvent.objects.update_or_create(
        milestone=milestone,
        defaults={
            'title': f"Milestone: {milestone.title}",
            'description': milestone.description or '',
            'event_type': 'milestone',
            'start_date': milestone.due_date,
            'end_date': milestone.due_date,
            'all_day': True,
            'project': milestone.project,
            'is_public': True,
            'color': '#45B7D1',
        }
    )


def create_weekends_for_year(year):
    """Generate weekend events for a year"""
    start = datetime(year, 1, 1)
    end = datetime(year, 12, 31)
    
    current = start
    while current <= end:
        # Saturday = 5, Sunday = 6
        if current.weekday() in [5, 6]:
            day_name = 'Saturday' if current.weekday() == 5 else 'Sunday'
            CalendarEvent.objects.get_or_create(
                event_type='weekend',
                start_date=current,
                defaults={
                    'title': day_name,
                    'end_date': current + timedelta(days=1),
                    'all_day': True,
                    'is_public': True,
                    'color': '#D3D3D3',
                }
            )
        current += timedelta(days=1)


def sync_public_holidays_to_calendar():
    """Sync public holidays to calendar events"""
    holidays = PublicHoliday.objects.all()
    
    for holiday in holidays:
        CalendarEvent.objects.update_or_create(
            event_type='public_holiday',
            start_date=datetime.combine(holiday.date, datetime.min.time()),
            defaults={
                'title': holiday.name,
                'end_date': datetime.combine(holiday.date, datetime.max.time()),
                'all_day': True,
                'is_public': True,
                'color': '#FFA07A',
            }
        )


# Kenya public holidays 2025
KENYA_HOLIDAYS_2025 = [
    ('New Year\'s Day', '2025-01-01'),
    ('Good Friday', '2025-04-18'),
    ('Easter Monday', '2025-04-21'),
    ('Labour Day', '2025-05-01'),
    ('Madaraka Day', '2025-06-01'),
    ('Eid al-Adha', '2025-06-16'),  # Approximate, depends on moon
    ('Huduma Day', '2025-10-10'),
    ('Mashujaa Day', '2025-10-20'),
    ('Jamhuri Day', '2025-12-12'),
    ('Christmas Day', '2025-12-25'),
    ('Boxing Day', '2025-12-26'),
]


def populate_kenya_holidays(year=2025):
    """Populate Kenya public holidays"""
    for name, date_str in KENYA_HOLIDAYS_2025:
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        PublicHoliday.objects.get_or_create(
            date=date,
            year=year,
            defaults={
                'name': name,
                'is_recurring': True,
            }
        )