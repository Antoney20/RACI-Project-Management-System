from datetime import date
from django.utils import timezone

def get_leave_year_range(ref_date=None):
    """
    Leave year: May 1 → April 30
    Example: May 2025 → April 2026 => leave_year = 2025
    """
    if not ref_date:
        ref_date = timezone.now().date()

    if ref_date.month >= 5:  # May–Dec
        start = date(ref_date.year, 5, 1)
        end = date(ref_date.year + 1, 4, 30)
        leave_year = ref_date.year
    else:  # Jan–Apr
        start = date(ref_date.year - 1, 5, 1)
        end = date(ref_date.year, 4, 30)
        leave_year = ref_date.year - 1

    return start, end, leave_year
