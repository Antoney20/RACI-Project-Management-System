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




# class TaskStatus(models.TextChoices):
#     NOT_STARTED = "not_started", "Not Started"
#     IN_PROGRESS = "in_progress", "In Progress"
#     PENDING = "pending", "Pending"
#     COMPLETED = "completed", "Completed"
#     CANCELLED = "cancelled", "Cancelled"

# class TaskPriority(models.TextChoices):
#     LOW = "low", "Low"
#     MEDIUM = "medium", "Medium"
#     HIGH = "high", "High"
#     URGENT = "urgent", "Urgent"


# class RACIRole(models.TextChoices):
#     RESPONSIBLE = "R", "Responsible"
#     ACCOUNTABLE = "A", "Accountable"
#     CONSULTED = "C", "Consulted"
#     INFORMED = "I", "Informed"




# class ProjectStatus(models.TextChoices):
#     NOT_STARTED = "not_started", "Not Started"
#     IN_PROGRESS = "in_progress", "In Progress"
#     ON_HOLD = "on_hold", "On Hold"
#     COMPLETED = "completed", "Completed"
#     CANCELLED = "cancelled", "Cancelled"





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




# class Project(models.Model):
#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     name = models.CharField(max_length=200)
#     description = models.TextField(blank=True, null=True)

#     owner = models.ForeignKey(
#         User, on_delete=models.CASCADE, related_name="owned_projects"
#     )
#     sprint = models.ForeignKey(Sprint, on_delete=models.SET_NULL, null=True, blank=True, related_name="projects")
#     status = models.CharField(max_length=50, default="pending")
#     priority = models.CharField(max_length=20, null=True, blank=True)
#     start_date = models.DateTimeField(null=True, blank=True)
#     duration_days = models.IntegerField(editable=False, null=True)
#     end_date = models.DateTimeField(null=True, blank=True)
#     progress = models.FloatField(default=0.0)

#     created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="created_projects")
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)
    
    
    
#     project_link = models.URLField(
#         max_length=500,
#         blank=True,
#         null=True,
#         help_text="Link to project resources, documentation, or repository"
#     )
    
    
#     supervisors = models.ManyToManyField(
#         User,
#         related_name="supervised_projects",
#         blank=True,
#         verbose_name="Project Supervisors",
#         help_text="The supervisors/coordinators responsible for this project"
#     )
    
#     notify_supervisor = models.BooleanField(
#         default=False,
#         help_text="Notify supervisor/informed users when project status changes"
#     )
    
#     comment_notify = models.BooleanField(
#         default=True,
#         help_text="Send notifications when comments are added to project reviews"
#     )
    

#     class Meta:
#         db_table = "mint_project"
#         verbose_name = "Project"
#         verbose_name_plural = "Projects"
#         ordering = ["-created_at"]
#         indexes = [
#             models.Index(fields=["owner", "status"])
#         ]

#     def save(self, *args, **kwargs):
#         if self.start_date and self.end_date:
#             self.duration_days = (self.end_date - self.start_date).days
#         super().save(*args, **kwargs)

#     def __str__(self):
#         return self.name
    

    
#     @property
#     def supervisor_list(self):
#         """Return list of supervisor names"""
#         return [sup.get_full_name() or sup.email for sup in self.supervisors.all()]



# class RACIAssignment(models.Model):
#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
#     project = models.ForeignKey(
#         Project, 
#         on_delete=models.CASCADE, 
#         related_name="raci_assignments" 
#     )
    
#     user = models.ForeignKey(
#         User, 
#         on_delete=models.CASCADE, 
#         related_name="project_raci_assignments"  
#     )
#     raci_role = models.CharField(max_length=20, choices=RACIRole.choices)

#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     class Meta:
#         db_table = "p_raci_assignment"
#         verbose_name = "RACI Assignment"
#         verbose_name_plural = "RACI Assignments"
#         indexes = [
#             models.Index(fields=["project", "raci_role"]),
#             models.Index(fields=["user", "raci_role"]),
#         ]

#     def __str__(self):
#         return f"{self.user.get_full_name() or self.user.username} - {self.raci_role} on {self.project.name}"

# class Milestones(models.Model): 
#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="proj_milestones")
#     title = models.CharField(max_length=200)
#     description = models.TextField(blank=True, null=True)
#     due_date = models.DateTimeField(blank=True, null=True)
#     is_completed = models.BooleanField(default=False)
#     completed_at = models.DateTimeField(null=True, blank=True)

#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     class Meta:
#         db_table = "proj_mint_milestone"
#         verbose_name = "Proj_Milestone"
#         verbose_name_plural = "Proj_Milestones"
#         ordering = ["due_date"]

