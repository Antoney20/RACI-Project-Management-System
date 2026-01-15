import logging
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone
from smtplib import SMTPException

logger = logging.getLogger(__name__)


def send_invite_email(invite_user, invite_link, invited_by=None):
    """
    Send email invitation to a new user
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

    try:
        html_content = render_to_string('invite/invited.html', context)

        email = EmailMultiAlternatives(
            subject=subject,
            body='',
            from_email=from_email,
            to=[recipient],
            reply_to=[reply_to] if reply_to != from_email else None
        )
        email.attach_alternative(html_content, "text/html")
        email.send(fail_silently=False)

        logger.info(f"Invite email sent to: {recipient}")
        return True

    except (SMTPException, Exception) as exc:
        logger.error(f"Failed to send invite email to {recipient}: {exc}")
        return False
    
    
def send_invite_success_email(user):
    """
    Send confirmation email after successful invite acceptance
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

    try:
        html_content = render_to_string(
            'invite/success.html',
            context
        )

        email = EmailMultiAlternatives(
            subject=subject,
            body='',
            from_email=from_email,
            to=[recipient],
            reply_to=[reply_to] if reply_to != from_email else None
        )
        email.attach_alternative(html_content, "text/html")
        email.send(fail_silently=False)

        logger.info(f"Invite success email sent to: {recipient}")
        return True

    except (SMTPException, Exception) as exc:
        logger.error(f"Failed to send invite success email to {recipient}: {exc}")
        return False

