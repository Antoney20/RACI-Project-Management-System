import logging
from django.conf import settings
from django.utils import timezone

from core.services.leave_emails import _send_email


def send_accountable_alert_email(activity, supervisor):
    subject = "Supervisor Review Required - RACI"

    activity_link = f"{settings.FRONTEND_URL}/a/u/dash/projects/activities/{activity.id}"

    context = {
        "user_name": supervisor.first_name or supervisor.username,
        "activity_name": activity.name,
        "activity_link": activity_link,
        "support_email": getattr(settings, "SUPPORT_EMAIL", "raci@cema.africa"),
        "current_year": timezone.now().year,
    }

    return _send_email(
        subject,
        "emails/activities/accountable_alert.html",
        context,
        supervisor.email,
        category="alert-accountable",
    )
    
    
def send_supervisor_review_alert_email(activity, supervisor):
    subject = "Activity Escalated for Supervisor Review - RACI"

    activity_link = f"{settings.FRONTEND_URL}/a/u/dash/projects/activities/{activity.id}"

    context = {
        "user_name": supervisor.first_name or supervisor.username,
        "activity_name": activity.name,
        "activity_link": activity_link,
        "support_email": getattr(settings, "SUPPORT_EMAIL", "raci@cema.africa"),
        "current_year": timezone.now().year,
    }

    return _send_email(
        subject,
        "emails/activities/supervisor_alert.html",
        context,
        supervisor.email,
        category="alert-supervisor",
    )


def send_admin_review_alert_email(activity, admin_user):
    subject = "Activity Awaiting Admin Review - RACI"

    admin_desk_link = f"{settings.FRONTEND_URL}/a/u/dash/admin/reviews"

    context = {
        "user_name": admin_user.first_name or admin_user.username,
        "activity_name": activity.name,
        "admin_desk_link": admin_desk_link,
        "support_email": getattr(settings, "SUPPORT_EMAIL", "raci@cema.africa"),
        "current_year": timezone.now().year,
    }

    return _send_email(
        subject,
        "emails/activities/admin_alert.html",
        context,
        admin_user.email,
        category="alert-admin",
    )
