from django.contrib import admin

# # Register your models here.
from .models import  Project, Activity, SupervisorReview


admin.site.register(Project)
admin.site.register(Activity)
admin.site.register(SupervisorReview)
# admin.site.register(ProjectMilestone)
# admin.site.register(RACIAssignment)
# admin.site.register(ProjectDocument)
