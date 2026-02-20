import uuid
from django.conf import settings
from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class LeaveType(models.TextChoices):
    ANNUAL = "annual", "Annual Leave"
    SICK = "sick", "Sick Leave"
    MATERNITY = "maternity", "Maternity Leave"
    PATERNITY = "paternity", "Paternity Leave"
    COMPASSIONATE = "compassionate", "Compassionate Leave"
    STUDY = "study", "Study Leave"
    OTHER = "other", "Other (Specify)"


class LeaveStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    CANCELLED = "cancelled", "Cancelled"


class LeaveRequest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="leave_requests"
    )
    
    position = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Job position/title of the employee"
    )
    
    supervisors = models.ManyToManyField(
        User,
        related_name="supervised_leave_requests",
        blank=True,
        help_text="Direct supervisor(s) of the employee"
    )
    
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_leave_requests",
        help_text="Supervisor/Manager who approved the request"
    )
    
    programme_manager_approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="programme_manager_approved_leave_requests",
        help_text="Programme Manager approval (can be after leave has been taken)"
    )
    
    leave_type = models.CharField(
        max_length=20,
        choices=LeaveType.choices,
        default=LeaveType.ANNUAL
    )
    
    leave_type_other = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Specify if leave_type is 'Other'"
    )
    
    status = models.CharField(
        max_length=20,
        choices=LeaveStatus.choices,
        default=LeaveStatus.PENDING
    )

    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    num_days = models.IntegerField(null=True, blank=True)
    reason = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    
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
        db_table = "mint_leave_request"
        verbose_name = "Leave Request"
        verbose_name_plural = "Leave Requests"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["start_date", "end_date"]),
        ]

    def __str__(self):
        leave_type_display = self.get_leave_type_display()
        if self.leave_type == LeaveType.OTHER and self.leave_type_other:
            leave_type_display = self.leave_type_other
        return f"{self.user.username} - {leave_type_display} ({self.status})"
    
    
    
class LeaveAllocation(models.Model):
    """Track annual leave allocation and utilization per year"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='leave_allocations'
    )
    
    position = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Job position/title"
    )

    year = models.IntegerField(default=2025)
    annual_leave_days = models.IntegerField(default=0)
    annual_used = models.IntegerField(default=0)
    annual_left = models.IntegerField(default=0)
    
    sick_leave_days = models.IntegerField(default=10)
    sick_used = models.IntegerField(default=0)
    
    maternity_leave_days = models.IntegerField(default=0)
    maternity_used = models.IntegerField(default=0)
    
    paternity_leave_days = models.IntegerField(default=0)
    paternity_used = models.IntegerField(default=0)
    
    compassionate_leave_days = models.IntegerField(default=0)
    compassionate_used = models.IntegerField(default=0)
    
    study_leave_days = models.IntegerField(default=0)
    study_used = models.IntegerField(default=0)
    
    other_leave_days = models.IntegerField(default=0)
    other_used = models.IntegerField(default=0)
    
    carryover_expiry_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "mint_leave_allocation"
        ordering = ["-year"]
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["user", "year"]),
        ]
        unique_together = [["user", "year"]]

    def __str__(self):
        return f"{self.user.username} - {self.year}"

    @property
    def annual_remaining(self):
        return self.annual_leave_days - self.annual_used

    @property
    def sick_remaining(self):
        return self.sick_leave_days - self.sick_used
    
    @property
    def maternity_remaining(self):
        return self.maternity_leave_days - self.maternity_used
    
    @property
    def paternity_remaining(self):
        return self.paternity_leave_days - self.paternity_used
    
    @property
    def compassionate_remaining(self):
        return self.compassionate_leave_days - self.compassionate_used
    
    @property
    def study_remaining(self):
        return self.study_leave_days - self.study_used

    @property
    def other_remaining(self):
        return self.other_leave_days - self.other_used





class Sprint(models.Model):
    """Sprint/Timeline for grouping projects (like Asana sections)"""
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)
    department = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    duration_template = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="e.g., '3 months'"
    )

    sprint_goals = models.TextField(
        blank=True,
        null=True,
        help_text="Describe the main objectives"
    )

    expected_deliverables = models.TextField(
        blank=True,
        null=True,
        help_text="List the key deliverables"
    )
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="created_sprints")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "sprint"
        ordering = ["-start_date"]
        indexes = [
            models.Index(fields=["start_date", "end_date"]),
            models.Index(fields=["is_active", "department"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.start_date} - {self.end_date})"

    def clean(self):
        if self.end_date and self.start_date and self.end_date < self.start_date:
            raise ValidationError("End date must be after start date")

