from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone

User = get_user_model()


# class ProjectStatus(models.TextChoices):
#     NOT_STARTED = "not_started", "Not Started"
#     IN_PROGRESS = "in_progress", "In Progress"
#     ON_HOLD = "on_hold", "On Hold"
#     COMPLETED = "completed", "Completed"
#     CANCELLED = "cancelled", "Cancelled"


# class ProjectPriority(models.TextChoices):
#     LOW = "low", "Low"
#     MEDIUM = "medium", "Medium"
#     HIGH = "high", "High"
#     URGENT = "urgent", "Urgent"


# class MilestoneStatus(models.TextChoices):
#     PENDING = "pending", "Pending"
#     IN_PROGRESS = "in_progress", "In Progress"
#     COMPLETED = "completed", "Completed"


# class RACIRole(models.TextChoices):
#     """
#     RACI Matrix Roles:
#     - R (Responsible): Does the work
#     - A (Accountable): Signs off, ultimate ownership (ONE per project)
#     - C (Consulted): Provides input (TWO-WAY communication)
#     - I (Informed): Kept updated (ONE-WAY communication)
#     """
#     RESPONSIBLE = "R", "Responsible"
#     ACCOUNTABLE = "A", "Accountable"
#     CONSULTED = "C", "Consulted"
#     INFORMED = "I", "Informed"


# class Sprint(models.Model):
#     """Sprint/Timeline for grouping projects (like Asana sections)"""
#     name = models.CharField(max_length=200)
#     description = models.TextField(blank=True, null=True)
#     start_date = models.DateField()
#     end_date = models.DateField()
#     is_active = models.BooleanField(default=True)
#     department = models.CharField(max_length=100, blank=True, null=True, db_index=True)
#     duration_template = models.CharField(
#         max_length=100,
#         blank=True,
#         null=True,
#         help_text="e.g., '3 months'"
#     )

#     sprint_goals = models.TextField(
#         blank=True,
#         null=True,
#         help_text="Describe the main objectives"
#     )

#     expected_deliverables = models.TextField(
#         blank=True,
#         null=True,
#         help_text="List the key deliverables"
#     )
#     created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="created_sprints")
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     class Meta:
#         db_table = "projects_sprint"
#         ordering = ["-start_date"]
#         indexes = [
#             models.Index(fields=["start_date", "end_date"]),
#             models.Index(fields=["is_active", "department"]),
#         ]

#     def __str__(self):
#         return f"{self.name} ({self.start_date} - {self.end_date})"

#     def clean(self):
#         if self.end_date and self.start_date and self.end_date < self.start_date:
#             raise ValidationError("End date must be after start date")


# class Project(models.Model):
#     """
#     Main Project Model
    
#     VISIBILITY RULES:
#     - Admins: See all projects
#     - Scientific Coordinators: See all projects in their department
#     - Supervisors: See only projects where they are assigned (any RACI role)
#     - Staff: See only projects where they are assigned
#     - External: See only projects where they are Consulted/Informed
#     """
#     name = models.CharField(max_length=255, db_index=True)
#     description = models.TextField(blank=True, null=True)
#     expected_output = models.TextField(blank=True, null=True)
    
#     sprint = models.ForeignKey(Sprint, on_delete=models.SET_NULL, null=True, blank=True, related_name="projects")
#     start_date = models.DateField()
#     end_date = models.DateField()
#     duration_days = models.IntegerField(editable=False, null=True)
    
#     status = models.CharField(max_length=20, choices=ProjectStatus.choices, default=ProjectStatus.NOT_STARTED, db_index=True)
#     priority = models.CharField(max_length=20, choices=ProjectPriority.choices, default=ProjectPriority.MEDIUM, db_index=True)
#     progress_percentage = models.IntegerField(default=0)
    
#     # Project ownership
#     accountable_person = models.ForeignKey(
#         User, 
#         on_delete=models.PROTECT, 
#         related_name="accountable_projects",
#         help_text="Primary person accountable for project success (RACI: Accountable)"
#     )
    
#     created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="created_projects")
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     class Meta:
#         db_table = "projects_project"
#         ordering = ["-created_at"]
#         indexes = [
#             models.Index(fields=["status", "priority"]),
#             models.Index(fields=["accountable_person"]),
#         ]

#     def __str__(self):
#         return self.name

#     def clean(self):
#         if self.end_date and self.start_date and self.end_date < self.start_date:
#             raise ValidationError("End date must be after start date")
        
#     def save(self, *args, **kwargs):
#         if self.start_date and self.end_date:
#             self.duration_days = (self.end_date - self.start_date).days
#         super().save(*args, **kwargs)

#     @property
#     def is_overdue(self):
#         if self.status not in [ProjectStatus.COMPLETED, ProjectStatus.CANCELLED]:
#             return timezone.now().date() > self.end_date
#         return False

#     @property
#     def days_remaining(self):
#         if self.status not in [ProjectStatus.COMPLETED, ProjectStatus.CANCELLED]:
#             return (self.end_date - timezone.now().date()).days
#         return 0



# class ProjectMilestone(models.Model):
#     """
#     Milestones/subtasks within a project (like subtasks)
#     Examples: Data Cleaning, Model Training, Dashboard Development
#     """
#     project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="milestones")
#     title = models.CharField(max_length=255)
#     description = models.TextField(blank=True, null=True)
    
