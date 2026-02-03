import logging
from django.utils import timezone
from django.db import transaction

from  projects.models import Activity, SupervisorReview

logger = logging.getLogger(__name__)


def move_completed_activities_to_review():
    """
    Move completed activities into supervisor review if they are not already
    in the review pipeline.

    Runs daily via cron.
    """
    try:
        # Activities that are completed AND have no supervisor reviews yet
        completed_activities = Activity.objects.filter(
            status='completed'
        ).exclude(
            supervisor_reviews__isnull=False
        )

        created_count = 0

        for activity in completed_activities:
            try:
                with transaction.atomic():
                    SupervisorReview.objects.create(
                        activity=activity,
                        review_level='supervisor',
                        status='not_started',
                        reviewer=activity.owner if hasattr(activity, 'owner') else None,
                        created_at=timezone.now()
                    )

                    created_count += 1
                    logger.info(
                        f"Supervisor review created for activity "
                        f"(ID={activity.id})"
                    )

            except Exception as e:
                logger.error(
                    f"Failed to create supervisor review for activity "
                    f"{activity.id}: {str(e)}"
                )
                continue

        logger.info(
            f"move_completed_activities_to_review completed. "
            f"Created {created_count} reviews."
        )

    except Exception as e:
        logger.critical(
            f"Fatal error in move_completed_activities_to_review cron: {str(e)}"
        )


# from projects.services.for_review import move_completed_activities_to_review
