from decimal import Decimal
import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone

User = get_user_model()

      

class EmployeeSupervisor(models.Model):
    """Track supervisor relationships for employees"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(User, on_delete=models.CASCADE, related_name='employee_supervisors')
    supervisor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='supervised_employees')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "employee_supervisor"
       
    
    def __str__(self):
        return f"{self.employee} → {self.supervisor}"

class HolidayType(models.TextChoices):
    PUBLIC_NATIONAL = "public_national", "Public Holiday (National)"
    PUBLIC_GLOBAL = "public_global", "Public Holiday (Global)"
    ADMINISTRATIVE = "administrative", "Administrative Holiday"
    WEEKOFF = "weekoff", "Week Off",
    OTHER = "other", "Other"



class Holiday(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    date = models.DateField()
    holiday_type = models.CharField(max_length=20, choices=HolidayType.choices, default=HolidayType.PUBLIC_NATIONAL)
    is_recurring = models.BooleanField(default=False)
    
    class Meta:
        db_table = "employee_holiday"
        ordering = ["date"]
        indexes = [models.Index(fields=["date", "holiday_type"])]



class ContractType(models.TextChoices):
    INTERNSHIP = "internship", "Internship"
    FIXED_TERM_LOCUM = "fixed_term_locum", "Fixed Term (Locum Basis)"
    FTE = "fte", "FTE (Full-Time Equivalent)"
    ANNUAL = "annual", "Annual Contract"


class LeaveType(models.TextChoices):
    ANNUAL = "annual", "Annual Leave"
    SICK = "sick", "Sick Leave"
    MATERNITY = "maternity", "Maternity Leave"
    PATERNITY = "paternity", "Paternity Leave"
    COMPASSIONATE = "compassionate", "Compassionate Leave"
    STUDY = "study", "Study Leave"
    OTHER = "other", "Other"


class LeaveStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    CANCELLED = "cancelled", "Cancelled"

class GenderChoices(models.TextChoices):
    MALE = "male", "Male"
    FEMALE = "female", "Female"
    OTHER = "other", "Other"

class LeaveGroup(models.Model):
    """Define leave entitlements for different employee groups"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    
    # Leave entitlements per year (for full-time)
    annual_days = models.DecimalField(max_digits=6, decimal_places=2, default=25)
    sick_days = models.DecimalField(max_digits=6, decimal_places=2, default=10)
    maternity_days = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    paternity_days = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    compassionate_days = models.DecimalField(max_digits=6, decimal_places=2, default=5)
    study_days = models.DecimalField(max_digits=6, decimal_places=2, default=5)
    
    # Gender-specific settings
    applies_to_gender = models.CharField(
        max_length=10, 
        choices=GenderChoices.choices,
        blank=True,
        null=True,
        help_text="Leave this blank if applies to all genders"
    )
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "leave_group"
        ordering = ["name"]
    
    def __str__(self):
        return self.name


class EmployeeContract(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='contracts')
    payroll_number = models.CharField(max_length=50, blank=True, null=True)
    
    contract_type = models.CharField(max_length=30, choices=ContractType.choices)
    leave_group = models.ForeignKey(
        LeaveGroup, 
        on_delete=models.PROTECT, 
        related_name='contracts',
        null=True,      
        blank=True,
        help_text="Leave entitlement group for this contract"
    )
    
    is_fte = models.BooleanField(default=False)
    fte_percentage = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0,
        help_text="fte percentage proportion"
    )
    default_week_days = models.IntegerField(default=5)
    contract_months = models.IntegerField(blank=True, null=True)
    
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    is_current = models.BooleanField(default=True)
    is_expired = models.BooleanField(default=False) 
    is_forfeited = models.BooleanField(default=False) 
    annual_carried_forward = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0,
        help_text="Annual leave days carried forward from previous leave year"
    )


    annual_leave_used = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0,
        help_text="Annual leave days already used before system tracking"
    )

    sick_leave_used = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0,
        help_text="Sick leave days already used before system tracking"
    )

    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "employee_contract"
        ordering = ["-start_date", "-is_current"]
        indexes = [
            models.Index(fields=["user", "is_current"]),
            models.Index(fields=["start_date", "end_date"]),
            models.Index(fields=["payroll_number"]),
        ]
    

    def __str__(self):
        return f"{self.user} - {self.contract_type} ({self.start_date} to {self.end_date or 'Present'})"

class LeaveRequest(models.Model):
    """Individual leave requests"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='employee_leave_requests')
    
    contract = models.ForeignKey(
        EmployeeContract,
        on_delete=models.PROTECT,
        related_name="leave_requests",
        blank=True, null=True 
    )
    
    leave_type = models.CharField(
        max_length=20,
        choices=LeaveType.choices, 
        default=LeaveType.ANNUAL
    )
    status = models.CharField(max_length=20, choices=LeaveStatus.choices, default=LeaveStatus.PENDING)
    
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    days_requested = models.DecimalField(
        max_digits=6, 
        decimal_places=2,
        null=True,         
        blank=True,
        help_text="Number of leave days (can be fractional for half days)"
    )
    
    details = models.TextField(blank=True, null=True)
    supervisor_notes = models.TextField(blank=True, null=True)
    
    # Approval tracking
    supervisor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='leave_requests_to_approve_old',
        help_text="Supervisor assigned to approve this request old"
    )
    supervisors = models.ManyToManyField(
        User,
        related_name='leave_requests_to_approve',
        blank=True,
        help_text="Supervisors assigned to approve this request"
    )
    approved_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='leave_approvals'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, null=True)
    
    
    programme_manager_approved = models.BooleanField(
        default=False,
        help_text="Whether programme manager has approved"
    )
    programme_manager_approved_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date when programme manager approved"
    )

    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "leave_request"
        ordering = ["-start_date", "-created_at"]
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["supervisor", "status"]),
            models.Index(fields=["start_date", "end_date"]),
            models.Index(fields=["leave_type", "status"]),
        ]
        
    @staticmethod
    def get_current_for_user(user):
        return (
            EmployeeContract.objects
            .filter(user=user, is_current=True, is_expired=False)
            .order_by("-start_date")
            .first()
        )
    
    def __str__(self):
        return f"{self.user} - {self.leave_type} ({self.start_date} to {self.end_date})"
    
    
    
    
    