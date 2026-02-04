# from datetime import datetime, date
# from decimal import Decimal
# from django.utils import timezone
# from django.db.models import Sum, Q
# from employee.models import LeaveRequest, Holiday


# def earned_annual_leave(start_date, end_date, is_fte, fte_percentage, annual_allocation):
#     """
#     Calculate earned ANNUAL leave days based on contract duration and FTE status.
#     This function is ONLY for annual leave.
#     """
#     if isinstance(start_date, str):
#         start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
#     if isinstance(end_date, str):
#         end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
#     today = date.today()
#     accrual_end = end_date if end_date and end_date < today else today
    
#     # Calculate calendar months passed
#     years_diff = accrual_end.year - start_date.year
#     months_diff = accrual_end.month - start_date.month
#     calendar_months = years_diff * 12 + months_diff
    
#     # Adjust if we haven't reached the anniversary day yet
#     if accrual_end.day < start_date.day:
#         calendar_months -= 1
    
#     # Months earned includes current month if applicable
#     months_earned = max(0, calendar_months + 1)
    
#     # Calculate total contract months (for full-year reference)
#     contract_months = 12
#     if end_date:
#         end_years = end_date.year - start_date.year
#         end_months = end_date.month - start_date.month
#         total_contract_months = end_years * 12 + end_months
        
#         if end_date.day >= start_date.day:
#             total_contract_months += 1
            
#         contract_months = max(1, total_contract_months)
    
#     # Apply FTE adjustment
#     fractional_basis = Decimal(str(fte_percentage)) / Decimal('100') if is_fte else Decimal('1')
#     effective_allocation = Decimal(str(annual_allocation)) * fractional_basis
    
#     # Prorate
#     days_per_month = effective_allocation / Decimal(str(contract_months))
#     earned_days = Decimal(str(months_earned)) * days_per_month
#     earned_days = min(earned_days, effective_allocation)
    
#     return {
#         'earned_days': round(earned_days, 2),
#         'days_per_month': round(days_per_month, 4),
#         'months_earned': months_earned,
#         'contract_months': contract_months,
#         'fractional_basis': round(fractional_basis, 4),
#         'effective_allocation': round(effective_allocation, 2)
#     }


# def is_gender_eligible_for_leave(user_gender, leave_type):
#     """
#     Check if a user's gender is eligible for a specific leave type.
    
#     Args:
#         user_gender: User's gender (string, case-insensitive)
#         leave_type: Type of leave (MATERNITY, PATERNITY, etc.)
    
#     Returns:
#         tuple: (is_eligible, error_message)
#     """
#     if not user_gender:
#         # If gender is not set, allow all except maternity/paternity
#         if leave_type in ['MATERNITY', 'PATERNITY']:
#             return False, f"Gender information required for {leave_type.lower()} leave"
#         return True, None
    
#     # Normalize gender to lowercase for comparison
#     gender_lower = user_gender.lower().strip()
    
#     # Gender-specific leave type rules
#     gender_rules = {
#         'MATERNITY': ['female', 'woman', 'f'],
#         'PATERNITY': ['male', 'man', 'm']
#     }
    
#     if leave_type in gender_rules:
#         allowed_genders = gender_rules[leave_type]
#         if gender_lower not in allowed_genders:
#             gender_label = "female" if leave_type == 'MATERNITY' else "male"
#             return False, f"{leave_type.capitalize()} leave is only available to {gender_label} employees"
    
#     return True, None


# def get_leave_balance(user, contract, leave_type='ANNUAL'):
#     """
#     Get current leave balance for a user's contract.
    
#     - ANNUAL leave: prorated (earned)
#     - Other types: full allocation (not earned/prorated)
#     - Gender-specific validation for MATERNITY/PATERNITY
#     """
#     # Normalize leave_type to uppercase for consistency
#     leave_type = leave_type.upper()
    
#     if not contract or not contract.is_current or contract.is_expired:
#         return {
#             'available': Decimal('0'),
#             'earned': Decimal('0'),
#             'used': Decimal('0'),
#             'carried_forward': Decimal('0'),
#             'pending': Decimal('0'),
#             'approved': Decimal('0'),
#             'error': 'No active contract found'
#         }
    
