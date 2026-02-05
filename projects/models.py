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
    deadline = models.DateTimeField(null=True, blank=True)
    order = models.PositiveIntegerField(
        null=True, blank=True,
        db_index=True,
        help_text="Display order within the project"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "raci_activity"
        verbose_name = "RACI Activity"
        verbose_name_plural = "RACI Activities"
        ordering = ['project', '-created_at']
        indexes = [
            models.Index(fields=["project", "status"]),
            models.Index(fields=["responsible"]),
            models.Index(fields=["accountable"]),
            models.Index(fields=["project"]),
        ]
        
        # constraints = [
        #     models.UniqueConstraint(
        #         fields=['project', 'order'],
        #         name='unique_activity_order_per_project'
        #     )
        # ]


    def save(self, *args, **kwargs):
        if self.status == 'completed':
            self.is_complete = True
            if self.completed_at is None:
                self.completed_at = timezone.now()
        else:
            self.is_complete = False
            self.completed_at = None

        # Auto-assign order on first save if missing
        if self.pk is None and self.order == 0:
            max_order = Activity.objects.filter(project=self.project).aggregate(
                models.Max('order')
            )['order__max'] or 0
            self.order = max_order + 1

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.project.name} - {self.name} (order {self.order})"
    
    
    

class UserActivityPriority(models.Model):
    """User's personal priority ordering for activities"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="activity_priorities")
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE, related_name="user_priorities")
    priority_order = models.PositiveIntegerField(default=0, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_activity_priority"
        ordering = ['user', 'priority_order']
        constraints = [
            models.UniqueConstraint(fields=['user', 'activity'], name='unique_user_activity'),
            models.UniqueConstraint(fields=['user', 'priority_order'], name='unique_user_order')
        ]

    def __str__(self):
        return f"{self.user.email} - {self.activity.name} (#{self.priority_order})"


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


class SupervisorReview(models.Model):
    REVIEW_STATUS_CHOICES = [
        ('not_started', 'Not Started'),
        ('started', 'Review Started'),
        ('completed', 'Review Completed'),
        ('reopened', 'Reopened'),
    ]

    REVIEW_LEVEL_CHOICES = [
        ('supervisor', 'Supervisor'),
        ('admin', 'Admin'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    activity = models.ForeignKey(
        Activity,
        on_delete=models.CASCADE,
        related_name="supervisor_reviews"
    )
    reviewer = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviews',
        verbose_name="Reviewer"
    )
    review_level = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        choices=REVIEW_LEVEL_CHOICES
        
    )

    status = models.CharField(
        max_length=20,
        choices=REVIEW_STATUS_CHOICES,
        default='not_started'
    )
    is_supervisor_approved = models.BooleanField(
        null=True,
        blank=True,
        help_text="Supervisor approval decision"
    )
    supervisor_approved_at = models.DateTimeField(null=True, blank=True)
    
    move_to_admin = models.BooleanField(
        default=False,
        help_text="Supervisor has escalated this review to Admin"
    )

    is_admin_approved = models.BooleanField(
        null=True,
        blank=True,
        help_text="Admin approval decision"
    )
    admin_approved_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    is_complete = models.BooleanField(
        default=False,
        editable=False
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "raci_supervisor_review"
        ordering = ['-completed_at', '-started_at']
        indexes = [
            models.Index(fields=['activity', 'status']),
            models.Index(fields=['reviewer']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['activity', 'review_level'],
                name='unique_review_per_level'
            )
        ]

    def __str__(self):
        return f" review for {self.activity}"

    def save(self, *args, **kwargs):
        if self.status == 'started' and not self.started_at:
            self.started_at = timezone.now()

        if self.status == 'completed' and not self.completed_at:
            self.completed_at = timezone.now()
            self.is_complete = True

        super().save(*args, **kwargs)

        
        
        

class Notification(models.Model):
    """Simplified notification model"""
    TYPES = [
        ('leave_pending', 'Leave Pending Approval'),
        ('leave_approved', 'Leave Approved'),
        ('leave_rejected', 'Leave Rejected'),
        ('activity_assigned', 'Activity Assigned'),
        ('activity_due', 'Activity Due Soon'),
        ('activity_overdue', 'Activity Overdue'),
        ('review_needed', 'Review Needed'),
        ('review_completed', 'Review Completed'),
        ('project_status', 'Project Status Update'),
        ('contract_expiring', 'Contract Expiring'),
        ('contract_expired', 'Contract Expired'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=30, choices=TYPES)
    title = models.CharField(max_length=255)
    message = models.TextField()
    
    # Generic linking
    related_id = models.UUIDField(null=True, blank=True)
    action_url = models.CharField(max_length=500, blank=True, null=True)
    
    # Status
    is_read = models.BooleanField(default=False)
    is_sent = models.BooleanField(default=False)
    sent_at = models.DateTimeField(null=True, blank=True)
    retry_count = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = "notification"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "is_read"]),
            models.Index(fields=["is_sent", "retry_count"]),
        ]
    
    def mark_read(self):
        self.is_read = True
        self.save(update_fields=['is_read'])
    
    def mark_sent(self):
        self.is_sent = True
        self.sent_at = timezone.now()
        self.save(update_fields=['is_sent', 'sent_at'])
