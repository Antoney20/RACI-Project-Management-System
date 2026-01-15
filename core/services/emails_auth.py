import logging
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone
from smtplib import SMTPException

logger = logging.getLogger(__name__)


def send_rejection_email(user, rejection_reason=''):
    """Send email notifying user of registration rejection"""
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@cema.africa')
    reply_to = getattr(settings, 'REPLY_TO_EMAIL', from_email)
    recipient = user.email
    subject = 'Registration Status - Action Required'

    contact_email = getattr(settings, 'SUPPORT_EMAIL', 'raci@cema.africa')

    context = {
        'user_name': user.first_name or user.username,
        'rejection_reason': rejection_reason,
        'contact_email': contact_email,
        'current_year': timezone.now().year,
    }

    try:
        html_content = render_to_string('emails/registration_rejection.html', context)

        email = EmailMultiAlternatives(
            subject=subject,
            body='',
            from_email=from_email,
            to=[recipient],
            reply_to=[reply_to] if reply_to != from_email else None
        )
        email.attach_alternative(html_content, "text/html")
        email.send(fail_silently=False)

        logger.info(f"Rejection email sent to: {recipient}")
        return True

    except (SMTPException, Exception) as exc:
        logger.error(f"Failed to send rejection email to {recipient}: {exc}")
        return False


def send_password_reset_email(user, reset_link):
    """Send password reset email with template"""
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@cema.africa')
    reply_to = getattr(settings, 'REPLY_TO_EMAIL', from_email)
    recipient = user.email
    subject = 'Password Reset Request - CEMA'

    context = {
        'user_name': user.first_name or user.username,
        'reset_link': reset_link,
        'current_year': timezone.now().year,
    }

    try:
        html_content = render_to_string('emails/password_reset.html', context)

        email = EmailMultiAlternatives(
            subject=subject,
            body='',
            from_email=from_email,
            to=[recipient],
            reply_to=[reply_to] if reply_to != from_email else None
        )
        email.attach_alternative(html_content, "text/html")
        email.send(fail_silently=False)

        logger.info(f"Password reset email sent to: {recipient}")
        return True

    except (SMTPException, Exception) as exc:
        logger.error(f"Failed to send password reset email to {recipient}: {exc}")
        return False


def send_password_change_confirmation(user):
    """Send confirmation email after password change"""
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@cema.africa')
    reply_to = getattr(settings, 'REPLY_TO_EMAIL', from_email)
    recipient = user.email
    subject = 'Password Changed Successfully - CEMA'

    contact_email = getattr(settings, 'SUPPORT_EMAIL', 'raci@cema.africa')

    context = {
        'user_name': user.first_name or user.username,
        'contact_email': contact_email,
        'current_year': timezone.now().year,
    }

    try:
        html_content = render_to_string('emails/password_change_confirmation.html', context)

        email = EmailMultiAlternatives(
            subject=subject,
            body='',
            from_email=from_email,
            to=[recipient],
            reply_to=[reply_to] if reply_to != from_email else None
        )
        email.attach_alternative(html_content, "text/html")
        email.send(fail_silently=False)

        logger.info(f"Password change confirmation email sent to: {recipient}")
        return True

    except (SMTPException, Exception) as exc:
        logger.error(f"Failed to send password change confirmation email to {recipient}: {exc}")
        return False