#     if not contract.leave_group:
#         return {
#             'available': Decimal('0'),
#             'earned': Decimal('0'),
#             'used': Decimal('0'),
#             'carried_forward': Decimal('0'),
#             'pending': Decimal('0'),
#             'approved': Decimal('0'),
#             'error': 'No leave group assigned'
#         }
    
#     # Check gender eligibility for maternity/paternity leave
#     is_eligible, gender_error = is_gender_eligible_for_leave(user.gender, leave_type)
#     if not is_eligible:
#         return {
#             'available': Decimal('0'),
#             'earned': Decimal('0'),
#             'used': Decimal('0'),
#             'carried_forward': Decimal('0'),
#             'pending': Decimal('0'),
#             'approved': Decimal('0'),
#             'error': gender_error
#         }
    
#     # Get base allocation
#     allocation_map = {
#         'ANNUAL': contract.leave_group.annual_days,
#         'SICK': contract.leave_group.sick_days,
#         'MATERNITY': contract.leave_group.maternity_days,
#         'PATERNITY': contract.leave_group.paternity_days,
#         'COMPASSIONATE': contract.leave_group.compassionate_days,
#         'STUDY': contract.leave_group.study_days,
#     }
    
#     base_allocation = allocation_map.get(leave_type, Decimal('0'))
    
#     # ── ANNUAL LEAVE ──► prorated / earned
#     if leave_type == 'ANNUAL':
#         earned_calc = earned_annual_leave(
#             start_date=contract.start_date,
#             end_date=contract.end_date,
#             is_fte=contract.is_fte,
#             fte_percentage=float(contract.fte_percentage or 100),
#             annual_allocation=float(base_allocation)
#         )
#         earned_days = Decimal(str(earned_calc['earned_days']))
#         total_allocation = Decimal(str(earned_calc['effective_allocation']))
    
#     # ── OTHER LEAVE TYPES ──► full allocation, no proration
#     else:
#         earned_days = Decimal('0')              # not applicable
#         total_allocation = base_allocation      # full amount is available from day 1
    
#     # Carried forward (mostly relevant for annual)
#     carried_forward = contract.annual_carried_forward if leave_type == 'ANNUAL' else Decimal('0')
    
#     # Pre-used from contract (legacy/previous usage)
#     pre_used = (
#         contract.annual_leave_used if leave_type == 'ANNUAL' else
#         contract.sick_leave_used if leave_type == 'SICK' else
#         Decimal('0')
#     )
    
#     # Query for approved and pending requests
#     # Need to handle both uppercase and lowercase leave_type values in database
#     # Use case-insensitive lookup
#     approved_requests = LeaveRequest.objects.filter(
#         contract=contract,
#         leave_type__iexact=leave_type,  
#         status__iexact='APPROVED'  
#     ).aggregate(total=Sum('days_requested'))
    
#     pending_requests = LeaveRequest.objects.filter(
#         contract=contract,
#         leave_type__iexact=leave_type,  
#         status__iexact='PENDING'  
#     ).aggregate(total=Sum('days_requested'))
    
#     approved_used = approved_requests['total'] or Decimal('0')
#     pending_days = pending_requests['total'] or Decimal('0')
    
#     total_used = pre_used + approved_used
    
#     # Final available balance
#     if leave_type == 'ANNUAL':
#         available = earned_days + carried_forward - total_used - pending_days
#     else:
#         available = total_allocation - total_used - pending_days
    
#     return {
#         'available': round(available, 2),
#         'earned': round(earned_days, 2) if leave_type == 'ANNUAL' else Decimal('0'),
#         'used': round(total_used, 2),
#         'carried_forward': round(carried_forward, 2),
#         'pending': round(pending_days, 2),
#         'approved': round(approved_used, 2),
#         'pre_used': round(pre_used, 2),
#         'total_allocation': round(total_allocation, 2),
#         'is_prorated': leave_type == 'ANNUAL'
#     }


