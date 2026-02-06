import uuid
from django.conf import settings
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager, Group, Permission
from django.core.validators import MinLengthValidator
from django.utils import timezone


from auditlog.registry import auditlog


class UserStatus(models.TextChoices):
    INVITED = "invited", "Invited"
    ACTIVE = "active", "Active"
    INACTIVE = "inactive", "Inactive"
    BLOCKED = "blocked", "Blocked"


class RoleEnum(models.TextChoices):
    """
    RACI System Role Hierarchy:
    
    ADMIN (System-wide)
        - Director/Principal Investigator
        - Full system access, all users, all data
    
    OFFICE_ADMIN (Office Management)
        - Office Manager / Administrative Officer
        - See all team members in their office/unit
        - Approve/reject leave requests for their team
        - View team activity and submissions
        
    SUPERVISOR (Scientific/Project)
        - Research Coordinator / Task Owner / Project Lead
        - Can only approve leave for their direct team members
        - Limited to their assigned projects/teams
        - View project-specific data only
    
    STAFF (Individual Contributors)
        - Researchers / Data Scientists / Field Officers
        - View own data
        - Cannot approve leave
        - Limited access
    """
    ADMIN = "admin", "Admin (Director/PI)"
    OFFICE_ADMIN = "office_admin", "Office Admin (Manager)"
    SUPERVISOR = "supervisor", "Supervisor (Coordinator)"
    STAFF = "staff", "Staff (Researcher)"


