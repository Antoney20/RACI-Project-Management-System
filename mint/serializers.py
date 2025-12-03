from rest_framework import serializers

from mint.models import LeaveAllocation, LeaveRequest, Milestone, Project, ProjectDocument, Task, TaskAttachment, TaskComment, TaskRACIAssignment





class LeaveRequestSerializer(serializers.ModelSerializer):
    user_details = serializers.SerializerMethodField(read_only=True)
    approved_by_details = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = LeaveRequest
        fields = [
            'id', 'user', 'user_details', 'leave_type', 'status',
            'start_date', 'end_date', 'num_days', 'reason', 'notes',
            'approved_by', 'approved_by_details', 'approved_at',
            'rejection_reason', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'user', 'status', 'approved_by', 'approved_at',
            'rejection_reason', 'created_at', 'updated_at'
        ]
    
    def get_user_details(self, obj):
        return {
            'id': str(obj.user.id),
            'username': obj.user.username,
            'email': obj.user.email,
            'full_name': obj.user.full_name
        }
    
    def get_approved_by_details(self, obj):
        if obj.approved_by:
            return {
                'id': str(obj.approved_by.id),
                'username': obj.approved_by.username,
                'full_name': obj.approved_by.full_name
            }
        return None
    
    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class LeaveApprovalSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=['approve', 'reject'])
    rejection_reason = serializers.CharField(required=False, allow_blank=True)



class LeaveAllocationSerializer(serializers.ModelSerializer):
    user_details = serializers.SerializerMethodField()
    annual_remaining = serializers.IntegerField(read_only=True)
    sick_remaining = serializers.IntegerField(read_only=True)
    special_remaining = serializers.IntegerField(read_only=True)

    class Meta:
        model = LeaveAllocation
        fields = [
            'id', 'user', 'user_details', 'year',
            'annual_leave_days', 'annual_used', 'annual_remaining',
            'sick_leave_days', 'sick_used', 'sick_remaining',
            'special_leave_days', 'special_used', 'special_remaining',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'annual_remaining', 'sick_remaining', 'special_remaining', 'created_at', 'updated_at']

    def get_user_details(self, obj):
        return {'id': str(obj.user.id), 'username': obj.user.username, 'email': obj.user.email, 'full_name': obj.user.full_name}

    def validate(self, data):
        annual_used = data.get('annual_used', self.instance.annual_used if self.instance else 0)
        annual_total = data.get('annual_leave_days', self.instance.annual_leave_days if self.instance else 20)
        if annual_used > annual_total:
            raise serializers.ValidationError('Annual used cannot exceed allocated days')
        return data




class ProjectListSerializer(serializers.ModelSerializer):
    owner_name = serializers.CharField(source='owner.full_name', read_only=True)
    collaborator_count = serializers.SerializerMethodField()
    task_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Project
        fields = [
            'id', 'name', 'slug', 'owner', 'owner_name', 
            'status', 'progress', 'start_date', 'end_date',
            'collaborator_count', 'task_count', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_collaborator_count(self, obj):
        return obj.collaborators.count()
    
    def get_task_count(self, obj):
        return obj.tasks.count()


class ProjectDetailSerializer(serializers.ModelSerializer):
    owner_name = serializers.CharField(source='owner.full_name', read_only=True)
    collaborators_list = serializers.SerializerMethodField()
    milestones_count = serializers.SerializerMethodField()
    tasks_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Project
        fields = [
            'id', 'name', 'slug', 'description', 'owner', 'owner_name',
            'collaborators', 'collaborators_list', 'status', 'progress',
            'start_date', 'end_date', 'milestones_count', 'tasks_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_collaborators_list(self, obj):
        return [
            {
                'id': str(c.id),
                'username': c.username,
                'email': c.email,
                'full_name': c.full_name
            }
            for c in obj.collaborators.all()
        ]
    
    def get_milestones_count(self, obj):
        return obj.milestones.count()
    
    def get_tasks_count(self, obj):
        return obj.tasks.count()


class MilestoneSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source='project.name', read_only=True)
    
    class Meta:
        model = Milestone
        fields = [
            'id', 'project', 'project_name', 'title', 'description',
            'due_date', 'is_completed', 'completed_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class TaskRACIAssignmentSerializer(serializers.ModelSerializer):
    user_details = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = TaskRACIAssignment
        fields = ['id', 'task', 'user', 'user_details', 'raci_role', 'created_at']
        read_only_fields = ['id', 'created_at']
    
    def get_user_details(self, obj):
        return {
            'id': str(obj.user.id),
            'username': obj.user.username,
            'email': obj.user.email,
            'full_name': obj.user.full_name
        }


class TaskCommentSerializer(serializers.ModelSerializer):
    user_details = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = TaskComment
        fields = ['id', 'task', 'user', 'user_details', 'content', 'created_at', 'updated_at']
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']
    
    def get_user_details(self, obj):
        return {
            'id': str(obj.user.id),
            'username': obj.user.username,
            'full_name': obj.user.full_name
        }
    
    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class TaskAttachmentSerializer(serializers.ModelSerializer):
    uploader_name = serializers.CharField(source='uploaded_by.full_name', read_only=True)
    
    class Meta:
        model = TaskAttachment
        fields = [
            'id', 'task', 'file_name', 'file', 'file_size',
            'mime_type', 'uploaded_by', 'uploader_name', 'created_at'
        ]
        read_only_fields = ['id', 'uploaded_by', 'created_at', 'file_size']
    
    def create(self, validated_data):
        validated_data['uploaded_by'] = self.context['request'].user
        return super().create(validated_data)


class TaskDetailSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source='project.name', read_only=True)
    raci_assignments = TaskRACIAssignmentSerializer(many=True, read_only=True)
    comments = TaskCommentSerializer(many=True, read_only=True)
    attachments = TaskAttachmentSerializer(many=True, read_only=True)
    
    class Meta:
        model = Task
        fields = [
            'id', 'project', 'project_name', 'title', 'description',
            'status', 'priority', 'progress', 'start_date', 'due_date',
            'completed_at', 'raci_assignments', 'comments', 'attachments',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'completed_at']


class TaskListSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source='project.name', read_only=True)
    assigned_users = serializers.SerializerMethodField()
    
    class Meta:
        model = Task
        fields = [
            'id', 'project', 'project_name', 'title', 'status',
            'priority', 'progress', 'due_date', 'assigned_users', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_assigned_users(self, obj):
        users = obj.raci_assignments.values_list('user__username', flat=True).distinct()
        return list(users)


class ProjectDocumentSerializer(serializers.ModelSerializer):
    uploader_name = serializers.CharField(source='uploaded_by.full_name', read_only=True)
    
    class Meta:
        model = ProjectDocument
        fields = [
            'id', 'project', 'title', 'description', 'document_type',
            'file', 'file_size', 'mime_type', 'external_url',
            'uploaded_by', 'uploader_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'uploaded_by', 'created_at', 'updated_at', 'file_size']
    
    def create(self, validated_data):
        validated_data['uploaded_by'] = self.context['request'].user
        return super().create(validated_data)

