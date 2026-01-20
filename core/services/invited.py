import logging
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone
from smtplib import SMTPException

from accounts.models import EmailLog

logger = logging.getLogger(__name__)


def send_invite_email(invite_user, invite_link, invited_by=None):
    """
    Send email invitation to a new user and log it
    """
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@cema.africa')
    reply_to = getattr(settings, 'REPLY_TO_EMAIL', from_email)

    recipient = invite_user.email
    subject = 'RACI - You are invited to join'
    support_email = getattr(settings, 'SUPPORT_EMAIL', 'raci@cema.africa')

    context = {
        'user_name': invite_user.first_name or invite_user.email,
        'invite_link': invite_link,
        'role': invite_user.role,
        'invited_by': invited_by.get_full_name() if invited_by else None,
        'expires_at': invite_user.invite_expires_at,
        'support_email': support_email,
        'current_year': timezone.now().year,
    }

    html_content = render_to_string('invite/invited.html', context)

    email_log = EmailLog.objects.create(
        subject=subject,
        message=html_content,
        sender=from_email,
        recipient=recipient,
        category='invite',
        status='initial',
    )

    try:
        logger.info(f"Preparing invite email for: {recipient}")
        email_log.mark_sending()

        email = EmailMultiAlternatives(
            subject=subject,
            body='',  # HTML-only
            from_email=from_email,
            to=[recipient],
            reply_to=[reply_to] if reply_to != from_email else None
        )
        email.attach_alternative(html_content, "text/html")
        email.send(fail_silently=False)

        email_log.mark_sent()
        logger.info(f"Invite email sent successfully to: {recipient}")
        return True

    except (SMTPException, Exception) as exc:
        email_log.mark_failed(exc)
        logger.error(
            f"Failed to send invite email to {recipient} - Error: {exc}",
            exc_info=True
        )
        return False


def send_invite_success_email(user):
    """
    Send confirmation email after successful invite acceptance and log it
    """
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@cema.africa')
    reply_to = getattr(settings, 'REPLY_TO_EMAIL', from_email)

    recipient = user.email
    subject = 'Welcome to RACI by CEMA 🎉'
    support_email = getattr(settings, 'SUPPORT_EMAIL', 'raci@cema.africa')

    context = {
        'user_name': user.first_name or user.username or user.email,
        'support_email': support_email,
        'current_year': timezone.now().year,
    }

    html_content = render_to_string('invite/success.html', context)

    email_log = EmailLog.objects.create(
        subject=subject,
        message=html_content,
        sender=from_email,
        recipient=recipient,
        category='invite_success',
        status='initial',
    )

    try:
        logger.info(f"Preparing invite success email for: {recipient}")
        email_log.mark_sending()

        email = EmailMultiAlternatives(
            subject=subject,
            body='',
            from_email=from_email,
            to=[recipient],
            reply_to=[reply_to] if reply_to != from_email else None
        )
        email.attach_alternative(html_content, "text/html")
        email.send(fail_silently=False)

        email_log.mark_sent()
        logger.info(f"Invite success email sent to: {recipient}")
        return True

    except (SMTPException, Exception) as exc:
        email_log.mark_failed(exc)
        logger.error(
            f"Failed to send invite success email to {recipient} - Error: {exc}",
            exc_info=True
        )
        return False
