import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone

from mint.models import Sprint

User = get_user_model()


class Project(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    deliverables = models.TextField(
        blank=True,
        null=True,
        help_text="Expected outputs or deliverables for this project"
    )
    sprint = models.ForeignKey(Sprint, on_delete=models.SET_NULL, null=True, blank=True, related_name="projects")
    status = models.CharField(max_length=50, default="pending")
    priority = models.CharField(max_length=20, null=True, blank=True)
    start_date = models.DateTimeField(null=True, blank=True)
    duration_days = models.IntegerField(editable=False, null=True)
    end_date = models.DateTimeField(null=True, blank=True)
    
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="created_projects")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    project_link = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        help_text="Link to project resources, documentation, or repository"
    )
    class Meta:
        db_table = "raci_project"
        verbose_name = "RACI Project"
        verbose_name_plural = "RACI Projects"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"])
        ]

    def save(self, *args, **kwargs):
        if self.start_date and self.end_date:
            self.duration_days = (self.end_date - self.start_date).days
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Activity(models.Model):
    STATUS_CHOICES = [
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    

    TYPE_CHOICES = [
        ('general', 'General'),
        ('manuscript', 'Manuscript'),
        ('dashboard', 'Dashboard'),
        ('analysis', 'Analysis'),
        ('review', 'Review'),
        ('data_collection', 'Data Collection'),
        ('administrative', 'Administrative'),
        ('other', 'Other'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="activities")
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    type = models.CharField( max_length=30, choices=TYPE_CHOICES, default='general',  help_text="Category/type of activity" )
    is_complete = models.BooleanField(default=False, editable=False)
    completed_at = models.DateTimeField(null=True, blank=True, editable=False)
    # RACI roles
    responsible = models.ForeignKey( User,  on_delete=models.SET_NULL,  null=True, related_name="responsible_activities", help_text="Person doing the work")
    accountable = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name="accountable_activities",
        help_text="Person ultimately answerable"
    )
    consulted = models.ManyToManyField( User,
        blank=True,
        related_name="consulted_activities",
        help_text="People to consult"
    )
    informed = models.ManyToManyField(
        User,
        blank=True,
        related_name="informed_activities",
        help_text="People to keep informed"
    )
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='not_started')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    is_complete = models.BooleanField(default=False, editable=False)
    deadline = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "raci_activity"
        verbose_name = "RACI Activity"
        verbose_name_plural = "RACI Activities"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["project", "status"]),
            models.Index(fields=["responsible"]),
            models.Index(fields=["accountable"]),
        ]

    def clean(self):
        if self.deadline and self.project.end_date:
            if self.deadline > self.project.end_date:
                raise ValidationError("Activity deadline cannot be after project end date")

    def save(self, *args, **kwargs):
        if self.status == 'completed':
            self.is_complete = True
            if self.completed_at is None:
                self.completed_at = timezone.now()
        else:
            self.is_complete = False
            self.completed_at = None

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.project.name} - {self.name}"


class Milestone(models.Model):
    STATUS_CHOICES = [
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE, related_name="milestones")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_milestones"
    )
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='not_started')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    due_date = models.DateTimeField(blank=True, null=True)
    is_completed = models.BooleanField(default=False, editable=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "raci_milestone"
        verbose_name = "RACI Milestone"
        verbose_name_plural = "RACI Milestones"
        ordering = ["due_date"]
        indexes = [
            models.Index(fields=["activity", "status"]),
        ]

    def save(self, *args, **kwargs):
        if self.status == 'completed':
            self.is_completed = True
            if not self.completed_at:
                self.completed_at = timezone.now()
        else:
            self.is_completed = False
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.activity.name} - {self.title}"


class ActivityComment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    activity = models.ForeignKey(
        Activity, 
        on_delete=models.CASCADE, 
        related_name="comments"
    )
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name="activity_comments"
    )
    content = models.TextField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "raci_activity_comment"
        verbose_name = "RACI Activity Comment"
        verbose_name_plural = "RACI Activity Comments"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Comment by {self.user.get_full_name() or self.user.username} on {self.activity.name}"


class MilestoneComment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    milestone = models.ForeignKey(
        Milestone, 
        on_delete=models.CASCADE, 
        related_name="comments"
    )
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name="milestone_comments"
    )
    content = models.TextField()
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "raci_milestone_comment"
        verbose_name = "RACI Milestone Comment"
        verbose_name_plural = "RACI Milestone Comments"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Comment by {self.user.get_full_name() or self.user.username} on {self.milestone.title}"


class ActivityDocument(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE, related_name="documents")
    title = models.CharField(max_length=200, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    document_type = models.CharField(max_length=50, blank=True, null=True)
    file = models.FileField(upload_to="activities/documents/%Y/%m/", blank=True, null=True)
    file_size = models.IntegerField(null=True, blank=True)
    mime_type = models.CharField(max_length=100, blank=True, null=True)
    external_url = models.URLField(blank=True, null=True)
    uploaded_by = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name="uploaded_activity_documents"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "raci_activity_document"
        verbose_name = "RACI Activity Document"
        verbose_name_plural = "RACI Activity Documents"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title or 'Untitled'} - {self.activity.name}"