# def calculate_working_days(start_date, end_date, default_week_days=5):
#     """
#     Calculate working days between two dates (excluding weekends).
    
#     Args:
#         start_date: Start date
#         end_date: End date
#         default_week_days: Number of working days per week (default 5)
    
#     Returns:
#         Decimal: Number of working days
#     """
#     if isinstance(start_date, str):
#         start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
#     if isinstance(end_date, str):
#         end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
#     if start_date > end_date:
#         return Decimal('0')
    
#     # Get holidays in date range
#     holidays = Holiday.objects.filter(
#         date__gte=start_date,
#         date__lte=end_date,
#         is_active=True
#     ).values_list('date', flat=True)
    
#     holiday_set = set(holidays)
    
#     working_days = Decimal('0')
#     current_date = start_date
    
#     while current_date <= end_date:
#         # Check if it's a working day (not weekend and not holiday)
#         is_weekend = current_date.weekday() >= default_week_days
#         is_holiday = current_date in holiday_set
        
#         if not is_weekend and not is_holiday:
#             working_days += Decimal('1')
        
#         current_date = date.fromordinal(current_date.toordinal() + 1)
    
#     return working_days


# def validate_leave_request(user, contract, leave_type, start_date, end_date, days_requested):
#     """
#     Validate if a leave request can be made.
    
#     Returns:
#         tuple: (is_valid, error_message)
#     """
#     # Normalize leave_type to uppercase
#     leave_type = leave_type.upper()
    
#     # Check if contract is active
#     if not contract or not contract.is_current or contract.is_expired:
#         return False, "No active contract found"
    
#     # Check gender eligibility for maternity/paternity leave
#     is_eligible, gender_error = is_gender_eligible_for_leave(user.gender, leave_type)
#     if not is_eligible:
#         return False, gender_error
    
#     try:
#         if isinstance(start_date, str):
#             start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
#         if isinstance(end_date, str):
#             end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
#     except ValueError:
#         return False, "Invalid date format. Use YYYY-MM-DD"
    
#     # Check dates
#     if start_date > end_date:
#         return False, "End date must be after start date"

#     today = date.today()
#     if start_date < today:
#         return False, "Start date cannot be in the past"
        
#     # Get leave balance
#     balance = get_leave_balance(user, contract, leave_type)
    
#     if 'error' in balance:
#         return False, balance['error']
    
#     # Check if enough days available
#     if days_requested > balance['available']:
#         return False, f"Insufficient leave balance. Available: {balance['available']} days, Requested: {days_requested} days"
    
#     # Check for overlapping requests - use case-insensitive status matching
#     overlapping = LeaveRequest.objects.filter(
#         user=user,
#         contract=contract,
#         status__iexact='PENDING'
#     ).filter(
#         Q(start_date__lte=end_date, end_date__gte=start_date)
#     ).exists()
    
#     if not overlapping:
#         # Also check approved requests
#         overlapping = LeaveRequest.objects.filter(
#             user=user,
#             contract=contract,
#             status__iexact='APPROVED'
#         ).filter(
#             Q(start_date__lte=end_date, end_date__gte=start_date)
#         ).exists()
    
#     if overlapping:
#         return False, "You have an overlapping leave request"
    
#     return True, None



from datetime import datetime, date
from decimal import Decimal
from django.utils import timezone
from django.db.models import Sum, Q
from employee.models import LeaveRequest, Holiday


