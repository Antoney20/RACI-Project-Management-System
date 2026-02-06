"""
Dashboard Statistics Service

Provides role-based dashboard data:
- Admin: Pending leave requests, system overview, team activities
- Supervisor: Team leave requests, supervised activities, reviews pending
- Staff: Personal activities, milestones, leave balance

Keep it simple, fast, and focused.
"""

import logging
from datetime import timedelta
from django.utils import timezone
from django.db.models import Q, Count, Prefetch
from django.contrib.auth import get_user_model

from decimal import Decimal
from employee.models import LeaveRequest, EmployeeContract, EmployeeSupervisor
from employee.utils.leave_logic import get_leave_balance
from projects.models import Activity, Milestone, SupervisorReview, Project

logger = logging.getLogger(__name__)
User = get_user_model()


class DashboardStatsService:
    """Generate role-based dashboard statistics"""
    
    @staticmethod
    def get_stats(user):
        """
        Main entry point - returns stats based on user role.
        
        Args:
            user: User object with role attribute
            
        Returns:
            dict: Role-specific dashboard statistics
        """
        role = getattr(user, 'role', 'staff')
        
        if role == 'admin':
            return DashboardStatsService._admin_stats(user)
        elif role == 'supervisor':
            return DashboardStatsService._supervisor_stats(user)
        else:
            return DashboardStatsService._staff_stats(user)
    
    
    @staticmethod
    def _admin_stats(user):
        """Admin dashboard: System overview + actionable items"""
        today = timezone.now()
        week_start = today - timedelta(days=7)
        
        # Pending leave requests (needs action)
        pending_leaves = LeaveRequest.objects.filter(
            status='pending'
        ).select_related('user', 'contract').order_by('created_at')[:10]
        
        # This week's activity summary
        activities_due_this_week = Activity.objects.filter(
            deadline__gte=today,
            deadline__lt=today + timedelta(days=7),
            status__in=['not_started', 'in_progress']
        ).count()
        
        activities_completed_this_week = Activity.objects.filter(
            completed_at__gte=week_start,
            status='completed'
        ).count()
        
        overdue_activities = Activity.objects.filter(
            deadline__lt=today,
            status__in=['not_started', 'in_progress']
        ).count()
        
        # Pending reviews (admin level)
        pending_admin_reviews = SupervisorReview.objects.filter(
            review_level='admin',
            status__in=['not_started', 'started']
        ).select_related('activity', 'activity__project').order_by('created_at')[:10]
        
        # Contracts expiring soon (next 30 days)
        contracts_expiring = EmployeeContract.objects.filter(
            is_current=True,
            is_expired=False,
            end_date__lte=today.date() + timedelta(days=30),
            end_date__gte=today.date()
        ).select_related('user').order_by('end_date')[:10]
        
        return {
            'role': 'admin',
            'leave_requests': {
                'pending_count': pending_leaves.count(),
                'items': [{
                    'id': str(lr.id),
                    'employee': lr.user.get_full_name(),
                    'type': lr.leave_type,
                    'start_date': lr.start_date,
                    'end_date': lr.end_date,
                    'days': float(lr.days_requested),
                    'created': lr.created_at,
                } for lr in pending_leaves]
            },
            'activities': {
                'due_this_week': activities_due_this_week,
                'completed_this_week': activities_completed_this_week,
                'overdue': overdue_activities,
            },
            'reviews': {
                'pending_count': pending_admin_reviews.count(),
                'items': [{
                    'id': str(review.id),
                    'activity': review.activity.name,
                    'project': review.activity.project.name,
                    'status': review.status,
                    'created': review.created_at,
                } for review in pending_admin_reviews]
            },
            'contracts': {
                'expiring_count': contracts_expiring.count(),
                'items': [{
                    'id': str(contract.id),
                    'employee': contract.user.get_full_name(),
                    'end_date': contract.end_date,
                    'days_remaining': (contract.end_date - today.date()).days,
                } for contract in contracts_expiring]
            }
        }
    
    
    @staticmethod
    def _supervisor_stats(user):
        """Supervisor dashboard: Team management + reviews"""
        today = timezone.now()
        
        # Get team members
        supervised_employees = EmployeeSupervisor.objects.filter(
            supervisor=user,
            is_active=True
        ).values_list('employee_id', flat=True)
        
        # Team leave requests
        team_leave_pending = LeaveRequest.objects.filter(
            user_id__in=supervised_employees,
            status='pending'
        ).select_related('user', 'contract').order_by('created_at')[:10]
        
        # Activities where supervisor is involved
        my_activities = Activity.objects.filter(
            Q(accountable=user) | Q(responsible=user) |
            Q(consulted=user) | Q(informed=user)
        ).select_related('project').order_by('-deadline')
        
        # Categorize activities
        activities_in_progress = my_activities.filter(status='in_progress').count()
        activities_due_soon = my_activities.filter(
            deadline__gte=today,
            deadline__lt=today + timedelta(days=7),
            status__in=['not_started', 'in_progress']
        )[:10]
        
        activities_overdue = my_activities.filter(
            deadline__lt=today,
            status__in=['not_started', 'in_progress']
        )[:10]
        
        pending_reviews = SupervisorReview.objects.filter(
            reviewer=user,
            review_level='supervisor',
            status__in=['not_started', 'started']
        ).select_related('activity', 'activity__project').order_by('created_at')[:10]
        
        return {
            'role': 'supervisor',
            'team': {
                'member_count': len(supervised_employees),
                'pending_leaves': {
                    'count': team_leave_pending.count(),
                    'items': [{
                        'id': str(lr.id),
                        'employee': lr.user.get_full_name(),
                        'type': lr.leave_type,
                        'start_date': lr.start_date,
                        'end_date': lr.end_date,
                        'days': float(lr.days_requested),
                    } for lr in team_leave_pending]
                }
            },
            'activities': {
                'in_progress': activities_in_progress,
                'due_soon': [{
                    'id': str(act.id),
                    'name': act.name,
                    'project': act.project.name,
                    'deadline': act.deadline,
                    'role': DashboardStatsService._get_my_role(user, act),
                    'status': act.status,
                } for act in activities_due_soon],
                'overdue': [{
                    'id': str(act.id),
                    'name': act.name,
                    'project': act.project.name,
                    'deadline': act.deadline,
                    'role': DashboardStatsService._get_my_role(user, act),
                    'days_overdue': (today - act.deadline).days,
                } for act in activities_overdue]
            },
            'reviews': {
                'pending_count': pending_reviews.count(),
                'items': [{
                    'id': str(review.id),
                    'activity': review.activity.name,
                    'project': review.activity.project.name,
                    'status': review.status,
                    'created': review.created_at,
                } for review in pending_reviews]
            }
        }
    

    @staticmethod
    def _staff_stats(user):
        """Staff dashboard: Personal activities + milestones + leave"""
        today = timezone.now()
        
        # Leave balance
        leave_balance = DashboardStatsService._get_leave_summary(user)
        
        # My activities (as responsible person)
        my_activities = Activity.objects.filter(
            responsible=user
        ).select_related('project')
        
        activities_in_progress = my_activities.filter(
            status='in_progress'
        ).order_by('deadline')[:10]
        
        activities_due_soon = my_activities.filter(
            deadline__gte=today,
            deadline__lt=today + timedelta(days=7),
            status__in=['not_started', 'in_progress']
        ).order_by('deadline')[:10]
        
        activities_overdue = my_activities.filter(
            deadline__lt=today,
            status__in=['not_started', 'in_progress']
        ).order_by('deadline')[:5]
        
        # Upcoming milestones
        my_milestones = Milestone.objects.filter(
            assigned_to=user,
            status__in=['not_started', 'in_progress'],
            due_date__gte=today
        ).select_related('activity', 'activity__project').order_by('due_date')[:10]
        
        # Recent leave requests
        recent_leaves = LeaveRequest.objects.filter(
            user=user
        ).select_related('contract').order_by('-created_at')[:5]
        
        return {
            'role': 'staff',
            'leave': leave_balance,
            'recent_requests': [{
                'id': str(lr.id),
                'type': lr.leave_type,
                'start_date': lr.start_date,
                'end_date': lr.end_date,
                'days': float(lr.days_requested),
                'status': lr.status,
            } for lr in recent_leaves],
            'activities': {
                'in_progress': [{
                    'id': str(act.id),
                    'name': act.name,
                    'project': act.project.name,
                    'deadline': act.deadline,
                    'progress': DashboardStatsService._calculate_progress(act),
                } for act in activities_in_progress],
                'due_soon': [{
                    'id': str(act.id),
                    'name': act.name,
                    'project': act.project.name,
                    'deadline': act.deadline,
                    'days_remaining': (act.deadline - today).days if act.deadline else None,
                } for act in activities_due_soon],
                'overdue': [{
                    'id': str(act.id),
                    'name': act.name,
                    'project': act.project.name,
                    'deadline': act.deadline,
                    'days_overdue': (today - act.deadline).days,
                } for act in activities_overdue]
            },
            'milestones': {
                'upcoming': [{
                    'id': str(m.id),
                    'title': m.title,
                    'activity': m.activity.name,
                    'project': m.activity.project.name,
                    'due_date': m.due_date,
                    'priority': m.priority,
                } for m in my_milestones]
            }
        }
    
    
    @staticmethod
    def _get_my_role(user, activity):
        """Determine user's role in activity"""
        if activity.responsible == user:
            return 'Responsible'
        elif activity.accountable == user:
            return 'Accountable'
        elif activity.consulted.filter(id=user.id).exists():
            return 'Consulted'
        elif activity.informed.filter(id=user.id).exists():
            return 'Informed'
        return 'Unknown'
    
    @staticmethod
    def _calculate_progress(activity):
        """Calculate activity progress based on milestones"""
        milestones = activity.milestones.all()
        if not milestones:
            return None
        
        total = milestones.count()
        completed = milestones.filter(is_completed=True).count()
        
        return round((completed / total) * 100) if total > 0 else 0
    


    @staticmethod
    def _get_leave_summary(user):
        """Get leave balance summary for user"""
        contract = EmployeeContract.objects.filter(
            user=user,
            is_current=True,
            is_expired=False
        ).first()
        
        if not contract:
            return {
                'has_contract': False,
                'balances': {}
            }

        leave_types = ['ANNUAL', 'SICK', 'MATERNITY', 'PATERNITY', 'COMPASSIONATE', 'STUDY']
        balances = {}

        for leave_type in leave_types:
            result = get_leave_balance(user, contract, leave_type)

            if isinstance(result, dict):
                # Convert Decimals to float for JSON serialization
                balances[leave_type.lower()] = {k: float(v) if isinstance(v, Decimal) else v for k, v in result.items()}
            else:
                # If it's a single numeric value, just pass as float
                balances[leave_type.lower()] = float(result) if result is not None else None

        return {
            'has_contract': True,
            'contract_id': str(contract.id),
            'balances': balances
        }








