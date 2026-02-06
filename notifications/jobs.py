"""
Cron job functions for scheduled notifications.

These functions are called at specified intervals.


Sample configs:
    JOBS = [
        ('0 9 * * *', 'notifications.jobs.notify_pending_leaves'),
        ('0 8 * * *', 'notifications.jobs.notify_activities_due'),
        ('0 10 * * *', 'notifications.jobs.notify_overdue_activities'),
        ('0 9 * * *', 'notifications.jobs.notify_pending_reviews'),
        ('0 8 * * 1', 'notifications.jobs.notify_expiring_contracts'),
        ('0 * * * *', 'notifications.jobs.send_pending_notifications'),
    ]
"""

from .service import NotificationService


def notify_pending_leaves():
    """
    Cron: Notify supervisors of pending leave approvals.
    Schedule: Daily at 9:00 AM
    """
    result = NotificationService.notify_pending_leave_approvals()
    print(f"Created {result['created']} leave approval notifications")
    return result


def notify_activities_due():
    """
    Cron: Notify about activities due soon (based on user preferences).
    Schedule: Daily at 8:00 AM
    """
    result = NotificationService.notify_activity_due_soon()
    print(f"Created {result['created']} activity due notifications")
    return result


def notify_overdue_activities():
    """
    Cron: Notify about overdue activities.
    Schedule: Daily at 10:00 AM
    """
    result = NotificationService.notify_overdue_activities()
    print(f"Created {result['created']} overdue activity notifications")
    return result


def notify_pending_reviews():
    """
    Cron: Notify about pending reviews.

    """
    result = NotificationService.notify_pending_reviews()
    print(f"Created {result['created']} review notifications")
    return result


def notify_expiring_contracts():
    """
    Cron: Notify about expiring contracts (based on user preferences).
    Schedule: Weekly on Monday at 8:00 AM
    """
    result = NotificationService.notify_expiring_contracts()
    print(f"Created {result['created']} contract expiration notifications")
    return result


def send_pending_notifications():
    """
    Cron: Send all pending notifications via email.
    Schedule: Every hour
    """
    result = NotificationService.send_pending_notifications()
    print(f"Sent {result['sent']} notifications, {result['failed']} failed, {result['skipped']} skipped")
    return result