"""
MyTeam Service

Provides team management data for supervisors and admins:
- Team member listing with key stats
- Leave status overview
- Activities and milestones tracking
- Pending supervisor reviews

Optimized queries with select_related/prefetch_related.
"""

import logging
from datetime import timedelta
from django.utils import timezone
from django.db.models import Q, Count, Prefetch
from django.contrib.auth import get_user_model

from employee.models import LeaveRequest, EmployeeSupervisor, EmployeeContract
from projects.models import Activity, Milestone, SupervisorReview

logger = logging.getLogger(__name__)
User = get_user_model()


class MyTeamService:
    """Handle team management operations for supervisors"""
    
    @staticmethod
    def get_team_members(supervisor):
        """
        Get all team members with their key stats.
        
        Returns list of team members with:
        - Basic info (name, email, role)
        - Activity counts (total, in_progress, overdue)
        - Milestone counts (upcoming, overdue)
        - Current leave status
        """
        team_relationships = EmployeeSupervisor.objects.filter(
            supervisor=supervisor,
            is_active=True
        ).select_related('employee').order_by('employee__first_name')
        
        team_data = []
        today = timezone.now()
        
        for rel in team_relationships:
            member = rel.employee
            
            # Activity stats
            activities = Activity.objects.filter(responsible=member)
            activity_stats = {
                'total': activities.count(),
                'in_progress': activities.filter(status='in_progress').count(),
                'overdue': activities.filter(
                    deadline__lt=today,
                    status__in=['not_started', 'in_progress']
                ).count(),
                'completed_this_month': activities.filter(
                    status='completed',
                    completed_at__gte=today.replace(day=1)
                ).count()
            }
            
            # Milestone stats
            milestones = Milestone.objects.filter(assigned_to=member)
            milestone_stats = {
                'upcoming': milestones.filter(
                    status__in=['not_started', 'in_progress'],
                    due_date__gte=today
                ).count(),
                'overdue': milestones.filter(
                    status__in=['not_started', 'in_progress'],
                    due_date__lt=today
                ).count()
            }
            
            # Current leave status
            on_leave = LeaveRequest.objects.filter(
                user=member,
                status='approved',
                start_date__lte=today.date(),
                end_date__gte=today.date()
            ).first()
            
            team_data.append({
                'id': str(member.id),
                'name': member.get_full_name() or member.username,
                'email': member.email,
                'role': getattr(member, 'role', 'staff'),
                'activities': activity_stats,
                'milestones': milestone_stats,
                'on_leave': {
                    'status': True,
                    'type': on_leave.leave_type,
                    'end_date': on_leave.end_date
                } if on_leave else {'status': False},
                'relationship_id': str(rel.id)
            })
        
        return team_data
    
    
    @staticmethod
    def get_team_leave_requests(supervisor, status_filter=None):
        """Get leave requests from team members"""
        supervised_ids = EmployeeSupervisor.objects.filter(
            supervisor=supervisor,
            is_active=True
        ).values_list('employee_id', flat=True)
        
        queryset = LeaveRequest.objects.filter(
            user_id__in=supervised_ids
        ).select_related('user', 'contract').order_by('-created_at')
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return [{
            'id': str(lr.id),
            'employee_id': str(lr.user.id),
            'employee_name': lr.user.get_full_name(),
            'type': lr.leave_type,
            'start_date': lr.start_date,
            'end_date': lr.end_date,
            'days': float(lr.days_requested),
            'status': lr.status,
            'created_at': lr.created_at,
            'reason': lr.reason if hasattr(lr, 'reason') else None
        } for lr in queryset]
    
    
    @staticmethod
    def get_team_activities(supervisor, filters=None):
        """
        Get activities where team members are responsible.
        
        Filters: status, deadline_range, priority
        """
        supervised_ids = EmployeeSupervisor.objects.filter(
            supervisor=supervisor,
            is_active=True
        ).values_list('employee_id', flat=True)
        
        queryset = Activity.objects.filter(
            responsible_id__in=supervised_ids
        ).select_related('responsible', 'project').order_by('-deadline')
        
        # Apply filters
        if filters:
            if 'status' in filters:
                queryset = queryset.filter(status=filters['status'])
            
            if 'overdue_only' in filters and filters['overdue_only']:
                queryset = queryset.filter(
                    deadline__lt=timezone.now(),
                    status__in=['not_started', 'in_progress']
                )
        
        return [{
            'id': str(act.id),
            'name': act.name,
            'project': act.project.name,
            'responsible': act.responsible.get_full_name(),
            'responsible_id': str(act.responsible.id),
            'status': act.status,
            'deadline': act.deadline,
            'priority': getattr(act, 'priority', None),
            'is_overdue': act.deadline < timezone.now() if act.deadline else False
        } for act in queryset[:50]]  # Limit to 50 for performance
    
    
    @staticmethod
    def get_pending_reviews(supervisor):
        """Get supervisor reviews assigned to this supervisor"""
        reviews = SupervisorReview.objects.filter(
            reviewer=supervisor,
            review_level='supervisor',
            status__in=['not_started', 'started']
        ).select_related(
            'activity',
            'activity__project',
            'activity__responsible'
        ).order_by('created_at')
        
        return [{
            'id': str(review.id),
            'activity_id': str(review.activity.id),
            'activity_name': review.activity.name,
            'project': review.activity.project.name,
            'responsible': review.activity.responsible.get_full_name(),
            'status': review.status,
            'created_at': review.created_at,
            'due_date': getattr(review, 'due_date', None)
        } for review in reviews]