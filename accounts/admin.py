from django.contrib import admin

# Register your models here.
from .models import CustomUser, EmailLog, TrustedDevice, LoginAttempt

admin.site.register(CustomUser)
admin.site.register(EmailLog)
admin.site.register(TrustedDevice)
admin.site.register(LoginAttempt)