#     def __str__(self):
#         return f"{self.project.name} - {self.title}"


# class ProjectDocument(models.Model):
#     project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="documents")
#     title = models.CharField(max_length=200, blank=True, null=True)
#     description = models.TextField(blank=True, null=True)
#     document_type = models.CharField(max_length=50, blank=True, null=True)
#     file = models.FileField(upload_to="projects/documents/%Y/%m/", blank=True, null=True)
#     file_size = models.IntegerField(null=True, blank=True)
#     mime_type = models.CharField(max_length=100, blank=True, null=True)
#     external_url = models.URLField(blank=True, null=True)
#     uploaded_by = models.ForeignKey(
#         User, 
#         on_delete=models.CASCADE, 
#         related_name="uploaded_project_documents"
#     )

#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     class Meta:
#         db_table = "mint_project_document"
#         verbose_name = "Project Document"
#         verbose_name_plural = "Project Documents"
#         ordering = ["-created_at"]

#     def __str__(self):
#         return f"{self.title or 'Untitled'} - {self.project.name}"



# # class ProjectComment(models.Model):
# #     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
# #     project = models.ForeignKey(
# #         Project, 
# #         on_delete=models.CASCADE, 
# #         related_name="comments"
# #     )
# #     user = models.ForeignKey(
# #         User, 
# #         on_delete=models.CASCADE, 
# #         related_name="project_comments"
# #     )
# #     content = models.TextField()
    
# #     created_at = models.DateTimeField(auto_now_add=True)
# #     updated_at = models.DateTimeField(auto_now=True)

# #     class Meta:
# #         db_table = "mint_project_comment"
# #         verbose_name = "Project Comment"
# #         verbose_name_plural = "Project Comments"
# #         ordering = ["-created_at"]

# #     def __str__(self):
# #         return f"Comment by {self.user.get_full_name()} on {self.project.name}"


# # class ProjectNote(models.Model):
# #     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
# #     project = models.ForeignKey(
# #         Project, 
# #         on_delete=models.CASCADE, 
# #         related_name="notes"
# #     )
# #     user = models.ForeignKey(
# #         User, 
# #         on_delete=models.CASCADE, 
# #         related_name="project_notes"
# #     )
# #     title = models.CharField(max_length=200, blank=True, null=True)
# #     content = models.TextField()
    
# #     created_at = models.DateTimeField(auto_now_add=True)
# #     updated_at = models.DateTimeField(auto_now=True)

# #     class Meta:
# #         db_table = "mint_project_note"
# #         verbose_name = "Project Note"
# #         verbose_name_plural = "Project Notes"
# #         ordering = ["-created_at"]

# #     def __str__(self):
# #         return f"Note by {self.user.get_full_name()} on {self.project.name}"


# # class MilestoneComment(models.Model):
# #     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
# #     milestone = models.ForeignKey(
# #         Milestones, 
# #         on_delete=models.CASCADE, 
# #         related_name="comments"
# #     )
# #     user = models.ForeignKey(
# #         User, 
# #         on_delete=models.CASCADE, 
# #         related_name="milestone_comments"
# #     )
# #     content = models.TextField()
    
# #     created_at = models.DateTimeField(auto_now_add=True)

# #     class Meta:
# #         db_table = "mint_milestone_comment"
# #         verbose_name = "Milestone Comment"
# #         verbose_name_plural = "Milestone Comments"
# #         ordering = ["-created_at"]

# #     def __str__(self):
# #         return f"Comment by {self.user.get_full_name()} on {self.milestone.title}"







# class ProjectReviewStatus(models.TextChoices):
#     PENDING = "pending", "Pending"
#     ON_REVIEW = "on_review", "On Review"
#     SUCCESSFULLY_REVIEWED = "successfully_reviewed", "Successfully Reviewed"
#     CHANGES_REQUESTED = "changes_requested", "Changes Requested"




# class ProjectReview(models.Model):
#     """Review for completed projects by supervisors/informed users"""
#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
#     project = models.OneToOneField(
#         Project,
#         on_delete=models.CASCADE,
#         related_name="project_review",
#         help_text="The project being reviewed"
#     )
    
#     status = models.CharField(
#         max_length=50,
#         choices=ProjectReviewStatus.choices,
#         default=ProjectReviewStatus.PENDING,
#         help_text="Current status of the review"
#     )
    
#     reviewer = models.ForeignKey(
#         User,
#         on_delete=models.SET_NULL,
#         null=True,
#         blank=True,
#         related_name="project_reviews_conducted",
#         help_text="Primary reviewer (typically supervisor/informed user)"
#     )
    
