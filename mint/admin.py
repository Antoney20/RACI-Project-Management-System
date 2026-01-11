from django.contrib import admin

# Register your models here.
from mint.models import LeaveAllocation, LeaveRequest, Sprint
# Milestones, Project, ProjectDocument, ProjectReviewComment, RACIAssignment, ProjectReview, Sprint
# from projects.models import Sprint

admin.site.register(LeaveAllocation)
admin.site.register(LeaveRequest)

admin.site.register(Sprint)
# admin.site.register(Project)
# admin.site.register(Milestones)
# admin.site.register(RACIAssignment)
# admin.site.register(ProjectDocument)


# admin.site.register(ProjectReview)
# admin.site.register(ProjectReviewComment)