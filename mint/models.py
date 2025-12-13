import uuid
from django.conf import settings
from django.db import models
from django.contrib.auth import get_user_model

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

class TaskStatus(models.TextChoices):
    NOT_STARTED = "not_started", "Not Started"
    IN_PROGRESS = "in_progress", "In Progress"
    PENDING = "pending", "Pending"
    COMPLETED = "completed", "Completed"
    CANCELLED = "cancelled", "Cancelled"


class TaskPriority(models.TextChoices):
    LOW = "low", "Low"
    MEDIUM = "medium", "Medium"
    HIGH = "high", "High"
    CRITICAL = "critical", "Critical"


class RACIRole(models.TextChoices):
    RESPONSIBLE = "responsible", "Responsible (R)"
    ACCOUNTABLE = "accountable", "Accountable (A)"
    CONSULTED = "consulted", "Consulted (C)"
    INFORMED = "informed", "Informed (I)"





class Project(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)

    owner = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="owned_projects"
    )
    status = models.CharField(max_length=50, default="pending")
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    progress = models.FloatField(default=0.0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "mint_project"
        verbose_name = "Project"
        verbose_name_plural = "Projects"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["owner", "status"])
        ]

    def __str__(self):
        return self.name


# Project collaborators via RACI
class RACIAssignment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Renamed from 'task' to 'project' for clarity
    project = models.ForeignKey(
        Project, 
        on_delete=models.CASCADE, 
        related_name="raci_assignments"  # Clean, unique related_name
    )
    
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name="project_raci_assignments"  # Changed to avoid clash
    )
    raci_role = models.CharField(max_length=20, choices=RACIRole.choices)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "p_raci_assignment"
        verbose_name = "RACI Assignment"
        verbose_name_plural = "RACI Assignments"
        unique_together = ['project', 'user', 'raci_role']  # Optional: prevent duplicates
        indexes = [
            models.Index(fields=["project", "raci_role"]),
            models.Index(fields=["user", "raci_role"]),
        ]

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} - {self.raci_role} on {self.project.name}"

class Milestones(models.Model):  # Consider renaming class to Milestone (singular)
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="proj_milestones")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    due_date = models.DateTimeField(blank=True, null=True)
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "proj_mint_milestone"
        verbose_name = "Proj_Milestone"
        verbose_name_plural = "Proj_Milestones"
        ordering = ["due_date"]

    def __str__(self):
        return f"{self.project.name} - {self.title}"


class ProjectDocument(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="documents")
    title = models.CharField(max_length=200, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    document_type = models.CharField(max_length=50, blank=True, null=True)
    file = models.FileField(upload_to="projects/documents/", blank=True, null=True)
    file_size = models.IntegerField(null=True, blank=True)
    mime_type = models.CharField(max_length=100, blank=True, null=True)
    external_url = models.URLField(blank=True, null=True)
    uploaded_by = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name="uploaded_project_documents"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "mint_project_document"
        verbose_name = "Project Document"
        verbose_name_plural = "Project Documents"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title or 'Untitled'} - {self.project.name}"








###later

class Task(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="tasks")

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)

    status = models.CharField(max_length=20, choices=TaskStatus.choices, default=TaskStatus.NOT_STARTED)
    priority = models.CharField(max_length=20, choices=TaskPriority.choices, default=TaskPriority.MEDIUM)

    start_date = models.DateTimeField(null=True, blank=True)
    due_date = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    progress = models.FloatField(default=0.0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "mint_task"
        verbose_name = "Task"
        verbose_name_plural = "Tasks"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["project", "status"]),
            models.Index(fields=["priority"]),
        ]

    def __str__(self):
        return self.title


class TaskRACIAssignment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="raci_assignments")
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="task_raci_assignments"
    )
    raci_role = models.CharField(max_length=20, choices=RACIRole.choices)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "mint_task_raci_assignment"
        verbose_name = "Task RACI Assignment"
        verbose_name_plural = "Task RACI Assignments"
        unique_together = ["task", "user", "raci_role"]
        indexes = [
            models.Index(fields=["task", "raci_role"]),
            models.Index(fields=["user", "raci_role"]),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.raci_role} on {self.task.title}"


class TaskComment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="comments")
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "mint_task_comment"
        verbose_name = "Task Comment"
        verbose_name_plural = "Task Comments"
        ordering = ["created_at"]

    def __str__(self):
        return f"Comment by {self.user.username} on {self.task.title}"


class TaskAttachment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="attachments")
    file_name = models.CharField(max_length=255)
    file = models.FileField(upload_to="tasks/attachments/")
    file_size = models.IntegerField(null=True, blank=True)
    mime_type = models.CharField(max_length=100, blank=True, null=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "mint_task_attachment"
        verbose_name = "Task Attachment"
        verbose_name_plural = "Task Attachments"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.file_name} - {self.task.title}"