def earned_annual_leave(start_date, end_date, is_fte, fte_percentage, annual_allocation):
    """
    Calculate earned ANNUAL leave days based on contract duration and FTE status.
    This function is ONLY for annual leave.
    
    Args:
        start_date (date|str): Contract start date
        end_date (date|str): Contract end date (None for ongoing)
        is_fte (bool): Whether employee is FTE (part-time)
        fte_percentage (float): FTE percentage (e.g., 50 for 50%)
        annual_allocation (float): Full annual leave days allocation
    
    Returns:
        dict: {
            'earned_days': Prorated days earned so far,
            'days_per_month': Monthly accrual rate,
            'months_earned': Number of months worked,
            'contract_months': Total contract duration in months,
            'fractional_basis': FTE multiplier,
            'effective_allocation': Total allocation after FTE adjustment
        }
    """
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    today = date.today()
    accrual_end = end_date if end_date and end_date < today else today
    
    # Calculate calendar months passed
    years_diff = accrual_end.year - start_date.year
    months_diff = accrual_end.month - start_date.month
    calendar_months = years_diff * 12 + months_diff
    
    # Adjust if we haven't reached the anniversary day yet
    if accrual_end.day < start_date.day:
        calendar_months -= 1
    
    # Months earned includes current month if applicable
    months_earned = max(0, calendar_months + 1)
    
    # Calculate total contract months (for full-year reference)
    contract_months = 12
    if end_date:
        end_years = end_date.year - start_date.year
        end_months = end_date.month - start_date.month
        total_contract_months = end_years * 12 + end_months
        
        if end_date.day >= start_date.day:
            total_contract_months += 1
            
        contract_months = max(1, total_contract_months)
    
    # Apply FTE adjustment
    fractional_basis = Decimal(str(fte_percentage)) / Decimal('100') if is_fte else Decimal('1')
    effective_allocation = Decimal(str(annual_allocation)) * fractional_basis
    
    # Prorate
    days_per_month = effective_allocation / Decimal(str(contract_months))
    earned_days = Decimal(str(months_earned)) * days_per_month
    earned_days = min(earned_days, effective_allocation)
    
    return {
        'earned_days': round(earned_days, 2),
        'days_per_month': round(days_per_month, 4),
        'months_earned': months_earned,
        'contract_months': contract_months,
        'fractional_basis': round(fractional_basis, 4),
        'effective_allocation': round(effective_allocation, 2)
    }


def is_gender_eligible_for_leave(user_gender, leave_type):
    """
    Check if a user's gender is eligible for a specific leave type.
    
    Gender-specific leave types:
    - MATERNITY: Only for female employees
    - PATERNITY: Only for male employees
    - Other types: No gender restriction
    
    Args:
        user_gender (str): User's gender (case-insensitive)
        leave_type (str): Type of leave (MATERNITY, PATERNITY, etc.)
    
    Returns:
        tuple: (is_eligible: bool, error_message: str|None)
    """
    if not user_gender:
        # If gender is not set, allow all except maternity/paternity
        if leave_type in ['MATERNITY', 'PATERNITY']:
            return False, f"Gender information required for {leave_type.lower()} leave"
        return True, None
    
    # Normalize gender to lowercase for comparison
    gender_lower = user_gender.lower().strip()
    
    # Gender-specific leave type rules
    gender_rules = {
        'MATERNITY': ['female', 'woman', 'f'],
        'PATERNITY': ['male', 'man', 'm']
    }
    
    if leave_type in gender_rules:
        allowed_genders = gender_rules[leave_type]
        if gender_lower not in allowed_genders:
            gender_label = "female" if leave_type == 'MATERNITY' else "male"
            return False, f"{leave_type.capitalize()} leave is only available to {gender_label} employees"
    
    return True, None


