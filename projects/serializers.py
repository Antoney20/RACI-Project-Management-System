from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from .models import (
    Sprint, Project, ProjectMilestone, ProjectMember,
    ProjectMaterial, ProjectComment, RACIRole
)

User = get_user_model()


class UserMinimalSerializer(serializers.ModelSerializer):
    """Lightweight user info for nested relations"""
    full_name = serializers.CharField(read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'full_name', 'role', 'department', 'profile_image']


class SprintSerializer(serializers.ModelSerializer):
    """Sprint/Timeline serializer"""
    created_by = UserMinimalSerializer(read_only=True)
    project_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Sprint
        fields = '__all__'
        read_only_fields = ['created_by', 'created_at', 'updated_at']
    
    def get_project_count(self, obj):
        return obj.projects.count()
    
    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)




class ProjectMilestoneSerializer(serializers.ModelSerializer):
    assigned_to = UserMinimalSerializer(read_only=True)
    assigned_to_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        source='assigned_to',
        write_only=True,
        required=False
    )


    class Meta:
        model = ProjectMilestone
        fields = '__all__'
        read_only_fields = ['completed_at', 'created_at', 'updated_at']


class ProjectMemberSerializer(serializers.ModelSerializer):
    """Project team member with RACI role"""
    user = UserMinimalSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        source='user',
        write_only=True
    )
    assigned_by = UserMinimalSerializer(read_only=True)
    
    class Meta:
        model = ProjectMember
        fields = '__all__'
        read_only_fields = ['assigned_by', 'assigned_at']
    
    def validate(self, attrs):
        """Prevent Accountable role via members (use project.accountable_person)"""
        if attrs.get('raci_role') == RACIRole.ACCOUNTABLE:
            raise serializers.ValidationError(
                "Use project.accountable_person to set Accountable role"
            )
        
        user = attrs.get('user')
        if user and user.is_blocked():
            raise serializers.ValidationError(f"Cannot assign blocked user {user.username}")
        
        return attrs
    
    def create(self, validated_data):
        validated_data['assigned_by'] = self.context['request'].user
        return super().create(validated_data)


class ProjectMaterialSerializer(serializers.ModelSerializer):
    """Project files and links"""
    uploaded_by = UserMinimalSerializer(read_only=True)
    
    class Meta:
        model = ProjectMaterial
        fields = '__all__'
        read_only_fields = ['uploaded_by', 'uploaded_at']
    
    def create(self, validated_data):
        validated_data['uploaded_by'] = self.context['request'].user
        return super().create(validated_data)


class ProjectCommentSerializer(serializers.ModelSerializer):
    """Project comments with threading support"""
    user = UserMinimalSerializer(read_only=True)
    replies = serializers.SerializerMethodField()
    reply_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ProjectComment
        fields = '__all__'
        read_only_fields = ['user', 'created_at', 'updated_at']
    
    def get_replies(self, obj):
        """Get direct replies (non-recursive for performance)"""
        if obj.parent is None:
            replies = obj.replies.all()[:5]  # Limit nested replies
            return ProjectCommentSerializer(replies, many=True, context=self.context).data
        return []
    
    def get_reply_count(self, obj):
        return obj.replies.count()
    
    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class ProjectListSerializer(serializers.ModelSerializer):
    """Lightweight project list view"""
    accountable_person = UserMinimalSerializer(read_only=True)
    sprint = serializers.StringRelatedField()
    milestone_count = serializers.SerializerMethodField()
    member_count = serializers.SerializerMethodField()
    is_overdue = serializers.BooleanField(read_only=True)
    days_remaining = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Project
        fields = [
            'id', 'name', 'status', 'priority', 'progress_percentage',
            'start_date', 'end_date', 'duration_days', 'sprint','description', 'expected_output',
            'accountable_person', 'milestone_count', 'member_count',
            'is_overdue', 'days_remaining', 'created_at'
        ]
    
    def get_milestone_count(self, obj):
        return obj.milestones.count()
    
    def get_member_count(self, obj):
        return obj.members.count()


class ProjectDetailSerializer(serializers.ModelSerializer):
    """Full project details with related data"""
    accountable_person = UserMinimalSerializer(read_only=True)
    accountable_person_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        source='accountable_person',
        write_only=True
    )
    sprint = SprintSerializer(read_only=True)
    sprint_id = serializers.PrimaryKeyRelatedField(
        queryset=Sprint.objects.all(),
        source='sprint',
        write_only=True,
        required=False
    )
    created_by = UserMinimalSerializer(read_only=True)
    
    milestones = ProjectMilestoneSerializer(many=True, read_only=True)
    members = ProjectMemberSerializer(many=True, read_only=True)
    materials = ProjectMaterialSerializer(many=True, read_only=True)
    comments = ProjectCommentSerializer(many=True, read_only=True)
    
    is_overdue = serializers.BooleanField(read_only=True)
    days_remaining = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Project
        fields = '__all__'
        read_only_fields = ['duration_days', 'created_by', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)