#     review_summary = models.TextField(
#         blank=True,
#         null=True,
#         help_text="Overall review summary and feedback"
#     )
    
    
#     submitted_at = models.DateTimeField(
#         null=True,
#         blank=True,
#         help_text="When the project was submitted for review"
#     )
    
#     reviewed_at = models.DateTimeField(
#         null=True,
#         blank=True,
#         help_text="When the review was completed"
#     )
    
#     is_closed = models.BooleanField(
#         default=False,
#         help_text="Mark project review as closed/completed"
#     )
    
#     closed_at = models.DateTimeField(
#         null=True,
#         blank=True,
#         help_text="Timestamp when project review was closed"
#     )
    
    
#     created_by = models.ForeignKey(
#         User,
#         on_delete=models.SET_NULL,
#         null=True,
#         related_name="project_reviews_created"
#     )
    
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     class Meta:
#         db_table = "project_review"
#         verbose_name = "Project Review"
#         verbose_name_plural = "Project Reviews"
#         ordering = ["-created_at"]
#         indexes = [
#             models.Index(fields=["project", "status"]),
#             models.Index(fields=["reviewer", "status"]),
#             models.Index(fields=["status", "submitted_at"]),
#         ]


#     def save(self, *args, **kwargs):
#         from django.utils import timezone
        
#         # Auto-set reviewed_at when status changes to successfully_reviewed
#         if self.status == ProjectReviewStatus.SUCCESSFULLY_REVIEWED and not self.reviewed_at:
#             self.reviewed_at = timezone.now()
            
#         # Set submitted_at on first save if not set
#         if not self.pk and not self.submitted_at:
#             self.submitted_at = timezone.now()
            
#         super().save(*args, **kwargs)

#     def __str__(self):
#         return f"Review for {self.project.name} "


# class ProjectReviewComment(models.Model):
#     """Comments on project reviews"""
#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
#     review = models.ForeignKey(
#         ProjectReview,
#         on_delete=models.CASCADE,
#         related_name="comments",
#         help_text="The review this comment belongs to"
#     )
    
#     user = models.ForeignKey(
#         User,
#         on_delete=models.CASCADE,
#         related_name="review_comments",
#         help_text="User who made the comment"
#     )
    
#     comment = models.TextField(
#         help_text="Comment content"
#     )
    
#     attachment_links = models.JSONField(
#         default=list,
#         blank=True,
#         help_text="List of URLs for attachments/references"
#     )
    
#     is_resolved = models.BooleanField(
#         default=False,
#         help_text="Mark if this comment/issue has been resolved"
#     )
    
#     parent_comment = models.ForeignKey(
#         'self',
#         on_delete=models.CASCADE,
#         null=True,
#         blank=True,
#         related_name="replies",
#         help_text="Parent comment for threaded discussions"
#     )
    
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     class Meta:
#         db_table = "project_review_comment"
#         verbose_name = "Project Review Comment"
#         verbose_name_plural = "Project Review Comments"
#         ordering = ["created_at"]
#         indexes = [
#             models.Index(fields=["review", "created_at"]),
#             models.Index(fields=["user", "created_at"]),
#             models.Index(fields=["is_resolved"]),
#         ]

#     def __str__(self):
#         return f"Comment by {self.user.get_full_name() or self.user.username} on {self.review}"













# class EventType(models.TextChoices):
#     LEAVE = "leave", "Leave"
#     PROJECT_DEADLINE = "project_deadline", "Project Deadline"
#     MILESTONE = "milestone", "Milestone"
#     PUBLIC_HOLIDAY = "public_holiday", "Public Holiday"
#     WEEKEND = "weekend", "Weekend"
#     MEETING = "meeting", "Meeting"
#     OTHER = "other", "Other"


# class CalendarEvent(models.Model):
#     """Unified calendar events for all activities"""
#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
#     title = models.CharField(max_length=200)
#     description = models.TextField(blank=True, null=True)
    
#     event_type = models.CharField(
#         max_length=30,
#         choices=EventType.choices
#     )
    
#     start_date = models.DateTimeField()
#     end_date = models.DateTimeField()
#     all_day = models.BooleanField(default=False)
    
#     # Link to related objects
#     user = models.ForeignKey(
#         User,
#         on_delete=models.CASCADE,
#         null=True,
#         blank=True,
#         related_name="calendar_events",
#         help_text="User associated with this event (for leaves, personal events)"
#     )
    
#     project = models.ForeignKey(
#         "Project",
#         on_delete=models.CASCADE,
#         null=True,
#         blank=True,
#         related_name="calendar_events"
#     )
    
#     milestone = models.ForeignKey(
#         "Milestones",
#         on_delete=models.CASCADE,
#         null=True,
#         blank=True,
#         related_name="calendar_events"
#     )
    
