from projects.models import ActivityReview, SupervisorReview
from projects.services.alert import send_accountable_alert_email, send_admin_review_alert_email, send_supervisor_review_alert_email
import logging
from django.utils import timezone

logger = logging.getLogger(__name__)
def create_or_reset_accountable_review(activity):
    
    """
    Create or reset an accountable-level review for an activity.
    Sends alert email safely (never breaks flow).
    """

    accountable = activity.accountable

    review, created = ActivityReview.objects.get_or_create(
        activity=activity,
        review_level='accountable',
        defaults={
            'reviewer': accountable,
            'status': 'submitted',  
        }
    )

    if not created and review.is_complete:
        review.status = 'submitted'
        review.decision = None
        review.submitted_at = timezone.now()
        review.decided_at = None
        review.is_complete = False
        review.save()

    try:
        if accountable and accountable.email:
            send_accountable_alert_email(activity, accountable)
    except Exception as e:
        logger.error(
            f"Failed to send accountable alert email for activity {activity.id}: {e}",
            exc_info=True
        )

    return review


def create_supervisor_review(activity, supervisor):
    review, created = ActivityReview.objects.get_or_create(
        activity=activity,
        review_level='supervisor',
        defaults={
            'reviewer': supervisor,
            'status': 'submitted',
            'submitted_at': timezone.now()
        }
    )

    if created:
        try:
            if supervisor.email:
                send_supervisor_review_alert_email(activity, supervisor)
        except Exception:
            logger.exception("Supervisor email failed")

    return review


def create_admin_review(activity, admin_user):
    review, created = ActivityReview.objects.get_or_create(
        activity=activity,
        review_level='admin',
        defaults={
            'reviewer': admin_user,
            'status': 'submitted',
            'submitted_at': timezone.now()
        }
    )

    if created:
        try:
            if admin_user.email:
                send_admin_review_alert_email(activity, admin_user)
        except Exception:
            logger.exception("Admin email failed")

    return review