#     due_date = models.DateField()
#     status = models.CharField(max_length=20, choices=MilestoneStatus.choices, default=MilestoneStatus.PENDING)
    
#     # Who's responsible for this milestone
#     assigned_to = models.ForeignKey(
#         User, 
#         on_delete=models.SET_NULL, 
#         null=True, 
#         blank=True,
#         related_name="assigned_milestones"
#     )
    
#     order = models.IntegerField(default=0, help_text="Display order within project")
#     completed_at = models.DateTimeField(null=True, blank=True)
    
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     class Meta:
#         db_table = "projects_milestone"
#         ordering = ["project", "order", "due_date"]
#         indexes = [
#             models.Index(fields=["project", "status"]),
#             models.Index(fields=["assigned_to", "due_date"]),
#         ]

#     def __str__(self):
#         return f"{self.project.name} - {self.title}"

#     def save(self, *args, **kwargs):
#         if self.status == MilestoneStatus.COMPLETED and not self.completed_at:
#             self.completed_at = timezone.now()
#         super().save(*args, **kwargs)


# class ProjectMember(models.Model):
#     """
#     Project team members with RACI roles
    
#     RULES:
#     - One Accountable (A) per project (enforced at project.accountable_person)
#     - Multiple Responsible (R), Consulted (C), Informed (I) allowed
#     - External users: Only C or I roles
#     - Internal users: Any role except A (managed via accountable_person)
#     """
#     project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="members")
#     user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="project_memberships")
#     raci_role = models.CharField(max_length=1, choices=RACIRole.choices)
    
#     notes = models.TextField(blank=True, null=True)
#     assigned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="assigned_members")
#     assigned_at = models.DateTimeField(auto_now_add=True)

#     class Meta:
#         db_table = "projects_member"
#         unique_together = ["project", "user", "raci_role"]
#         indexes = [
#             models.Index(fields=["project", "raci_role"]),
#             models.Index(fields=["user"]),
#         ]

#     def __str__(self):
#         return f"{self.project.name} - {self.user.username} "

#     def clean(self): 
#         # Accountable role is managed through project.accountable_person
#         if self.raci_role == RACIRole.ACCOUNTABLE:
#             raise ValidationError("Use project.accountable_person field to set Accountable role")
        
#         if self.user.is_blocked():
#             raise ValidationError(f"Cannot assign blocked user {self.user.username}")

#     def save(self, *args, **kwargs):
#         self.full_clean()
#         super().save(*args, **kwargs)


# class ProjectMaterial(models.Model):
#     """Project files and links"""
#     MATERIAL_TYPE_CHOICES = [
#         ("file", "File Upload"),
#         ("link", "External Link"),
#     ]
    
#     project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="materials")
#     material_type = models.CharField(max_length=10, choices=MATERIAL_TYPE_CHOICES)
    
#     file = models.FileField(upload_to="projects/materials/%Y/%m/", blank=True, null=True)
#     file_name = models.CharField(max_length=255, blank=True, null=True)
    
#     link_title = models.CharField(max_length=255, blank=True, null=True)
#     link_url = models.URLField(max_length=500, blank=True, null=True)
    
#     description = models.TextField(blank=True, null=True)
#     uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="uploaded_materials")
#     uploaded_at = models.DateTimeField(auto_now_add=True)

#     class Meta:
#         db_table = "projects_material"
#         ordering = ["-uploaded_at"]

#     def __str__(self):
#         return self.file_name or self.link_title or "Material"

#     def clean(self):
#         if self.material_type == "file" and not self.file:
#             raise ValidationError("File required for file type")
#         if self.material_type == "link" and not self.link_url:
#             raise ValidationError("URL required for link type")


# class ProjectComment(models.Model):
#     """
#     Project comments with threading support
    
#     - Top-level comments: parent=None
#     - Replies: parent=<comment_id>
#     """
#     project = models.ForeignKey(
#         Project,
#         on_delete=models.CASCADE,
#         related_name="comments"
#     )
#     user = models.ForeignKey(
#         User,
#         on_delete=models.CASCADE,
#         related_name="project_comments"
#     )
#     comment = models.TextField()
#     parent = models.ForeignKey(
#         "self",
#         null=True,
#         blank=True,
#         on_delete=models.CASCADE,
#         related_name="replies",
#         help_text="Parent comment for threaded replies"
#     )

#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     class Meta:
#         db_table = "projects_comment"
#         ordering = ["-created_at"]  # Newest first
#         indexes = [
#             # Index for fetching project comments efficiently
#             models.Index(fields=["project", "-created_at"]),
#             # Index for fetching replies to a comment
#             models.Index(fields=["parent", "-created_at"]),
#             # Index for user's comments
#             models.Index(fields=["user", "-created_at"]),
#         ]

#     def __str__(self):
#         return f"{self.project.name} - {self.user.username} - {self.comment[:50]}"

#     def is_reply(self):
#         """Check if this is a reply to another comment"""
#         return self.parent is not None

#     def get_thread_depth(self):
#         """Calculate how deep this comment is in the thread"""
#         depth = 0
#         current = self.parent
#         while current is not None:
#             depth += 1
#             current = current.parent
#         return depth
