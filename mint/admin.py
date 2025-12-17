from django.contrib import admin

# Register your models here.
from mint.models import LeaveAllocation, LeaveRequest, Milestones, Project, ProjectDocument, RACIAssignment
# from projects.models import Sprint

admin.site.register(LeaveAllocation)
admin.site.register(LeaveRequest)
admin.site.register(Project)
# admin.site.register(Sprint)
admin.site.register(Milestones)
admin.site.register(RACIAssignment)
admin.site.register(ProjectDocument)