#     leave_request = models.ForeignKey(
#         "LeaveRequest",
#         on_delete=models.CASCADE,
#         null=True,
#         blank=True,
#         related_name="calendar_events"
#     )
    
#     is_public = models.BooleanField(
#         default=False,
#         help_text="Public holidays, weekends visible to all"
#     )
    
#     color = models.CharField(
#         max_length=7,
#         blank=True,
#         null=True,
#         help_text="Hex color code for display"
#     )
    
#     created_by = models.ForeignKey(
#         User,
#         on_delete=models.SET_NULL,
#         null=True,
#         related_name="created_events"
#     )
    
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     class Meta:
#         db_table = "mint_calendar_event"
#         verbose_name = "Calendar Event"
#         verbose_name_plural = "Calendar Events"
#         ordering = ["start_date"]
#         indexes = [  
#             models.Index(fields=["start_date", "end_date"]),
#             models.Index(fields=["event_type", "is_public"]),
#             models.Index(fields=["user", "start_date"]),
#         ]

#     def __str__(self):
#         return f"{self.title} ({self.event_type}) - {self.start_date.date()}"




















































































































# class PublicHoliday(models.Model):
#     """Kenya public holidays"""
#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
#     name = models.CharField(max_length=200)
#     date = models.DateField()
#     year = models.IntegerField()
#     is_recurring = models.BooleanField(
#         default=False,
#         help_text="Recurs annually on same date"
#     )
    
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     class Meta:
#         db_table = "mint_public_holiday"
#         verbose_name = "Public Holiday"
#         verbose_name_plural = "Public Holidays"
#         ordering = ["date"]
#         unique_together = [["date", "year"]]
#         indexes = [
#             models.Index(fields=["date", "year"]),
#         ]

#     def __str__(self):
#         return f"{self.name} - {self.date}"


# ###later

# class Task(models.Model):
#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="tasks")

#     title = models.CharField(max_length=200)
#     description = models.TextField(blank=True, null=True)

#     status = models.CharField(max_length=20, choices=TaskStatus.choices, default=TaskStatus.NOT_STARTED)
#     priority = models.CharField(max_length=20, choices=TaskPriority.choices, default=TaskPriority.MEDIUM)

#     start_date = models.DateTimeField(null=True, blank=True)
#     due_date = models.DateTimeField(null=True, blank=True)
#     completed_at = models.DateTimeField(null=True, blank=True)
#     progress = models.FloatField(default=0.0)

#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     class Meta:
#         db_table = "mint_task"
#         verbose_name = "Task"
#         verbose_name_plural = "Tasks"
#         ordering = ["-created_at"]
#         indexes = [
#             models.Index(fields=["project", "status"]),
#             models.Index(fields=["priority"]),
#         ]

#     def __str__(self):
#         return self.title


# class TaskRACIAssignment(models.Model):
#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="raci_assignments")
#     user = models.ForeignKey(
#         User, on_delete=models.CASCADE, related_name="task_raci_assignments"
#     )
#     raci_role = models.CharField(max_length=20, choices=RACIRole.choices)

#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     class Meta:
#         db_table = "mint_task_raci_assignment"
#         verbose_name = "Task RACI Assignment"
#         verbose_name_plural = "Task RACI Assignments"
#         unique_together = ["task", "user", "raci_role"]
#         indexes = [
#             models.Index(fields=["task", "raci_role"]),
#             models.Index(fields=["user", "raci_role"]),
#         ]

#     def __str__(self):
#         return f"{self.user.username} - {self.raci_role} on {self.task.title}"


# class TaskComment(models.Model):
#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="comments")
#     user = models.ForeignKey(User, on_delete=models.CASCADE)
#     content = models.TextField()

#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     class Meta:
#         db_table = "mint_task_comment"
#         verbose_name = "Task Comment"
#         verbose_name_plural = "Task Comments"
#         ordering = ["created_at"]

#     def __str__(self):
#         return f"Comment by {self.user.username} on {self.task.title}"


# class TaskAttachment(models.Model):
#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="attachments")
#     file_name = models.CharField(max_length=255)
#     file = models.FileField(upload_to="tasks/attachments/")
#     file_size = models.IntegerField(null=True, blank=True)
#     mime_type = models.CharField(max_length=100, blank=True, null=True)
#     uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)

#     created_at = models.DateTimeField(auto_now_add=True)

#     class Meta:
#         db_table = "mint_task_attachment"
#         verbose_name = "Task Attachment"
#         verbose_name_plural = "Task Attachments"
#         ordering = ["-created_at"]

#     def __str__(self):
#         return f"{self.file_name} - {self.task.title}"
