import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "raci.settings")
django.setup()

from django.utils import timezone
from projects.models import ActivityReview, SupervisorReview

def migrate_completed_reviews():
    qs = SupervisorReview.objects.filter(
        status="completed"
    ).select_related("activity", "reviewer")

    created = 0
    skipped = 0

    for old in qs:
        if ActivityReview.objects.filter(
            activity=old.activity,
            review_level=old.review_level
        ).exists():
            skipped += 1
            continue

        decision = None
        if old.review_level == "supervisor":
            if old.is_supervisor_approved is True:
                decision = "approved"
            elif old.is_supervisor_approved is False:
                decision = "rejected"

        elif old.review_level == "admin":
            if old.is_admin_approved is True:
                decision = "approved"
            elif old.is_admin_approved is False:
                decision = "rejected"

        ActivityReview.objects.create(
            activity=old.activity,
            reviewer=old.reviewer,
            review_level=old.review_level,
            status="completed",
            decision=decision,
            is_complete=True,
            decided_at=old.completed_at,
            created_at=old.created_at,
            updated_at=timezone.now(),
        )

        created += 1

    print("Migration completed")
    print(f"Created: {created}")
    print(f"Skipped (already existed): {skipped}")


if __name__ == "__main__":
    migrate_completed_reviews()
