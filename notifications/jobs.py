"""
Cron job functions for scheduled notifications
"""
from .service import NotificationService


def notify_pending_leaves():
    """Cron: Notify supervisors of pending leave approvals"""
    result = NotificationService.notify_pending_leave_approvals()
    print(f"Created {result['created']} leave approval notifications")
    return result


def notify_activities_due():
    """Cron: Notify about activities due soon"""
    result = NotificationService.notify_activity_due_soon()
    print(f"Created {result['created']} activity due notifications")
    return result


def notify_overdue_activities():
    """Cron: Notify about overdue activities"""
    result = NotificationService.notify_overdue_activities()
    print(f"Created {result['created']} overdue activity notifications")
    return result


def notify_pending_reviews():
    """Cron: Notify about pending reviews"""
    result = NotificationService.notify_pending_reviews()
    print(f"Created {result['created']} review notifications")
    return result


def notify_expiring_contracts():
    """Cron: Notify about expiring contracts"""
    result = NotificationService.notify_expiring_contracts()
    print(f"Created {result['created']} contract expiration notifications")
    return result


def send_pending_notifications():
    """Cron: Send all pending notifications"""
    result = NotificationService.send_pending_notifications()
    print(f"Sent {result['sent']} notifications, {result['failed']} failed")
    return result

