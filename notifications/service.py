from datetime import timedelta
from django.utils import timezone
from django.db.models import Q, Count, Prefetch
from django.core.mail import send_mail
from django.conf import settings


from employee.models import LeaveRequest, EmployeeContract, EmployeeSupervisor
from projects.models import Activity, Notification, Project, SupervisorReview


class NotificationService:
    """Service for creating and managing notifications"""
    
    MAX_RETRIES = 5
    
    @staticmethod
    def create_notification(recipient, notification_type, title, message, related_id=None, action_url=None):
        """Create a single notification"""
        return Notification.objects.create(
            recipient=recipient,
            notification_type=notification_type,
            title=title,
            message=message,
            related_id=related_id,
            action_url=action_url
        )
    
    @staticmethod
    def send_pending_notifications():
        """Send all pending notifications with retry logic"""
        notifications = Notification.objects.filter(
            is_sent=False,
            retry_count__lt=NotificationService.MAX_RETRIES
        )
        
        results = {'sent': 0, 'failed': 0}
        
        for notification in notifications:
            try:
                # Send email
                send_mail(
                    subject=notification.title,
                    message=notification.message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[notification.recipient.email],
                    fail_silently=False,
                )
                notification.mark_sent()
                results['sent'] += 1
            except Exception as e:
                notification.retry_count += 1
                notification.save(update_fields=['retry_count'])
                results['failed'] += 1
        
        return results
    

    @staticmethod
    def notify_pending_leave_approvals():
        """Notify supervisors of pending leave requests"""
        pending_leaves = LeaveRequest.objects.filter(
            status='pending'
        ).select_related('user', 'contract').prefetch_related('supervisors')
        
        notifications_created = 0
        
        for leave in pending_leaves:
            supervisors = leave.supervisors.all()
            if not supervisors and leave.supervisor:
                supervisors = [leave.supervisor]
            
            for supervisor in supervisors:
                # Check if notification already exists
                exists = Notification.objects.filter(
                    recipient=supervisor,
                    notification_type='leave_pending',
                    related_id=leave.id,
                    created_at__gte=timezone.now() - timedelta(days=1)
                ).exists()
                
                if not exists:
                    NotificationService.create_notification(
                        recipient=supervisor,
                        notification_type='leave_pending',
                        title=f'Leave approval needed: {leave.user.get_full_name()}',
                        message=f'{leave.user.get_full_name()} has requested {leave.leave_type} leave from {leave.start_date} to {leave.end_date} ({leave.days_requested} days)',
                        related_id=leave.id,
                        action_url=f'/a/u/dash'
                    )
                    notifications_created += 1
        
        return {'created': notifications_created}
    
    @staticmethod
    def notify_leave_decision(leave_request, approved=True, approved_by=None):
        """Notify employee of leave approval/rejection"""
        notification_type = 'leave_approved' if approved else 'leave_rejected'
        title = f'Leave request {"approved" if approved else "rejected"}'
        message = f'Your {leave_request.leave_type} leave request for {leave_request.start_date} to {leave_request.end_date} has been {"approved" if approved else "rejected"}'
        
        if not approved and leave_request.rejection_reason:
            message += f'. Reason: {leave_request.rejection_reason}'
        
        return NotificationService.create_notification(
            recipient=leave_request.user,
            notification_type=notification_type,
            title=title,
            message=message,
            related_id=leave_request.id,
            action_url=f'/a/u/dash'
        )
    
    @staticmethod
    def notify_expiring_contracts():
        """Notify about contracts expiring in next 30 days"""
        thirty_days_from_now = timezone.now().date() + timedelta(days=30)
        
        expiring_contracts = EmployeeContract.objects.filter(
            is_current=True,
            is_expired=False,
            end_date__lte=thirty_days_from_now,
            end_date__gte=timezone.now().date()
        ).select_related('user')
        
        notifications_created = 0
        
        for contract in expiring_contracts:
            # Notify employee
            days_remaining = (contract.end_date - timezone.now().date()).days
            
            # Check if notification already sent recently
            exists = Notification.objects.filter(
                recipient=contract.user,
                notification_type='contract_expiring',
                related_id=contract.id,
                created_at__gte=timezone.now() - timedelta(days=7)
            ).exists()
            
            if not exists:
                NotificationService.create_notification(
                    recipient=contract.user,
                    notification_type='contract_expiring',
                    title='Contract expiring soon',
                    message=f'Your contract is expiring in {days_remaining} days (on {contract.end_date})',
                    related_id=contract.id,
                    action_url=f'/a/u/dash/hr/employees/contracts'
                )
                notifications_created += 1
                
                # Also notify supervisors
                supervisors = EmployeeSupervisor.objects.filter(
                    employee=contract.user,
                    is_active=True
                ).select_related('supervisor')
                
                for emp_sup in supervisors:
                    NotificationService.create_notification(
                        recipient=emp_sup.supervisor,
                        notification_type='contract_expiring',
                        title=f'Contract expiring: {contract.user.get_full_name()}',
                        message=f'{contract.user.get_full_name()}\'s contract expires in {days_remaining} days (on {contract.end_date})',
                        related_id=contract.id,
                        action_url=f'/a/u/dash/hr/employees/contracts'
                    )
                    notifications_created += 1
        
        return {'created': notifications_created}
    

    @staticmethod
    def notify_activity_due_soon():
        """Notify about activities due in next 3 days"""
        three_days_from_now = timezone.now() + timedelta(days=3)
        
        due_activities = Activity.objects.filter(
            status__in=['not_started', 'in_progress'],
            deadline__lte=three_days_from_now,
            deadline__gte=timezone.now()
        ).select_related('responsible', 'project')
        
        notifications_created = 0
        
        for activity in due_activities:
            if activity.responsible:
                days_remaining = (activity.deadline - timezone.now()).days
                
                exists = Notification.objects.filter(
                    recipient=activity.responsible,
                    notification_type='activity_due',
                    related_id=activity.id,
                    created_at__gte=timezone.now() - timedelta(days=1)
                ).exists()
                
                if not exists:
                    NotificationService.create_notification(
                        recipient=activity.responsible,
                        notification_type='activity_due',
                        title=f'Activity due soon: {activity.name}',
                        message=f'Activity "{activity.name}" in project "{activity.project.name}" is due in {days_remaining} days',
                        related_id=activity.id,
                        action_url=f'/a/u/dash/projects/activities'
                    )
                    notifications_created += 1
        
        return {'created': notifications_created}
    
    @staticmethod
    def notify_overdue_activities():
        """Notify about overdue activities"""
        overdue_activities = Activity.objects.filter(
            status__in=['not_started', 'in_progress'],
            deadline__lt=timezone.now()
        ).select_related('responsible', 'accountable', 'project')
        
        notifications_created = 0
        
        for activity in overdue_activities:
            # Notify responsible person
            if activity.responsible:
                exists = Notification.objects.filter(
                    recipient=activity.responsible,
                    notification_type='activity_overdue',
                    related_id=activity.id,
                    created_at__gte=timezone.now() - timedelta(days=1)
                ).exists()
                
                if not exists:
                    days_overdue = (timezone.now() - activity.deadline).days
                    NotificationService.create_notification(
                        recipient=activity.responsible,
                        notification_type='activity_overdue',
                        title=f'Overdue activity: {activity.name}',
                        message=f'Activity "{activity.name}" is overdue by {days_overdue} days (was due: {activity.deadline.date()})',
                        related_id=activity.id,
                        action_url=f'/a/u/dash/projects/activities'
                    )
                    notifications_created += 1
            
            # Notify accountable person (if different)
            if activity.accountable and activity.accountable != activity.responsible:
                exists = Notification.objects.filter(
                    recipient=activity.accountable,
                    notification_type='activity_overdue',
                    related_id=activity.id,
                    created_at__gte=timezone.now() - timedelta(days=1)
                ).exists()
                
                if not exists:
                    days_overdue = (timezone.now() - activity.deadline).days
                    NotificationService.create_notification(
                        recipient=activity.accountable,
                        notification_type='activity_overdue',
                        title=f'Overdue activity (you\'re accountable): {activity.name}',
                        message=f'Activity "{activity.name}" assigned to {activity.responsible.get_full_name() if activity.responsible else "unassigned"} is overdue by {days_overdue} days',
                        related_id=activity.id,
                        action_url=f'/a/u/dash/projects/activities'
                    )
                    notifications_created += 1
        
        return {'created': notifications_created}
    

    @staticmethod
    def notify_pending_reviews():
        """Notify reviewers of activities needing review"""
        pending_reviews = SupervisorReview.objects.filter(
            status__in=['not_started', 'started']
        ).select_related('activity', 'reviewer', 'activity__project')
        
        notifications_created = 0
        
        for review in pending_reviews:
            if review.reviewer:
                exists = Notification.objects.filter(
                    recipient=review.reviewer,
                    notification_type='review_needed',
                    related_id=review.id,
                    created_at__gte=timezone.now() - timedelta(days=2)
                ).exists()
                
                if not exists:
                    NotificationService.create_notification(
                        recipient=review.reviewer,
                        notification_type='review_needed',
                        title=f'Review needed: {review.activity.name}',
                        message=f'Activity "{review.activity.name}" in "{review.activity.project.name}" needs your review (Level: {review.review_level})',
                        related_id=review.id,
                        action_url=f'/a/u/dash/projects/reviews'
                    )
                    notifications_created += 1
        
        return {'created': notifications_created}

    @staticmethod
    def generate_project_status_update(user):
        """Generate project status update for a user"""
        # Get projects user is involved in
        involved_projects = Project.objects.filter(
            Q(activities__responsible=user) | 
            Q(activities__accountable=user) |
            Q(created_by=user)
        ).distinct().prefetch_related(
            Prefetch(
                'activities',
                queryset=Activity.objects.filter(
                    Q(responsible=user) | Q(accountable=user)
                ).select_related('responsible')
            )
        )
        
        summary = []
        for project in involved_projects:
            activity_summary = {
                'not_started': 0,
                'in_progress': 0,
                'completed': 0,
                'overdue': 0
            }
            
            for activity in project.activities.all():
                activity_summary[activity.status] += 1
                if activity.deadline and activity.deadline < timezone.now() and activity.status != 'completed':
                    activity_summary['overdue'] += 1
            
            summary.append({
                'project': project.name,
                'activities': activity_summary
            })
        
        return summary