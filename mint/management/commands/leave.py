from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone

from mint.models import LeaveAllocation

User = get_user_model()


class Command(BaseCommand):
    help = "Create leave allocations for all users"

    def handle(self, *args, **options):
        years = [2026, 2027]

        users = User.objects.all()
        created_count = 0
        skipped_count = 0

        for year in years:
            for user in users:
                allocation, created = LeaveAllocation.objects.get_or_create(
                    user=user,
                    year=year,
                    defaults={
                        "annual_leave_days": 0,
                        "annual_used": 0,
                        "annual_left": 0,
                        "sick_leave_days": 0,
                        "sick_used": 0,
                        "other_leave_days": 0,
                        "other_used": 0,
                    }
                )

                if created:
                    created_count += 1
                else:
                    skipped_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"Leave allocation creation completed.\n"
            f"Created: {created_count}\n"
            f"Skipped (already existed): {skipped_count}"
        ))
