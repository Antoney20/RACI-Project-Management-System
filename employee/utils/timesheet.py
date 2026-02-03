from datetime import date, timedelta
from django.utils import timezone

from accounts.models import CustomUser
from employee.models import Holiday, LeaveRequest  

class AttendanceService:
    
    @staticmethod
    def get_attendance(user_id: str, start_date: date = None, end_date: date = None):
        """
        Get attendance records for a user within a date range.
        Only includes dates after the user was created.
        """
        try:
            user = CustomUser.objects.get(id=user_id)
        except CustomUser.DoesNotExist:
            return {'error': 'User not found'}
        
        today = timezone.localdate()
        start_date = start_date or date(today.year, today.month, 1)
        end_date = min(end_date or today, date(today.year + 5, 12, 31))
        
        # Get user's creation date
        user_created_date = user.created_at.date() if user.created_at else date(2026, 1, 1)
        
        # Adjust start_date to be no earlier than user creation date
        effective_start_date = max(start_date, user_created_date)
        
        # If effective start date is after end date, return empty attendance
        if effective_start_date > end_date:
            return {
                'user_id': str(user.id),
                'name': user.get_full_name(),
                'department': user.department,
                'position': user.position,
                'role': user.role,
                'created_at': user_created_date.isoformat(),
                'period': f"{start_date.isoformat()} to {end_date.isoformat()}",
                'attendance': [],
                'message': f'User created on {user_created_date.isoformat()}, after requested period'
            }

        if end_date.year < 2026:
            return {
                'user_id': str(user.id),
                'name': user.get_full_name(),
                'department': user.department,
                'position': user.position,
                'role': user.role,
                'created_at': user_created_date.isoformat(),
                'period': f"{start_date.isoformat()} to {end_date.isoformat()}",
                'attendance': [], 
                'message': 'No attendance data before 2026'
            }

        # Get holidays for the period
        holidays = {h.date: h.name for h in Holiday.objects.filter(
            date__gte=effective_start_date, date__lte=end_date
        )}
        
        # Get approved leaves for the user
        leaves = LeaveRequest.objects.filter(
            user_id=user_id, 
            status__iexact='approved',
            start_date__lte=end_date, 
            end_date__gte=effective_start_date
        ).values('start_date', 'end_date', 'leave_type')

        attendance = []
        current = effective_start_date
        
        while current <= end_date:
            day_status = {
                'date': current.isoformat(),
                'status': 'present',   
                'reason': None
            }
            
            if current > today:
                day_status['status'] = 'future'
                day_status['reason'] = 'upcoming'
            elif current.weekday() >= 5:  
                day_status['status'] = 'absent'
                day_status['reason'] = 'weekend'
            elif current in holidays:
                day_status['status'] = 'absent'
                day_status['reason'] = f'holiday - {holidays[current]}'
            else:
 
                for leave in leaves:
                    if leave['start_date'] <= current <= leave['end_date']:
                        day_status['status'] = 'absent'
                        day_status['reason'] = f"leave - {leave['leave_type']}"
                        break
            
            attendance.append(day_status)
            current += timedelta(days=1)
        
        return {
            'user_id': str(user.id),
            'name': user.get_full_name(),
            'department': user.department,
            'position': user.position,
            'role': user.role,
            'created_at': user_created_date.isoformat(),
            'period': f"{effective_start_date.isoformat()} to {end_date.isoformat()}",
            'attendance': attendance
        }