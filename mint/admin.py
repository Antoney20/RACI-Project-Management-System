from django.contrib import admin

# Register your models here.
from mint.models import LeaveAllocation, LeaveRequest

admin.site.register(LeaveAllocation)
admin.site.register(LeaveRequest)