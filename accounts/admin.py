from django.contrib import admin

# Register your models here.
from .models import CustomUser, EmailLog

admin.site.register(CustomUser)
admin.site.register(EmailLog)


