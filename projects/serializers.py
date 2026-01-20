from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Project, Activity, Milestone, ActivityComment, MilestoneComment, ActivityDocument
from mint.models import Sprint

User = get_user_model()


class UserMinimalSerializer(serializers.ModelSerializer):
    """Lightweight user info for nested relations"""
    full_name = serializers.CharField(read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'full_name', 'gender', 'role', 'department', 'profile_image']


# PROJECT SERIALIZERS
class ProjectCreateSerializer(serializers.ModelSerializer):
    sprint_id = serializers.PrimaryKeyRelatedField(
        queryset=Sprint.objects.all(),
        source='sprint',
        write_only=True,
        required=False,
        allow_null=True
    )

    class Meta:
        model = Project
        fields = [
            'id', 'name', 'description', 'sprint_id', 'priority', 'status',
            'deliverables',
            'start_date', 'end_date', 'project_link', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class ProjectListSerializer(serializers.ModelSerializer):
    created_by = UserMinimalSerializer(read_only=True)
    activity_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Project
        fields = [
            'id', 'name', 'description', 'sprint', 'status', 'priority', 'deliverables',
            'start_date', 'end_date', 'project_link', 'created_by', 
            'activity_count', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_activity_count(self, obj):
        return obj.activities.count()


class ProjectDetailSerializer(serializers.ModelSerializer):
    created_by = UserMinimalSerializer(read_only=True)
    
    class Meta:
        model = Project
        fields = [
            'id', 'name', 'description', 'sprint', 'status', 'priority', 'deliverables',
            'start_date', 'end_date', 'duration_days', 'project_link',
            'created_by', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'duration_days', 'created_at', 'updated_at']


# ACTIVITY SERIALIZERS
class ActivityCreateSerializer(serializers.ModelSerializer):
    project_id = serializers.PrimaryKeyRelatedField(
        queryset=Project.objects.all(),
        source='project',
        write_only=True
    )
    responsible_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        source='responsible',
        write_only=True,
        required=False,
        allow_null=True
    )
    accountable_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        source='accountable',
        write_only=True,
        required=False,
        allow_null=True
    )
    consulted_ids = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        source='consulted',
        many=True,
        write_only=True,
        required=False
    )
    informed_ids = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        source='informed',
        many=True,
        write_only=True,
        required=False
    )

    class Meta:
        model = Activity
        fields = [
            'id', 'project_id', 'name', 'description', 'responsible_id',
            'accountable_id', 'consulted_ids', 'informed_ids', 'status',
            'priority', 'deadline', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class ActivityListSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source='project.name', read_only=True)
    responsible = UserMinimalSerializer(read_only=True)
    informed = UserMinimalSerializer(read_only=True, many=True)
    consulted = UserMinimalSerializer(read_only=True, many=True)
    accountable = UserMinimalSerializer(read_only=True)
    milestone_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Activity
        fields = [
            'id', 'project', 'project_name', 'name', 'responsible', 'accountable', 'consulted','informed',
            'status', 'priority', 'is_complete', 'deadline', 'milestone_count', 'created_at'
        ]
        read_only_fields = ['id', 'is_complete', 'created_at']
    
    def get_milestone_count(self, obj):
        return obj.milestones.count()


class ActivityDetailSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source='project.name', read_only=True)
    responsible = UserMinimalSerializer(read_only=True)
    accountable = UserMinimalSerializer(read_only=True)
    consulted = UserMinimalSerializer(many=True, read_only=True)
    informed = UserMinimalSerializer(many=True, read_only=True)
    
    class Meta:
        model = Activity
        fields = [
            'id', 'project', 'project_name', 'name', 'description',
            'responsible', 'accountable', 'consulted', 'informed',
            'status', 'priority', 'is_complete', 'deadline',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'is_complete', 'created_at', 'updated_at']


# MILESTONE SERIALIZERS
class MilestoneSerializer(serializers.ModelSerializer):
    activity_name = serializers.CharField(source='activity.name', read_only=True)
    assigned_to = UserMinimalSerializer(read_only=True)
    assigned_to_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        source='assigned_to',
        write_only=True,
        required=False,
        allow_null=True
    )
    
    class Meta:
        model = Milestone
        fields = [
            'id', 'activity', 'activity_name', 'title', 'description',
            'assigned_to', 'assigned_to_id', 'status', 'priority',
            'due_date', 'is_completed', 'completed_at', 'created_at'
        ]
        read_only_fields = ['id', 'is_completed', 'completed_at', 'created_at']


# COMMENT SERIALIZERS
class ActivityCommentSerializer(serializers.ModelSerializer):
    user = UserMinimalSerializer(read_only=True)
    
    class Meta:
        model = ActivityComment
        fields = ['id', 'activity', 'user', 'content', 'created_at', 'updated_at']
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']


class MilestoneCommentSerializer(serializers.ModelSerializer):
    user = UserMinimalSerializer(read_only=True)
    
    class Meta:
        model = MilestoneComment
        fields = ['id', 'milestone', 'user', 'content', 'created_at']
        read_only_fields = ['id', 'user', 'created_at']


# DOCUMENT SERIALIZERS
class ActivityDocumentSerializer(serializers.ModelSerializer):
    uploaded_by = UserMinimalSerializer(read_only=True)
    activity_name = serializers.CharField(source='activity.name', read_only=True)
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = ActivityDocument
        fields = [
            'id', 'activity', 'activity_name', 'title', 'description',
            'document_type', 'file', 'file_url', 'file_size', 'mime_type',
            'external_url', 'uploaded_by', 'created_at'
        ]
        read_only_fields = ['id', 'uploaded_by', 'created_at']
    
    def get_file_url(self, obj):
        if obj.file:
            return obj.file.url
        return None