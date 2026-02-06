"""
Notification Service

Features:
- Template-based email rendering
- User preference checking
- Deduplication to prevent spam
- Comprehensive logging
- Query optimization for scale
"""

import logging
from datetime import timedelta
from django.utils import timezone
from django.db.models import Q, F
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from smtplib import SMTPException

from accounts.models import EmailLog, NotificationPreference
from employee.models import LeaveRequest, EmployeeContract, EmployeeSupervisor
from projects.models import Activity, Notification, SupervisorReview

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for creating and managing notifications with email support"""
    
    MAX_RETRIES = 5
    
    ALERT_LEVELS = [
        {"days": 60, "type_suffix": "60", "label": "2 months"},
        {"days": 30, "type_suffix": "30", "label": "1 month"},
        {"days": 14, "type_suffix": "14", "label": "2 weeks"},
        {"days":  7, "type_suffix":  "7", "label": "1 week"},
    ]


    # Template mapping for email notifications
    EMAIL_TEMPLATES = {
        'leave_pending': 'notifications/emails/leave_pending.html',
        'activity_assigned': 'notifications/emails/activity_assigned.html',
        'activity_due': 'notifications/emails/activity_due.html',
        'activity_overdue': 'notifications/emails/activity_overdue.html',
        'review_needed': 'notifications/emails/review_needed.html',
        'contract_expiring': 'notifications/emails/contract_expiring.html',
    }
    
    @staticmethod
    def _send_email(subject, template, context, recipient, category="system"):
        """
        Send an email using template and log the attempt.
        
        Args:
            subject: Email subject line
            template: Path to email template
            context: Context dict for template rendering
            recipient: Recipient email address
            category: Email category for logging
            
        Returns:
            bool: True if email sent successfully
        """
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@raci.com')
        reply_to = getattr(settings, 'REPLY_TO_EMAIL', from_email)
        
        try:
            html_content = render_to_string(template, context)
        except Exception as e:
            logger.error(f"Template rendering failed for {template}: {e}")
            return False
        
        # Create email log
        email_log = EmailLog.objects.create(
            subject=subject,
            message=html_content[:5000], 
            sender=from_email,
            recipient=recipient,
            category=category,
            status='initial',
        )
        
        try:
            logger.info(f"Sending email: [{subject}] → {recipient}")
            email_log.mark_sending()
            
            email = EmailMultiAlternatives(
                subject=subject,
                body='',  # HTML only
                from_email=from_email,
                to=[recipient],
                reply_to=[reply_to] if reply_to != from_email else None
            )
            email.attach_alternative(html_content, "text/html")
            email.send(fail_silently=False)
            
            email_log.mark_sent()
            logger.info(f"Email sent successfully: [{subject}] → {recipient}")
            return True
            
        except (SMTPException, Exception) as exc:
            email_log.mark_failed(exc)
            logger.error(f"Email failed: [{subject}] → {recipient}: {exc}", exc_info=True)
            return False
    
    @staticmethod
    def _get_user_preferences(user):
        """
        Get user notification preferences, create defaults if missing.
        
        Args:
            user: User object
            
        Returns:
            NotificationPreference object
        """

        
        prefs, created = NotificationPreference.objects.get_or_create(user=user)
        return prefs
    
    @staticmethod
    def create_notification(recipient, notification_type, title, message, 
                          related_id=None, action_url=None, email_context=None):
        """
        Create notification and optionally send email based on user preferences.
        
        Args:
            recipient: User to receive notification
            notification_type: Type of notification
            title: Notification title
            message: Notification message
            related_id: UUID of related object
            action_url: URL for action button
            email_context: Additional context for email template
            
        Returns:
            Notification object
        """
        notification = Notification.objects.create(
            recipient=recipient,
            notification_type=notification_type,
            title=title,
            message=message,
            related_id=related_id,
            action_url=action_url
        )
        
        # Check if user wants email for this type
        prefs = NotificationService._get_user_preferences(recipient)
        
        if prefs.should_send_email(notification_type):
            template = NotificationService.EMAIL_TEMPLATES.get(notification_type)
            
            if template:
                # Prepare email context
                context = {
                    'user_name': recipient.first_name or recipient.username,
                    'title': title,
                    'message': message,
                    'action_url': action_url or '/a/u/dash',
                    'current_year': timezone.now().year,
                    'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@raci.com'),
                }
                
                # Merge additional context
                if email_context:
                    context.update(email_context)
                
                # Send email
                category = notification_type.split('_')[0]
                NotificationService._send_email(
                    subject=title,
                    template=template,
                    context=context,
                    recipient=recipient.email,
                    category=category
                )
        
        return notification
    
    @staticmethod
    def send_pending_notifications():
        """
        Send all pending notifications with retry logic.
        
        Returns:
            dict: Statistics about sent/failed notifications
        """
        notifications = Notification.objects.filter(
            is_sent=False,
            retry_count__lt=NotificationService.MAX_RETRIES
        ).select_related('recipient')
        
        results = {'sent': 0, 'failed': 0, 'skipped': 0}
        
        for notification in notifications:
            # Check if user still wants emails
            prefs = NotificationService._get_user_preferences(notification.recipient)
            
            if not prefs.should_send_email(notification.notification_type):
                notification.mark_sent()  # Mark as sent to avoid retry
                results['skipped'] += 1
                continue
            
            template = NotificationService.EMAIL_TEMPLATES.get(notification.notification_type)
            
            if not template:
                notification.mark_sent()
                results['skipped'] += 1
                continue
            
            # Prepare context
            context = {
                'user_name': notification.recipient.first_name or notification.recipient.username,
                'title': notification.title,
                'message': notification.message,
                'action_url': notification.action_url or '/a/u/dash',
                'current_year': timezone.now().year,
                'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@raci.com'),
            }
            
            # Send email
            category = notification.notification_type.split('_')[0]
            success = NotificationService._send_email(
                subject=notification.title,
                template=template,
                context=context,
                recipient=notification.recipient.email,
                category=category
            )
            
            if success:
                notification.mark_sent()
                results['sent'] += 1
            else:
                notification.retry_count = F('retry_count') + 1
                notification.save(update_fields=['retry_count'])
                results['failed'] += 1
        
        logger.info(f"Notification batch: {results}")
        return results
    
    @staticmethod
    def notify_pending_leave_approvals():
        """
        Notify supervisors of pending leave requests (reminder only).
        Emails are sent when leave is created, this is just a reminder.
        
        Returns:
            dict: Statistics about notifications created
        """
        pending_leaves = LeaveRequest.objects.filter(
            status='pending'
        ).select_related('user', 'contract').prefetch_related('supervisors')
        
        notifications_created = 0
        
        for leave in pending_leaves:
            supervisors = leave.supervisors.all()
            if not supervisors and hasattr(leave, 'supervisor') and leave.supervisor:
                supervisors = [leave.supervisor]
            
            for supervisor in supervisors:
                # Check if notification already sent in last  3 days (prevent spam)
                exists = Notification.objects.filter(
                    recipient=supervisor,
                    notification_type='leave_pending',
                    related_id=leave.id,
                    created_at__gte=timezone.now() - timedelta(days=3)
                ).exists()
                
                if not exists:
                    email_context = {
                        'employee_name': leave.user.get_full_name(),
                        'leave_type': leave.leave_type,
                        'start_date': leave.start_date,
                        'end_date': leave.end_date,
                        'days_requested': leave.days_requested,
                    }
                    
                    NotificationService.create_notification(
                        recipient=supervisor,
                        notification_type='leave_pending',
                        title=f'Leave approval needed: {leave.user.get_full_name()}',
                        message=f'{leave.user.get_full_name()} has requested {leave.leave_type} leave from {leave.start_date} to {leave.end_date} ({leave.days_requested} days)',
                        related_id=leave.id,
                        action_url=f'/a/u/dash/leaves/{leave.id}',
                        email_context=email_context
                    )
                    notifications_created += 1
        
        logger.info(f"Created {notifications_created} leave approval notifications")
        return {'created': notifications_created}
    
    @staticmethod
    def notify_activity_assigned(activity):
        """
        Notify user when assigned to an activity.
        
        Args:
            activity: Activity object
            
        Returns:
            Notification object or None
        """
        if not activity.responsible:
            return None
        
        email_context = {
            'activity_name': activity.name,
            'project_name': activity.project.name,
            'deadline': activity.deadline,
            'assigned_by': getattr(activity, 'created_by', None),
        }
        
        return NotificationService.create_notification(
            recipient=activity.responsible,
            notification_type='activity_assigned',
            title=f'New activity assigned: {activity.name}',
            message=f'You have been assigned to activity "{activity.name}" in project "{activity.project.name}"',
            related_id=activity.id,
            action_url=f'/a/u/dash/projects/activities/',
            email_context=email_context
        )
    
    @staticmethod
    def notify_activity_due_soon():
        """
        Notify about activities due soon based on user preferences.
        
        Returns:
            dict: Statistics about notifications created
        """

        notifications_created = 0
        
        # Get all users with activity notifications enabled
        users_with_prefs = NotificationPreference.objects.filter(
            email_activities=True
        ).select_related('user')
        
        for pref in users_with_prefs:
            # Use user's preferred alert timing
            alert_days = pref.activity_due_alert_days
            future_datetime = timezone.now() + timedelta(days=alert_days)
            
            # Find activities due within user's preferred window
            due_activities = Activity.objects.filter(
                responsible=pref.user,
                status__in=['not_started', 'in_progress'],
                deadline__lte=future_datetime,
                deadline__gte=timezone.now()
            ).select_related('project')
            
            for activity in due_activities:
                exists = Notification.objects.filter(
                    recipient=pref.user,
                    notification_type='activity_due',
                    related_id=activity.id,
                    created_at__gte=timezone.now() - timedelta(days=1)
                ).exists()
                
                if not exists:
                    days_remaining = (activity.deadline - timezone.now()).days
                    
                    email_context = {
                        'activity_name': activity.name,
                        'project_name': activity.project.name,
                        'days_remaining': days_remaining,
                        'deadline': activity.deadline,
                    }
                    
                    NotificationService.create_notification(
                        recipient=activity.responsible,
                        notification_type='activity_due',
                        title=f'Activity due soon: {activity.name}',
                        message=f'Activity "{activity.name}" in project "{activity.project.name}" is due in {days_remaining} days',
                        related_id=activity.id,
                        action_url=f'/a/u/dash/projects/activities/',
                        email_context=email_context
                    )
                    notifications_created += 1
        
        logger.info(f"Created {notifications_created} activity due notifications")
        return {'created': notifications_created}
    
    @staticmethod
    def notify_overdue_activities():
        """
        Notify about overdue activities.
        
        Returns:
            dict: Statistics about notifications created
        """
        overdue_activities = Activity.objects.filter(
            status__in=['not_started', 'in_progress'],
            deadline__lt=timezone.now()
        ).select_related('responsible', 'accountable', 'project')
        
        notifications_created = 0
        
        for activity in overdue_activities:
            days_overdue = (timezone.now() - activity.deadline).days
            
            # Notify responsible person
            if activity.responsible:
                exists = Notification.objects.filter(
                    recipient=activity.responsible,
                    notification_type='activity_overdue',
                    related_id=activity.id,
                    created_at__gte=timezone.now() - timedelta(days=1)
                ).exists()
                
                if not exists:
                    email_context = {
                        'activity_name': activity.name,
                        'project_name': activity.project.name,
                        'days_overdue': days_overdue,
                        'deadline': activity.deadline,
                    }
                    
                    NotificationService.create_notification(
                        recipient=activity.responsible,
                        notification_type='activity_overdue',
                        title=f'Overdue activity: {activity.name}',
                        message=f'Activity "{activity.name}" is overdue by {days_overdue} days (was due: {activity.deadline.date()})',
                        related_id=activity.id,
                        action_url=f'/a/u/dash/projects/activities/',
                        email_context=email_context
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
                    email_context = {
                        'activity_name': activity.name,
                        'project_name': activity.project.name,
                        'days_overdue': days_overdue,
                        'deadline': activity.deadline,
                        'responsible_name': activity.responsible.get_full_name() if activity.responsible else 'Unassigned',
                    }
                    
                    NotificationService.create_notification(
                        recipient=activity.accountable,
                        notification_type='activity_overdue',
                        title=f'Overdue activity (you\'re accountable): {activity.name}',
                        message=f'Activity "{activity.name}" assigned to {activity.responsible.get_full_name() if activity.responsible else "unassigned"} is overdue by {days_overdue} days',
                        related_id=activity.id,
                        action_url=f'/a/u/dash/projects/activities/',
                        email_context=email_context
                    )
                    notifications_created += 1
        
        logger.info(f"Created {notifications_created} overdue activity notifications")
        return {'created': notifications_created}
    

    @staticmethod
    def notify_pending_reviews():
        """
        Notify eligible reviewers of activities submitted for review.

        - Supervisor reviews → supervisor
        - Admin reviews → assigned admin
        - Staff never notified
        - 7-day cooldown per review
        """
        notifications_created = 0

        pending_reviews = SupervisorReview.objects.filter(
            status__in=['not_started', 'started']
        ).select_related(
            'activity',
            'reviewer',
            'activity__project'
        )

        for review in pending_reviews:
            reviewer = review.reviewer

            if not reviewer:
                continue

        
            if reviewer.is_staff:
                continue

            if review.review_level == 'supervisor' and reviewer.role != 'supervisor':
                continue

            if review.review_level == 'admin' and reviewer.role != 'admin':
                continue

            recently_notified = Notification.objects.filter(
                recipient=reviewer,
                notification_type='review_submitted',
                related_id=review.id,
                created_at__gte=timezone.now() - timedelta(days=7)
            ).exists()

            if recently_notified:
                continue

            email_context = {
                'activity_name': review.activity.name,
                'project_name': review.activity.project.name,
                'review_level': review.review_level,
                'submitted_at': review.activity.updated_at,
            }

            NotificationService.create_notification(
                recipient=reviewer,
                notification_type='review_submitted',
                title=f'Submitted for review: {review.activity.name}',
                message=(
                    f'Activity "{review.activity.name}" in '
                    f'"{review.activity.project.name}" has been submitted for '
                    f'{review.review_level} review.'
                ),
                related_id=review.id,
                action_url='/a/u/dash/projects/reviews/',
                email_context=email_context,
            )

            notifications_created += 1

        logger.info(
            "Review notifications created: %s",
            notifications_created
        )

        return {'created': notifications_created}



    @staticmethod
    def notify_expiring_contracts():
        """
        Weekly contract expiry notifications.
        
        Buckets:
            - < 7 days: Critical
            - 8–14 days: Less than 2 weeks
            - 15–30 days: Less than a month
            - 31–60 days: Less than 2 months
        
        Notifications are sent once per bucket per contract.
        Supervisors/HR are notified.
        """
        today = timezone.now().date()
        notifications_created = 0


        ALERT_BUCKETS = [
            {"key": "lt_7_days", "max_days": 7, "label": "Less than 7 days"},
            {"key": "lt_14_days", "max_days": 14, "label": "Less than 2 weeks"},
            {"key": "lt_30_days", "max_days": 30, "label": "Less than a month"},
            {"key": "lt_60_days", "max_days": 60, "label": "Less than 2 months"},
        ]

        # Fetch active contracts that haven't expired
        contracts = EmployeeContract.objects.filter(
            is_current=True,
            is_expired=False,
            end_date__gt=today
        ).select_related('user')

        for contract in contracts:
            days_remaining = (contract.end_date - today).days
            if days_remaining <= 0:
                continue  # Already expired

            # Determine which bucket this contract falls into
            bucket = None
            for level in ALERT_BUCKETS:
                if days_remaining <= level["max_days"]:
                    bucket = level
                    break

            if not bucket:
                continue  # More than 60 days left → ignore

            notification_type = f"contract_expiring_{bucket['key']}"
            employee = contract.user
            employee_name = employee.get_full_name()

            # Prevent duplicate notifications per bucket
            already_sent = Notification.objects.filter(
                recipient=employee,
                notification_type=notification_type,
                related_id=contract.id
            ).exists()
            if already_sent:
                continue

            base_context = {
                "employee_name": employee_name,
                "days_remaining": days_remaining,
                "end_date": contract.end_date,
                "contract_type": getattr(contract, "contract_type", "Employment"),
                "bucket_label": bucket["label"],
            }

            # NotificationService.create_notification(
            #     recipient=employee,
            #     notification_type=notification_type,
            #     title=f"Contract Expiring ({bucket['label']})",
            #     message=(
            #         f"Your contract expires in {days_remaining} days "
            #         f"(on {contract.end_date})."
            #     ),
            #     related_id=contract.id,
            #     action_url="/a/u/dash/",
            #     email_context=base_context
            # )
            # notifications_created += 1

            # Notify Supervisors / HR
            supervisors = EmployeeSupervisor.objects.filter(
                employee=employee,
                is_active=True
            ).select_related('supervisor')

            for emp_sup in supervisors:
                NotificationService.create_notification(
                    recipient=emp_sup.supervisor,
                    notification_type=notification_type,
                    title=f"Contract Expiring ({bucket['label']}) – {employee_name}",
                    message=(
                        f"{employee_name}'s contract expires in {days_remaining} days "
                        f"(on {contract.end_date}). Action required."
                    ),
                    related_id=contract.id,
                    action_url="/a/u/dash/hr/contracts",
                    email_context=base_context
                )
                notifications_created += 1

        logger.info(
            f"Weekly contract expiry job: {notifications_created} notifications created"
        )
        return {"created": notifications_created}





