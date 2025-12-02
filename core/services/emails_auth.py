import logging
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone
from smtplib import SMTPException

logger = logging.getLogger(__name__)


def send_user_acknowledgment_email(user):
    """Send registration acknowledgment email to user"""
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@cema-africa.uonbi.ac.ke')
    reply_to = getattr(settings, 'REPLY_TO_EMAIL', from_email)
    recipient = user.email
    subject = 'Welcome to RACI - Registration Received'

    context = {
        'user_name': user.first_name or user.username,
        'email': user.email,
        'current_year': timezone.now().year,
    }

    try:
        html_content = render_to_string('emails/registration_acknowledgment.html', context)

        email = EmailMultiAlternatives(
            subject=subject,
            body='',
            from_email=from_email,
            to=[recipient],
            reply_to=[reply_to] if reply_to != from_email else None
        )
        email.attach_alternative(html_content, "text/html")
        email.send(fail_silently=False)

        logger.info(f"Registration acknowledgment email sent to: {recipient}")
        return True

    except (SMTPException, Exception) as exc:
        logger.error(f"Failed to send registration acknowledgment email to {recipient}: {exc}")
        return False


def send_secretariate_notification_email(user):
    """Send notification to secretariate about pending user registration"""
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@cema-africa.uonbi.ac.ke')
    secretariate_email = getattr(settings, 'SECRETARIATE_EMAIL', 'secretariate@cema-africa.uonbi.ac.ke')
    subject = f'New User Registration - {user.full_name} Pending Approval'

    frontend_url = getattr(settings, 'FRONTEND_URL', 'https://cema-africa.uonbi.ac.ke')
    verification_link = f"{frontend_url}/admin/verify/{user.id}/{user.verification_token}/"

    context = {
        'user': user,
        'verification_link': verification_link,
        'current_year': timezone.now().year,
    }

    try:
        html_content = render_to_string('emails/secretariate_notification.html', context)

        email = EmailMultiAlternatives(
            subject=subject,
            body='',
            from_email=from_email,
            to=[secretariate_email]
        )
        email.attach_alternative(html_content, "text/html")
        email.send(fail_silently=False)

        logger.info(f"Secretariate notification email sent for user: {user.email}")
        return True

    except (SMTPException, Exception) as exc:
        logger.error(f"Failed to send secretariate notification email: {exc}")
        return False


def send_verification_success_email(user):
    """Send email confirming account activation"""
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@cema-africa.uonbi.ac.ke')
    reply_to = getattr(settings, 'REPLY_TO_EMAIL', from_email)
    recipient = user.email
    subject = 'Account Activated - Welcome to RACI'

    context = {
        'user_name': user.first_name or user.username,
        'login_url': getattr(settings, 'FRONTEND_URL', 'https://cema-africa.uonbi.ac.ke') + '/auth/login',
        'current_year': timezone.now().year,
    }

    try:
        html_content = render_to_string('emails/verification_success.html', context)

        email = EmailMultiAlternatives(
            subject=subject,
            body='',
            from_email=from_email,
            to=[recipient],
            reply_to=[reply_to] if reply_to != from_email else None
        )
        email.attach_alternative(html_content, "text/html")
        email.send(fail_silently=False)

        logger.info(f"Account activation email sent to: {recipient}")
        return True

    except (SMTPException, Exception) as exc:
        logger.error(f"Failed to send account activation email to {recipient}: {exc}")
        return False


def send_rejection_email(user, rejection_reason=''):
    """Send email notifying user of registration rejection"""
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@cema-africa.uonbi.ac.ke')
    reply_to = getattr(settings, 'REPLY_TO_EMAIL', from_email)
    recipient = user.email
    subject = 'Registration Status - Action Required'

    contact_email = getattr(settings, 'SUPPORT_EMAIL', 'support@cema-africa.uonbi.ac.ke')

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
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@cema-africa.uonbi.ac.ke')
    reply_to = getattr(settings, 'REPLY_TO_EMAIL', from_email)
    recipient = user.email
    subject = 'Password Reset Request - RACI'

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
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@cema-africa.uonbi.ac.ke')
    reply_to = getattr(settings, 'REPLY_TO_EMAIL', from_email)
    recipient = user.email
    subject = 'Password Changed Successfully - RACI'

    contact_email = getattr(settings, 'SUPPORT_EMAIL', 'support@cema-africa.uonbi.ac.ke')

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

