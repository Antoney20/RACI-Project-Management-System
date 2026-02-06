from projects.models import SupervisorReview


def create_or_reset_supervisor_review(activity):
    supervisor = activity.accountable

    review, created = SupervisorReview.objects.get_or_create(
        activity=activity,
        review_level='supervisor',
        defaults={
            'reviewer': supervisor,
            'status': 'not_started',
        }
    )

    if not created and review.is_complete:
        review.status = 'not_started'
        review.started_at = None
        review.completed_at = None
        review.is_complete = False
        review.is_supervisor_approved = None
        review.supervisor_approved_at = None
        review.move_to_admin = False
        review.is_admin_approved = None
        review.admin_approved_at = None
        review.notes = ''
        review.save()

    return review