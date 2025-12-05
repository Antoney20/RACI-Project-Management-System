from django.utils import timezone
from rest_framework import serializers
from django.contrib.auth import authenticate
from django.db.models import Q

from mint.models import LeaveAllocation
from .models import CustomUser, UserStatus



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
        
        if CustomUser.objects.filter(email=data.get('email')).exists():
            raise serializers.ValidationError({
                'email': 'Email already registered.'
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
    role = serializers.SerializerMethodField()
    
    class Meta:
        model = CustomUser
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'full_name',
            'phone', 'bio',  'profile_image',
            'is_active', 'is_email_verified', 'status',
            'last_login_at', 'created_at', 'updated_at', 'role'
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
    
    class Meta:
        model = CustomUser
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'full_name',
            'phone', 'bio',  'profile_image',
            'is_active', 'is_email_verified', 'status',
            'is_staff', 'last_login_at', 'failed_login_attempts',
            'created_at', 'updated_at', 'role', 'department', 'position',
            'is_admin', 'is_supervisor'
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



class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = "__all__"
        read_only_fields = [
            "id", "created_at", "updated_at", "created_by",
            "is_superuser", "is_staff",
        ]
    def update(self, instance, validated_data):
        user = self.context["request"].user

        # Regular users cannot modify sensitive fields
        restricted_fields = [
            "role", "status", "is_active",
            "created_by", "failed_login_attempts",
            "account_locked_until", "is_external_member"
        ]

        if not user.is_admin():
            for field in restricted_fields:
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