import logging
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone
from smtplib import SMTPException

from accounts.models import EmailLog

logger = logging.getLogger(__name__)


def _send_email(subject, template, context, recipient, category="system"):
    """
    Send an email and ALWAYS log it.
    If sending fails, log failure and continue gracefully.
    """
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@cema.africa')
    reply_to = getattr(settings, 'REPLY_TO_EMAIL', from_email)
    html_content = render_to_string(template, context)

    # Create initial email log
    email_log = EmailLog.objects.create(
        subject=subject,
        message=html_content,
        sender=from_email,
        recipient=recipient,
        category=category,
        status="initial",
    )

    try:
        logger.info(f"Preparing email [{subject}] → {recipient}")
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
        logger.info(f"Email sent successfully [{subject}] → {recipient}")
        return True

    except (SMTPException, Exception) as exc:
        email_log.mark_failed(exc)
        logger.error(
            f"Email failed [{subject}] → {recipient}: {exc}",
            exc_info=True
        )
        return False
    

def send_leave_approved_email(leave):
    subject = "Leave Request Approved - RACI"

    context = {
        "user_name": leave.user.first_name or leave.user.username,
        "leave_type": leave.leave_type,
        "start_date": leave.start_date,
        "end_date": leave.end_date,
        "days": leave.days_requested,
        "approved_by": leave.approved_by.get_full_name() if leave.approved_by else "Supervisor",
        "current_year": timezone.now().year,
        
    }

    return _send_email(
        subject,
        "emails/leave/approved.html",
        context,
        leave.user.email,
        category="leave_approved",
    )



def send_leave_rejected_email(leave):
    subject = "Leave Request Rejected ❌"

    context = {
        "user_name": leave.user.first_name or leave.user.username,
        "leave_type": leave.leave_type,
        "start_date": leave.start_date,
        "end_date": leave.end_date,
        "days": leave.days_requested,
        "rejection_reason": leave.rejection_reason,
        "current_year": timezone.now().year,
    }

    return _send_email(
        subject,
        "emails/leave/rejected.html",
        context,
        leave.user.email,
        category="leave_rejected",
    )
    
def send_leave_cancelled_email(leave):
    subject = "Leave Request Cancelled"

    context = {
        "user_name": leave.user.first_name or leave.user.username,
        "leave_type": leave.leave_type,
        "start_date": leave.start_date,
        "end_date": leave.end_date,
        "days": leave.days_requested,
        "current_year": timezone.now().year,
    }

    return _send_email(
        subject,
        "emails/leave/cancelled.html",
        context,
        leave.user.email,
        category="leave_cancelled",
    )


def send_leave_failed_email(user, reason):
    subject = "Leave Request Not Submitted"

    context = {
        "user_name": user.first_name or user.username,
        "reason": reason,
        "current_year": timezone.now().year,
    }

    return _send_email(
        subject,
        "emails/leave/failed.html",
        context,
        user.email,
        category="leave_failed",
    )


def notify_supervisor_leave_request(leave):
    if not leave.supervisor or not leave.supervisor.email:
        return False
    subject = "New Leave Request Submitted"

    context = {
        "supervisor_name": leave.supervisor.first_name or leave.supervisor.username,
        "employee_name": leave.user.get_full_name() or leave.user.username,
        "leave_type": leave.leave_type,
        "start_date": leave.start_date,
        "end_date": leave.end_date,
        "days": leave.days_requested,
        "current_year": timezone.now().year,
    }

    return _send_email(
        subject,
        "emails/leave/supervisor_notify.html",
        context,
        leave.supervisor.email,
        category="notify_supervisor",
    )

