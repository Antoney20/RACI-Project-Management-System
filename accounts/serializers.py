import uuid
from django.utils import timezone
from rest_framework import serializers
from django.contrib.auth import authenticate
from django.db.models import Q

from mint.models import LeaveAllocation
from .models import CustomUser, RoleEnum, UserStatus
from django.contrib.auth.password_validation import validate_password



class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)
    
    class Meta:
        model = CustomUser
        fields = [
            'email', 'username', 'first_name', 'last_name', 
            'phone',  'password', 'password_confirm'
        ]
    
    def validate(self, data):
        if data.get('password') != data.get('password_confirm'):
            raise serializers.ValidationError({
                'password_confirm': 'Passwords do not match.'
            })
        
        if CustomUser.objects.filter(
            email=data.get('email'),
            status=UserStatus.INVITED
        ).exists():
            raise serializers.ValidationError({
                'email': 'This email has a pending invite. Please check your email.'
            })
        
        if CustomUser.objects.filter(username=data.get('username')).exists():
            raise serializers.ValidationError({
                'username': 'Username already taken.'
            })
        
        return data
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        
        user = CustomUser(**validated_data)
        user.set_password(password)
        user.save() #save

        # Auto-create leave allocation for the user
        LeaveAllocation.objects.create(
            user=user,
            year=timezone.now().year,
            annual_leave_days=0,
            annual_used=0,
            annual_left=0,
            sick_leave_days=0,
            sick_used=0,
            other_leave_days=0,
            other_used=0
        )

        return user

class InviteSerializer(serializers.ModelSerializer):
    email = serializers.EmailField()
    role = serializers.ChoiceField(choices=RoleEnum.choices)
    department = serializers.CharField(required=False, allow_blank=True)
    position = serializers.CharField(required=False, allow_blank=True)
    message = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = CustomUser
        fields = ["email", "role", "department", "position", "message"]

    def validate_email(self, value):
        if CustomUser.objects.filter(email=value).exists():
            raise serializers.ValidationError("User with this email already exists")
        return value

    def create(self, validated_data):
        user = CustomUser.objects.create(
            email=validated_data["email"],
            role=validated_data["role"],
            department=validated_data.get("department"),
            position=validated_data.get("position"),
            is_external_member=validated_data.get("is_external_member", False),
            description=validated_data.get("description", ""),
            status=UserStatus.INVITED,
            is_active=False,
            is_invited = True,
            invited_by=self.context["request"].user,
            invite_token=uuid.uuid4(),
            invite_expires_at=timezone.now() + timezone.timedelta(days=30),
        )

        return user

class AcceptInviteSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)
    invite_token = serializers.CharField(write_only=True)

    class Meta:
        model = CustomUser
        fields = [
            "invite_token", "username", "password", "password_confirm",
            "first_name", "last_name", "phone"
        ]

    def validate_username(self, value):
        """Validate username is unique and meets requirements"""
        if len(value) < 3:
            raise serializers.ValidationError("Username must be at least 3 characters long")
        
        if CustomUser.objects.filter(username=value).exists():
            raise serializers.ValidationError("This username is already taken")
        
        return value

    def validate_invite_token(self, value):
        """Validate invite token exists and is valid"""
        try:
            user = CustomUser.objects.get(
                invite_token=value,
                is_invited=True,
                is_active=False
            )
            
            # Check if expired
            if user.invite_expires_at and user.invite_expires_at < timezone.now():
                raise serializers.ValidationError("This invitation has expired")
            
            return value
            
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError("Invalid invitation token")

    def validate(self, data):
        """Validate passwords match"""
        if data["password"] != data["password_confirm"]:
            raise serializers.ValidationError({
                "password_confirm": "Passwords do not match"
            })
        return data

    def create(self, validated_data):
        """Create/activate user account"""
        invite_token = validated_data.pop("invite_token")
        password = validated_data.pop("password")
        validated_data.pop("password_confirm")

        # Get the invited user
        user = CustomUser.objects.get(
            invite_token=invite_token,
            is_invited=True
        )

        # Update user details
        user.username = validated_data["username"]
        user.first_name = validated_data.get("first_name", "")
        user.last_name = validated_data.get("last_name", "")
        user.phone = validated_data.get("phone", "")
        user.set_password(password)
        
        # Activate account
        user.is_active = True
        user.status = "active"
        user.invite_token = None
        user.is_invited = False
        user.save()

 
        LeaveAllocation.objects.get_or_create(
            user=user,
            year=timezone.now().year,
            defaults={
                'annual_leave_days': 0,
                'annual_used': 0,
                'annual_left': 0,
                'sick_leave_days': 0,
                'sick_used': 0,
                'other_leave_days': 0,
                'other_used': 0
            }
        )

        return user


