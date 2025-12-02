import uuid
from django.conf import settings
from django.db import models
# Create your models here.
from accounts.models import CustomUser



class LeaveType(models.TextChoices):
    ANNUAL = "annual", "Annual Leave"
    SICK = "sick", "Sick Leave"
    UNPAID = "unpaid", "Unpaid Leave"
    SPECIAL = "special", "Special Leave"


class LeaveStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    CANCELLED = "cancelled", "Cancelled"

class LeaveRequest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name="leave_requests"
    )
    
    supervisors = models.ManyToManyField(
        CustomUser,
        related_name="supervised_leave_requests",
        blank=True
    )
    
    approved_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_leave_requests",
    )
    leave_type = models.CharField(max_length=20, choices=LeaveType.choices, default=LeaveType.ANNUAL)
    status = models.CharField(max_length=20, choices=LeaveStatus.choices, default=LeaveStatus.PENDING)

    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    num_days = models.IntegerField(null=True, blank=True)
    reason = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, null=True)

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
        return f"{self.user.username} - {self.leave_type} ({self.status})"


class LeaveAllocation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        CustomUser, on_delete=models.CASCADE, related_name="leave_allocation"
    )

    annual_leave_days = models.IntegerField(default=0)
    sick_leave_days = models.IntegerField(default=0)
    special_leave_days = models.IntegerField(default=0)

    annual_used = models.IntegerField(default=0)
    sick_used = models.IntegerField(default=0)
    special_used = models.IntegerField(default=0)

    year = models.IntegerField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "mint_leave_allocation"
        verbose_name = "Leave Allocation"
        verbose_name_plural = "Leave Allocations"
        unique_together = ["user", "year"]
        indexes = [
            models.Index(fields=["user", "year"]),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.year}"

    @property
    def annual_remaining(self) -> int:
        return self.annual_leave_days - self.annual_used

    @property
    def sick_remaining(self) -> int:
        return self.sick_leave_days - self.sick_used

    @property
    def special_remaining(self) -> int:
        return self.special_leave_days - self.special_used










class TaskStatus(models.TextChoices):
    NOT_STARTED = "not_started", "Not Started"
    IN_PROGRESS = "in_progress", "In Progress"
    ON_HOLD = "on_hold", "On Hold"
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
    slug = models.SlugField(unique=True, max_length=100)

    owner = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name="owned_projects"
    )
    collaborators = models.ManyToManyField(
        CustomUser, related_name="projects", blank=True
    )

    status = models.CharField(max_length=50, default="active")
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
            models.Index(fields=["owner", "status"]),
            models.Index(fields=["slug"]),
        ]

    def __str__(self):
        return self.name


class Milestone(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="milestones")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    due_date = models.DateTimeField()
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "mint_milestone"
        verbose_name = "Milestone"
        verbose_name_plural = "Milestones"
        ordering = ["due_date"]

    def __str__(self):
        return f"{self.project.name} - {self.title}"


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
        CustomUser, on_delete=models.CASCADE, related_name="task_raci_assignments"
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
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
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
    uploaded_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "mint_task_attachment"
        verbose_name = "Task Attachment"
        verbose_name_plural = "Task Attachments"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.file_name} - {self.task.title}"


class ProjectDocument(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="documents")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    document_type = models.CharField(max_length=50, blank=True, null=True)
    file = models.FileField(upload_to="projects/documents/")
    file_size = models.IntegerField(null=True, blank=True)
    mime_type = models.CharField(max_length=100, blank=True, null=True)
    external_url = models.URLField(blank=True, null=True)
    uploaded_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "mint_project_document"
        verbose_name = "Project Document"
        verbose_name_plural = "Project Documents"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} - {self.project.name}"