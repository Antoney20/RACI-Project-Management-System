from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Project, Activity, Milestone, ActivityComment, MilestoneComment, ActivityDocument, SupervisorReview, UserActivityPriority
from mint.models import Sprint
from employee.models import EmployeeContract

User = get_user_model()



class UserMinimalSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    payroll_number = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'full_name',
            'gender',
            'role',
            'position',
            'department',
            'profile_image',
            'payroll_number',
        ]

    def get_payroll_number(self, obj):
        contract = obj.contracts.filter(is_current=True).first()
        return contract.payroll_number if contract else None


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
    sprint_name = serializers.CharField(source='sprint.name', read_only=True)
    
    class Meta:
        model = Project
        fields = [
            'id', 'name', 'description', 'sprint', 'sprint_name', 'status', 'priority', 'deliverables',
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
    order = serializers.IntegerField(read_only=False, required=False)

    class Meta:
        model = Activity
        fields = [
            'id', 'project_id', 'name', 'description', 'type', 'order',         
            'responsible_id', 'accountable_id', 'consulted_ids', 'informed_ids',
            'status', 'priority', 'deadline', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

class ActivityListSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source='project.name', read_only=True)
    responsible = UserMinimalSerializer(read_only=True)
    informed = UserMinimalSerializer(read_only=True, many=True)
    consulted = UserMinimalSerializer(read_only=True, many=True)
    accountable = UserMinimalSerializer(read_only=True)
    milestone_count = serializers.SerializerMethodField()
    type = serializers.CharField(read_only=True)  
    order = serializers.IntegerField(read_only=False, required=False)                   

    class Meta:
        model = Activity
        fields = [
            'id', 'project', 'project_name', 'name', 'responsible', 'accountable',
            'consulted', 'informed', 'status', 'priority', 'is_complete',
            'deadline', 'milestone_count', 'created_at', 'type'  , 'order'       
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
    type = serializers.CharField(read_only=True)   
    order = serializers.IntegerField(read_only=False, required=False)                  

    class Meta:
        model = Activity
        fields = [
            'id', 'project', 'project_name', 'name', 'description', 'type',  'order',    
            'responsible', 'accountable', 'consulted', 'informed',
            'status', 'priority', 'is_complete', 'deadline',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'is_complete', 'created_at', 'updated_at']




class UserActivityPrioritySerializer(serializers.ModelSerializer):
    activity_name = serializers.CharField(source='activity.name', read_only=True)
    project_name = serializers.CharField(source='activity.project.name', read_only=True)
    
    class Meta:
        model = UserActivityPriority
        fields = ['id', 'activity', 'activity_name', 'project_name', 'priority_order', 'created_at']
        read_only_fields = ['id', 'created_at']


class ReorderSerializer(serializers.Serializer):
    """Reorder request: {"activity_id": "uuid", "new_order": 1}"""
    activity_id = serializers.UUIDField(required=True)
    new_order = serializers.IntegerField(min_value=1, required=True)

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
    
  
  
  
class SupervisorReviewSerializer(serializers.ModelSerializer):
    # Activity details
    activity_name = serializers.CharField(source='activity.name', read_only=True)
    activity_type = serializers.CharField(source='activity.get_type_display', read_only=True)
    activity_status = serializers.CharField(source='activity.get_status_display', read_only=True)
    activity_priority = serializers.CharField(source='activity.get_priority_display', read_only=True)
    activity_deadline = serializers.DateTimeField(source='activity.deadline', read_only=True)
    
    project_id = serializers.UUIDField(source='activity.project.id', read_only=True)
    project_name = serializers.CharField(source='activity.project.name', read_only=True)
    
    # Responsible person
    responsible = UserMinimalSerializer(source='activity.responsible', read_only=True)
    
    reviewer_details = UserMinimalSerializer(source='reviewer', read_only=True)
    
    review_level_display = serializers.CharField(source='get_review_level_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = SupervisorReview
        fields = [
            'id', 'activity', 'activity_name', 'activity_type', 'activity_status',
            'activity_priority', 'activity_deadline', 'project_id', 'project_name',
            'responsible', 'reviewer', 'reviewer_details', 'review_level',
            'review_level_display', 'status', 'status_display', 
            'is_supervisor_approved', 'supervisor_approved_at', 'move_to_admin',
            'is_admin_approved', 'admin_approved_at', 'notes', 'started_at',
            'completed_at', 'is_complete', 'created_at', 'updated_at'
        ]
        read_only_fields = (
            'id', 'started_at', 'completed_at', 'supervisor_approved_at',
            'admin_approved_at', 'created_at', 'updated_at', 'is_complete'
        )  
  
  
  