def get_leave_balance(user, contract, leave_type='ANNUAL'):
    """
    Get current leave balance for a user's contract.
    
    Leave Calculation Logic:
    - ANNUAL leave: Prorated based on months worked (earned gradually)
    - Other types: Full allocation available from day 1 (not prorated)
    - Gender-specific validation for MATERNITY/PATERNITY
    
    Args:
        user: User instance
        contract: Contract instance
        leave_type (str): Type of leave (ANNUAL, SICK, MATERNITY, etc.)
    
    Returns:
        dict: {
            'available': Days available to request,
            'earned': Days earned so far (ANNUAL only),
            'used': Days already taken,
            'carried_forward': Days carried from previous year (ANNUAL only),
            'pending': Days in pending requests,
            'approved': Days in approved requests,
            'pre_used': Legacy/manual usage from contract,
            'total_allocation': Total days allocated,
            'is_prorated': Whether this leave type is prorated,
            'error': Error message if any
        }
    """
    # Normalize leave_type to uppercase for consistency
    leave_type = leave_type.upper()
    
    if not contract or not contract.is_current or contract.is_expired:
        return {
            'available': Decimal('0'),
            'earned': Decimal('0'),
            'used': Decimal('0'),
            'carried_forward': Decimal('0'),
            'pending': Decimal('0'),
            'approved': Decimal('0'),
            'error': 'No active contract found'
        }
    
    if not contract.leave_group:
        return {
            'available': Decimal('0'),
            'earned': Decimal('0'),
            'used': Decimal('0'),
            'carried_forward': Decimal('0'),
            'pending': Decimal('0'),
            'approved': Decimal('0'),
            'error': 'No leave group assigned'
        }
    
    # Check gender eligibility for maternity/paternity leave
    is_eligible, gender_error = is_gender_eligible_for_leave(user.gender, leave_type)
    if not is_eligible:
        return {
            'available': Decimal('0'),
            'earned': Decimal('0'),
            'used': Decimal('0'),
            'carried_forward': Decimal('0'),
            'pending': Decimal('0'),
            'approved': Decimal('0'),
            'error': gender_error
        }
    
    # Get base allocation from leave group
    allocation_map = {
        'ANNUAL': contract.leave_group.annual_days,
        'SICK': contract.leave_group.sick_days,
        'MATERNITY': contract.leave_group.maternity_days,
        'PATERNITY': contract.leave_group.paternity_days,
        'COMPASSIONATE': contract.leave_group.compassionate_days,
        'STUDY': contract.leave_group.study_days,
    }
    
    base_allocation = allocation_map.get(leave_type, Decimal('0'))
    
    if leave_type == 'ANNUAL':
        earned_calc = earned_annual_leave(
            start_date=contract.start_date,
            end_date=contract.end_date,
            is_fte=contract.is_fte,
            fte_percentage=float(contract.fte_percentage or 100),
            annual_allocation=float(base_allocation)
        )
        earned_days = Decimal(str(earned_calc['earned_days']))
        total_allocation = Decimal(str(earned_calc['effective_allocation']))
    
    else:
        earned_days = Decimal('0')      
        total_allocation = base_allocation  
    
    # Carried forward (mostly relevant for annual)
    carried_forward = contract.annual_carried_forward if leave_type == 'ANNUAL' else Decimal('0')
    

    pre_used = (
        contract.annual_leave_used if leave_type == 'ANNUAL' else
        contract.sick_leave_used if leave_type == 'SICK' else
        Decimal('0')
    )
    
    approved_requests = LeaveRequest.objects.filter(
        contract=contract,
        leave_type__iexact=leave_type,  
        status__iexact='APPROVED'  
    ).aggregate(total=Sum('days_requested'))
    
    pending_requests = LeaveRequest.objects.filter(
        contract=contract,
        leave_type__iexact=leave_type,  
        status__iexact='PENDING'  
    ).aggregate(total=Sum('days_requested'))
    
    approved_used = approved_requests['total'] or Decimal('0')
    pending_days = pending_requests['total'] or Decimal('0')
    
    total_used = pre_used + approved_used

    if leave_type == 'ANNUAL':
        available = earned_days + carried_forward - total_used - pending_days
    else:
        available = total_allocation - total_used - pending_days
    
    return {
        'available': round(available, 2),
        'earned': round(earned_days, 2) if leave_type == 'ANNUAL' else Decimal('0'),
        'used': round(total_used, 2),
        'carried_forward': round(carried_forward, 2),
        'pending': round(pending_days, 2),
        'approved': round(approved_used, 2),
        'pre_used': round(pre_used, 2),
        'total_allocation': round(total_allocation, 2),
        'is_prorated': leave_type == 'ANNUAL'
    }


