import uuid
from django.conf import settings
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager, Group, Permission
from django.core.validators import MinLengthValidator
from django.utils import timezone


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

