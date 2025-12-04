from datetime import timedelta
def calculate_business_days(start_date, end_date):
    """
    Calculate business days between two dates (excluding Saturday and Sunday).
    Both start_date and end_date are included in the count.
    """
    if start_date > end_date:
        return 0
    
    business_days = 0
    current_date = start_date
    
    while current_date <= end_date:
        # weekday() returns 0-6 (Monday-Sunday)
        # 5 = Saturday, 6 = Sunday
        if current_date.weekday() < 5:  # Monday to Friday
            business_days += 1
        current_date += timedelta(days=1)
    
    return business_days


def get_business_days_in_range(start_date, end_date):
    """
    Get list of all business days between two dates.
    """
    business_dates = []
    current_date = start_date
    
    while current_date <= end_date:
        if current_date.weekday() < 5:  # Monday to Friday
            business_dates.append(current_date)
        current_date += timedelta(days=1)
    
    return business_dates