class LoginSerializer(serializers.Serializer):
    username_or_email = serializers.CharField()
    password = serializers.CharField(write_only=True)
    
    def validate(self, data):
        username_or_email = data.get('username_or_email')
        password = data.get('password')
        
        user = CustomUser.objects.filter(
            Q(username=username_or_email) | Q(email=username_or_email)
        ).first()
        
        if not user:
            raise serializers.ValidationError("Invalid username or email.")
        
        if user.status == UserStatus.BLOCKED:
            raise serializers.ValidationError(
                "Your account has been blocked. Please contact CEMA-Africa support."
            )
        
        if not user.check_password(password):
            # Increment failed login attempts
            user.failed_login_attempts += 1
            user.save(update_fields=['failed_login_attempts'])
            raise serializers.ValidationError("Invalid password.")
        
        if not user.is_active:
            raise serializers.ValidationError(
                "Your account is inactive. Please contact support."
            )
        
        # if not user.is_email_verified:
        #     raise serializers.ValidationError(
        #         "Your email has not been verified. Please wait for secretariate approval."
        #     )
        
        return {"user": user}


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    
    
    
    groups = serializers.SlugRelatedField(
        many=True,
        slug_field='name',
        read_only=True
    )

    user_permissions = serializers.SlugRelatedField(
        many=True,
        slug_field='codename',
        read_only=True
    )
    class Meta:
        model = CustomUser
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'full_name',
            'phone', 'bio',  'profile_image',
            'is_active', 'is_email_verified', 'status',
            'is_staff', 'last_login_at', 'failed_login_attempts',
            'created_at', 'updated_at', 'role', 'department', 'position',
            'is_admin', 'is_supervisor',           
            "groups",
            "user_permissions",
        ]
        read_only_fields = [
            'id', 'is_active', 'status', 'is_email_verified', 
            'last_login_at', 'created_at', 'updated_at', 'role'
        ]
    
    def get_role(self, obj):
        roles = list(obj.groups.values_list('name', flat=True))
        return roles if roles else ['staff']

    


class UserDetailSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    role = serializers.SerializerMethodField()
    is_admin = serializers.SerializerMethodField()
    is_supervisor = serializers.SerializerMethodField()
    
    groups = serializers.SlugRelatedField(
        many=True,
        slug_field='name',
        read_only=True
    )

    user_permissions = serializers.SlugRelatedField(
        many=True,
        slug_field='codename',
        read_only=True
    )
    
    class Meta:
        model = CustomUser
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'full_name',
            'phone', 'bio',  'profile_image',
            'is_active', 'is_email_verified', 'status',
            'is_staff', 'last_login_at', 'failed_login_attempts',
            'created_at', 'updated_at', 'role', 'department', 'position',
            'is_admin', 'is_supervisor', 'is_external_member',          
            "groups",
            "user_permissions",
        ]
        read_only_fields = [
            'id', 'is_active', 'status', 'is_staff', 'is_email_verified',
            'last_login_at', 'failed_login_attempts', 'created_at', 'updated_at'
        ]
    
    def get_role(self, obj):
        return list(obj.groups.values_list('name', flat=True)) or ['staff']
    
    def get_is_admin(self, obj):
        return obj.is_admin()
    
    def get_is_supervisor(self, obj):
        return obj.is_supervisor()


class PasswordResetRequestSerializer(serializers.Serializer):
    email_or_username = serializers.CharField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True, min_length=8)
    
    def validate(self, data):
        if data.get('new_password') != data.get('confirm_password'):
            raise serializers.ValidationError({
                'confirm_password': 'Passwords do not match.'
            })
        return data


class EmailVerifySerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=['approve', 'reject'])
    rejection_reason = serializers.CharField(required=False, allow_blank=True)


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True, min_length=8)
    
    def validate(self, data):
        if data.get('new_password') != data.get('confirm_password'):
            raise serializers.ValidationError({
                'confirm_password': 'New passwords do not match.'
            })
        
        if data.get('old_password') == data.get('new_password'):
            raise serializers.ValidationError({
                'new_password': 'New password must be different from old password.'
            })
        
        return data


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()



class UserListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing users"""
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = CustomUser
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'full_name', 'role', 'department', 'position',
            'is_active', 'is_external_member', 'status',
            'profile_image', 'created_at'
        ]
    
    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or obj.username


class CustomUserSerializer(serializers.ModelSerializer):
    """Full serializer for user details"""
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = CustomUser
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'full_name', 'phone', 'bio', 'profile_image',
            'role', 'department', 'position', 'is_active',
            'is_staff', 'is_external_member', 'status',
            'is_email_verified', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'is_staff'
        ]
    
    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or obj.username
    
    def update(self, instance, validated_data):
        user = self.context["request"].user
        
        # Restricted fields for non-admin users
        if not (user.is_admin() or user.role == 'office_admin'):
            restricted = [
                'role', 'status', 'is_active',
                'is_external_member'
            ]
            for field in restricted:
                validated_data.pop(field, None)
        
        return super().update(instance, validated_data)
# ============================================================================
# mint/serializers.py
# ============================================================================

# class ProjectListSerializer(serializers.ModelSerializer):
#     owner_name = serializers.CharField(source='owner.full_name', read_only=True)
#     collaborator_count = serializers.SerializerMethodField()
#     task_count = serializers.SerializerMethodField()
    
#     class Meta:
#         model = Project
#         fields = [
#             'id', 'name', 'slug', 'owner', 'owner_name', 
#             'status', 'progress', 'start_date', 'end_date',
#             'collaborator_count', 'task_count', 'created_at'
#         ]
#         read_only_fields = ['id', 'created_at']
    
#     def get_collaborator_count(self, obj):
#         return obj.collaborators.count()
    
#     def get_task_count(self, obj):
#         return obj.tasks.count()


# class ProjectDetailSerializer(serializers.ModelSerializer):
#     owner_name = serializers.CharField(source='owner.full_name', read_only=True)
#     collaborators_list = serializers.SerializerMethodField()
#     milestones_count = serializers.SerializerMethodField()
#     tasks_count = serializers.SerializerMethodField()
    
#     class Meta:
#         model = Project
#         fields = [
#             'id', 'name', 'slug', 'description', 'owner', 'owner_name',
#             'collaborators', 'collaborators_list', 'status', 'progress',
#             'start_date', 'end_date', 'milestones_count', 'tasks_count',
#             'created_at', 'updated_at'
#         ]
#         read_only_fields = ['id', 'created_at', 'updated_at']
    
#     def get_collaborators_list(self, obj):
#         return [
#             {
#                 'id': str(c.id),
#                 'username': c.username,
#                 'email': c.email,
#                 'full_name': c.full_name
#             }
#             for c in obj.collaborators.all()
#         ]
    
#     def get_milestones_count(self, obj):
#         return obj.milestones.count()
    
#     def get_tasks_count(self, obj):
#         return obj.tasks.count()


# class MilestoneSerializer(serializers.ModelSerializer):
#     project_name = serializers.CharField(source='project.name', read_only=True)
    
#     class Meta:
#         model = Milestone
#         fields = [
#             'id', 'project', 'project_name', 'title', 'description',
#             'due_date', 'is_completed', 'completed_at', 'created_at', 'updated_at'
#         ]
#         read_only_fields = ['id', 'created_at', 'updated_at']


# class TaskRACIAssignmentSerializer(serializers.ModelSerializer):
#     user_details = serializers.SerializerMethodField(read_only=True)
    
#     class Meta:
#         model = TaskRACIAssignment
#         fields = ['id', 'task', 'user', 'user_details', 'raci_role', 'created_at']
#         read_only_fields = ['id', 'created_at']
    
#     def get_user_details(self, obj):
#         return {
#             'id': str(obj.user.id),
#             'username': obj.user.username,
#             'email': obj.user.email,
#             'full_name': obj.user.full_name
#         }


# class TaskCommentSerializer(serializers.ModelSerializer):
#     user_details = serializers.SerializerMethodField(read_only=True)
    
#     class Meta:
#         model = TaskComment
#         fields = ['id', 'task', 'user', 'user_details', 'content', 'created_at', 'updated_at']
#         read_only_fields = ['id', 'user', 'created_at', 'updated_at']
    
#     def get_user_details(self, obj):
#         return {
#             'id': str(obj.user.id),
#             'username': obj.user.username,
#             'full_name': obj.user.full_name
#         }
    
#     def create(self, validated_data):
#         validated_data['user'] = self.context['request'].user
#         return super().create(validated_data)


# class TaskAttachmentSerializer(serializers.ModelSerializer):
#     uploader_name = serializers.CharField(source='uploaded_by.full_name', read_only=True)
    
#     class Meta:
#         model = TaskAttachment
#         fields = [
#             'id', 'task', 'file_name', 'file', 'file_size',
#             'mime_type', 'uploaded_by', 'uploader_name', 'created_at'
#         ]
#         read_only_fields = ['id', 'uploaded_by', 'created_at', 'file_size']
    
#     def create(self, validated_data):
#         validated_data['uploaded_by'] = self.context['request'].user
#         return super().create(validated_data)


# class TaskDetailSerializer(serializers.ModelSerializer):
#     project_name = serializers.CharField(source='project.name', read_only=True)
#     raci_assignments = TaskRACIAssignmentSerializer(many=True, read_only=True)
#     comments = TaskCommentSerializer(many=True, read_only=True)
#     attachments = TaskAttachmentSerializer(many=True, read_only=True)
    
#     class Meta:
#         model = Task
#         fields = [
#             'id', 'project', 'project_name', 'title', 'description',
#             'status', 'priority', 'progress', 'start_date', 'due_date',
#             'completed_at', 'raci_assignments', 'comments', 'attachments',
#             'created_at', 'updated_at'
#         ]
#         read_only_fields = ['id', 'created_at', 'updated_at', 'completed_at']


# class TaskListSerializer(serializers.ModelSerializer):
#     project_name = serializers.CharField(source='project.name', read_only=True)
#     assigned_users = serializers.SerializerMethodField()
    
#     class Meta:
#         model = Task
#         fields = [
#             'id', 'project', 'project_name', 'title', 'status',
#             'priority', 'progress', 'due_date', 'assigned_users', 'created_at'
#         ]
#         read_only_fields = ['id', 'created_at']
    
#     def get_assigned_users(self, obj):
#         users = obj.raci_assignments.values_list('user__username', flat=True).distinct()
#         return list(users)


# class ProjectDocumentSerializer(serializers.ModelSerializer):
#     uploader_name = serializers.CharField(source='uploaded_by.full_name', read_only=True)
    
#     class Meta:
#         model = ProjectDocument
#         fields = [
#             'id', 'project', 'title', 'description', 'document_type',
#             'file', 'file_size', 'mime_type', 'external_url',
#             'uploaded_by', 'uploader_name', 'created_at', 'updated_at'
#         ]
#         read_only_fields = ['id', 'uploaded_by', 'created_at', 'updated_at', 'file_size']
    
#     def create(self, validated_data):
#         validated_data['uploaded_by'] = self.context['request'].user
#         return super().create(validated_data)


# class LeaveRequestSerializer(serializers.ModelSerializer):
#     user_details = serializers.SerializerMethodField(read_only=True)
#     approved_by_details = serializers.SerializerMethodField(read_only=True)
    
#     class Meta:
#         model = LeaveRequest
#         fields = [
#             'id', 'user', 'user_details', 'leave_type', 'status',
#             'start_date', 'end_date', 'num_days', 'reason', 'notes',
#             'approved_by', 'approved_by_details', 'approved_at',
#             'rejection_reason', 'created_at', 'updated_at'
#         ]
#         read_only_fields = [
#             'id', 'user', 'status', 'approved_by', 'approved_at',
#             'rejection_reason', 'created_at', 'updated_at'
#         ]
    
#     def get_user_details(self, obj):
#         return {
#             'id': str(obj.user.id),
#             'username': obj.user.username,
#             'email': obj.user.email,
#             'full_name': obj.user.full_name
#         }
    
#     def get_approved_by_details(self, obj):
#         if obj.approved_by:
#             return {
#                 'id': str(obj.approved_by.id),
#                 'username': obj.approved_by.username,
#                 'full_name': obj.approved_by.full_name
#             }
#         return None
    
#     def create(self, validated_data):
#         validated_data['user'] = self.context['request'].user
#         return super().create(validated_data)


# class LeaveApprovalSerializer(serializers.Serializer):
#     action = serializers.ChoiceField(choices=['approve', 'reject'])
#     rejection_reason = serializers.CharField(required=False, allow_blank=True)


# class LeaveAllocationSerializer(serializers.ModelSerializer):
#     user_details = serializers.SerializerMethodField(read_only=True)
    
#     class Meta:
#         model = LeaveAllocation
#         fields = [
#             'id', 'user', 'user_details', 'year',
#             'annual_leave_days', 'annual_used', 'annual_remaining',
#             'sick_leave_days', 'sick_used', 'sick_remaining',
#             'special_leave_days', 'special_used', 'special_remaining',
#             'created_at', 'updated_at'
#         ]
#         read_only_fields = [
#             'id', 'annual_remaining', 'sick_remaining', 'special_remaining',
#             'created_at', 'updated_at'
#         ]
    
#     def get_user_details(self, obj):
#         return {
#             'id': str(obj.user.id),
#             'username': obj.user.username,
#             'email': obj.user.email,
#             'full_name': obj.user.full_name
#         }