def calculate_working_days(start_date, end_date, default_week_days=5, leave_type='ANNUAL'):
    """
    Calculate days between two dates based on leave type.
    
    LEAVE TYPE CALCULATION RULES:
    ┌─────────────────┬──────────────────────────────────────────────┐
    │ ANNUAL          │ Working days only (exclude weekends + holidays) │
    │ MATERNITY       │ All calendar days (include weekends + holidays) │
    │ PATERNITY       │ All calendar days (include weekends + holidays) │
    │ SICK            │ All calendar days (include weekends + holidays) │
    │ COMPASSIONATE   │ All calendar days (include weekends + holidays) │
    │ STUDY           │ All calendar days (include weekends + holidays) │
    └─────────────────┴──────────────────────────────────────────────┘
    
    Args:
        start_date (date|str): Start date
        end_date (date|str): End date
        default_week_days (int): Number of working days per week (default: 5)
        leave_type (str): Type of leave (affects calculation method)
    
    Returns:
        Decimal: Number of days calculated
    """
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    if start_date > end_date:
        return Decimal('0')
    
    # Normalize leave type
    leave_type = leave_type.upper()
    
    if leave_type == 'ANNUAL':
        holidays = Holiday.objects.filter(
            date__gte=start_date,
            date__lte=end_date
        ).values_list('date', flat=True)
        
        holiday_set = set(holidays)  
        
        working_days = Decimal('0')
        current_date = start_date
        
        while current_date <= end_date:
            is_weekend = current_date.weekday() >= default_week_days
            is_holiday = current_date in holiday_set
            
            if not is_weekend and not is_holiday:
                working_days += Decimal('1')
            
            current_date = date.fromordinal(current_date.toordinal() + 1)
        
        return working_days
    
    else:
        delta = end_date - start_date
        return Decimal(str(delta.days + 1))  



def validate_leave_request(user, contract, leave_type, start_date, end_date, days_requested):
    """
    Validate if a leave request can be made.
    
    Validation checks:
    1. Active contract exists
    2. Gender eligibility (for MATERNITY/PATERNITY)
    3. Valid date format and range
    4. Start date not in the past
    5. Sufficient leave balance
    6. No overlapping approved/pending requests
    
    Args:
        user: User instance
        contract: Contract instance
        leave_type (str): Type of leave
        start_date (date|str): Leave start date
        end_date (date|str): Leave end date
        days_requested (Decimal): Number of days requested
    
    Returns:
        tuple: (is_valid: bool, error_message: str|None)
    """
    # Normalize leave_type to uppercase
    leave_type = leave_type.upper()

    if not contract or not contract.is_current or contract.is_expired:
        return False, "No active contract found"

    is_eligible, gender_error = is_gender_eligible_for_leave(user.gender, leave_type)
    if not is_eligible:
        return False, gender_error
    

    try:
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError:
        return False, "Invalid date format. Use YYYY-MM-DD"
    

    if start_date > end_date:
        return False, "End date must be after start date"

    today = date.today()
    if start_date < today:
        return False, "Start date cannot be in the past"
    

    calculated_days = calculate_working_days(start_date, end_date, leave_type=leave_type)
    
    # Allow some tolerance for rounding (0.5 days)
    if abs(float(days_requested) - float(calculated_days)) > 0.5:
        return False, (
            f"Days requested ({days_requested}) does not match calculated days ({calculated_days}) "
            f"for leave type {leave_type}"
        )

    balance = get_leave_balance(user, contract, leave_type)
    
    if 'error' in balance:
        return False, balance['error']
    
    if days_requested > balance['available']:
        return False, (
            f"Insufficient leave balance. "
            f"Available: {balance['available']} days, "
            f"Requested: {days_requested} days"
        )
    overlapping = LeaveRequest.objects.filter(
        user=user,
        contract=contract,
        status__iexact='PENDING'
    ).filter(
        Q(start_date__lte=end_date, end_date__gte=start_date)
    ).exists()
    
    if not overlapping:
        # Also check approved requests
        overlapping = LeaveRequest.objects.filter(
            user=user,
            contract=contract,
            status__iexact='APPROVED'
        ).filter(
            Q(start_date__lte=end_date, end_date__gte=start_date)
        ).exists()
    
    if overlapping:
        return False, "You have an overlapping leave request"

    return True, None