class CustomUserManager(BaseUserManager):
    def create_user(self, email, username, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        if not username:
            raise ValueError("The Username field must be set")

        email = self.normalize_email(email)
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)

        # Assign default user role
        user_role_group, _ = Group.objects.get_or_create(name=RoleEnum.STAFF)
        user.groups.add(user_role_group)

        return user

    def create_superuser(self, email, username, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("status", UserStatus.ACTIVE)
        return self.create_user(email, username, password, **extra_fields)
    
    def create_invited_user(self, email, role, invited_by=None, **extra):
        email = self.normalize_email(email)

        user = self.model(
            email=email,
            role=role,
            status=UserStatus.INVITED,
            is_active=False,
            invited_by=invited_by,
            invite_expires_at=timezone.now() + timezone.timedelta(days=7),
            **extra
        )
        user.set_unusable_password()
        user.save(using=self._db)

        return user


class CustomUser(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(
        max_length=150,
        unique=True,      
        null=True, blank=True 
    )
    email = models.EmailField(unique=True, db_index=True)

    first_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100, blank=True, null=True)

    phone = models.CharField(max_length=20, blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    profile_image = models.ImageField(
        upload_to="users/profiles/", blank=True, null=True
    )

    # user role
    role = models.CharField(
        max_length=20,
        choices=RoleEnum.choices,
        default=RoleEnum.STAFF,
        db_index=True
    )
    department = models.CharField(max_length=100, blank=True, null=True, db_index=True )
    position = models.CharField(max_length=100, blank=True, null=True, db_index=True )
    gender = models.CharField(max_length=20, blank=True, null=True)

    # Account status
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_external_member = models.BooleanField(default=False)
    status = models.CharField(
        max_length=20,
        choices=UserStatus.choices,
        default=UserStatus.ACTIVE,
        db_index=True
    )

    # Email verification
    is_email_verified = models.BooleanField(default=False)
    email_verified_at = models.DateTimeField(null=True, blank=True)
    verification_token = models.CharField(max_length=255, blank=True, null=True)

    # Authentication security
    last_login_at = models.DateTimeField(null=True, blank=True)
    failed_login_attempts = models.IntegerField(default=0)
    account_locked_until = models.DateTimeField(null=True, blank=True)
    force_password_change = models.BooleanField(default=False)

    # Creator (for office admin/supervisor)
    created_by = models.ForeignKey(
        "self", on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="created_users"
    )

 
    # -------------------- invite models
    is_invited = models.BooleanField(default=False)
    invite_token = models.UUIDField(
        null=True,
        blank=True,
        unique=True
    )
    description = models.TextField(blank=True, null=True)
    invite_expires_at = models.DateTimeField(null=True, blank=True)

    invited_by = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="invited_users"
    )

    invited_at = models.DateTimeField(null=True, blank=True)
    # Optional advanced permissions
    groups = models.ManyToManyField(
        Group,
        related_name="custom_users",
        blank=True
    )
    user_permissions = models.ManyToManyField(
        Permission,
        related_name="custom_users",
        blank=True
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
    # REQUIRED_FIELDS = ["username"]

    objects = CustomUserManager()

    class Meta:
        db_table = "accounts_custom_user"
        ordering = ["-created_at"]
        verbose_name = "User"
        verbose_name_plural = "Users"
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["username"]),
            models.Index(fields=["role"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"{self.username} ({self.role})"

    @property
    def full_name(self):
        return f"{self.first_name or ''} {self.last_name or ''}".strip()

    # --------------------
    # RACI ROLE CHECKS
    # --------------------
    def is_admin(self):
        return self.role == RoleEnum.ADMIN or self.is_superuser

    def is_office_admin(self):
        return self.role == RoleEnum.OFFICE_ADMIN

    def is_supervisor(self):
        return self.role == RoleEnum.SUPERVISOR

    def is_staff_member(self):
        return self.role == RoleEnum.STAFF
    
    def is_external(self):
        return self.is_external_member
    
    def get_full_name(self):
        return f"{self.first_name or ''} {self.last_name or ''}".strip()



    # --------------------
    # PERMISSION LOGIC
    # --------------------
    def can_view_all_leaves(self):
        return self.is_admin()

    def can_view_team_leaves(self):
        return self.is_supervisor() or self.is_office_admin()

    def is_blocked(self):
        return self.status == UserStatus.BLOCKED

    def save(self, *args, **kwargs):
        # Auto-disable login if blocked
        if self.status == UserStatus.BLOCKED:
            self.is_active = False
        super().save(*args, **kwargs)
        
        
class TokenBlacklist(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    token_jti = models.CharField(max_length=255, unique=True, db_index=True)
    token_type = models.CharField(max_length=20)  # 'access' or 'refresh'
    is_verified = models.BooleanField(default=False)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="blacklisted_tokens")
    blacklisted_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    reason = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        db_table = "accounts_token_blacklist"
        verbose_name = "Token Blacklist"
        verbose_name_plural = "Token Blacklists"
        indexes = [
            models.Index(fields=["token_jti"]),
            models.Index(fields=["user"]),
            models.Index(fields=["expires_at"]),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.token_type}"

class EmailLog(models.Model):
    STATUS_CHOICES = [
        ('initial', 'Initial'),
        ('sending', 'Sending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
    ]

    subject = models.TextField()
    message = models.TextField(blank=True, null=True)
    sender = models.CharField(
        max_length=255,
        default=settings.DEFAULT_FROM_EMAIL
    )
    recipient = models.TextField(help_text="Receiver email address")
    category = models.CharField(max_length=50, default='other')
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='initial'
    )
    error_message = models.TextField(blank=True, null=True)
    retry_count = models.PositiveIntegerField(default=0)
    last_attempt = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(blank=True, null=True)

    def mark_sending(self):
        self.status = 'sending'
        self.last_attempt = timezone.now()
        self.save(update_fields=['status', 'last_attempt'])

    def mark_sent(self):
        self.status = 'sent'
        self.sent_at = timezone.now()
        self.error_message = None
        self.save(update_fields=['status', 'sent_at', 'error_message'])

    def mark_failed(self, exc):
        self.status = 'failed'
        self.error_message = str(exc)
        self.retry_count += 1
        self.last_attempt = timezone.now()
        self.save(
            update_fields=[
                'status',
                'error_message',
                'retry_count',
                'last_attempt'
            ]
        )

    def __str__(self):
        return f"[{self.category}] {self.subject} → {self.recipient} ({self.status})"
    


class TrustedDevice(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    device_id = models.CharField(max_length=128)

    # Client / metadata (optional)
    device_name = models.CharField(max_length=100, blank=True)
    device_type = models.CharField(max_length=50, blank=True)

    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    browser = models.CharField(max_length=100, blank=True)
    os = models.CharField(max_length=100, blank=True)

    # Security state
    is_trusted = models.BooleanField(default=True)
    is_suspicious = models.BooleanField(default=False)

    failed_attempts = models.PositiveIntegerField(default=0)
    last_failed_attempt_at = models.DateTimeField(null=True, blank=True)

    verification_token = models.UUIDField(null=True, blank=True)
    verification_expires_at = models.DateTimeField(null=True, blank=True)

    last_used_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True,null=True, blank=True)


    class Meta:
        unique_together = [['user', 'device_id']]
        ordering = ['-last_used_at']

    def register_failed_attempt(self):
        now = timezone.now()

        if self.last_failed_attempt_at and now - self.last_failed_attempt_at > timezone.timedelta(minutes=30):
            self.failed_attempts = 0

        self.failed_attempts += 1
        self.last_failed_attempt_at = now

        if self.failed_attempts >= 5:
            self.is_suspicious = True
            self.is_trusted = False
            self.verification_token = uuid.uuid4()
            self.verification_expires_at = now + timezone.timedelta(hours=24)

        self.save()

    def reset_failures(self):
        self.failed_attempts = 0
        self.last_failed_attempt_at = None
        self.save(update_fields=["failed_attempts", "last_failed_attempt_at"])
        
class LoginAttempt(models.Model):
    STATUS_CHOICES = (
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('blocked', 'Blocked'),
    )

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    device_id = models.CharField(max_length=128, blank=True)

    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    browser = models.CharField(max_length=100, blank=True)
    os = models.CharField(max_length=100, blank=True)
    device_type = models.CharField(max_length=50, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    payload = models.JSONField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['ip_address']),
            models.Index(fields=['status']),
        ]
        
        

class NotificationPreference(models.Model):
    """User preferences for notification emails"""
    
    ALERT_TIMING_CHOICES = [
        (1, '1 Day Before'),
        (3, '3 Days Before'),
        (7, '7 Days Before'),
        (14, '14 Days Before'),
    ]
    
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='notification_preferences'
    )
    
    # Email notification toggles by category
    email_leave_approvals = models.BooleanField(default=True)
    email_activities = models.BooleanField(default=True)
    email_reviews = models.BooleanField(default=True)
    email_contracts = models.BooleanField(default=True)
    
    # Alert timing preferences
    activity_due_alert_days = models.IntegerField(
        choices=ALERT_TIMING_CHOICES,
        default=3,
        help_text="Days before deadline to send alert"
    )
    contract_expiry_alert_days = models.IntegerField(
        choices=ALERT_TIMING_CHOICES,
        default=14,
        help_text="Days before contract expiry to send alert"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "notification_preference"
    
    def __str__(self):
        return f"Preferences for {self.user.username}"
    
    def should_send_email(self, notification_type):
        """Check if user wants email for this notification type"""
        type_mapping = {
            'leave_pending': self.email_leave_approvals,
            'activity_assigned': self.email_activities,
            'activity_due': self.email_activities,
            'activity_overdue': self.email_activities,
            'review_needed': self.email_reviews,
            'contract_expiring': self.email_contracts,
        }
        return type_mapping.get(notification_type, True)



auditlog.register(CustomUser)
auditlog.register(TrustedDevice)
auditlog.register(EmailLog)
auditlog.register(LoginAttempt)