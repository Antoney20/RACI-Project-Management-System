from rest_framework import serializers

from mint.models import (  Sprint
# MilestoneComment,  Milestones, Project, ProjectComment, ProjectDocument, ProjectNote, ProjectReview, ProjectReviewComment, PublicHoliday, Task, TaskAttachment, TaskComment, RACIAssignment)
)

from django.contrib.auth import get_user_model


User = get_user_model()

class UserMinimalSerializer(serializers.ModelSerializer):
    """Lightweight user info for nested relations"""
    full_name = serializers.CharField(read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'full_name', 'role', 'department',  'position', 'profile_image']



# class LeaveRequestSerializer(serializers.ModelSerializer):
#     user_details = serializers.SerializerMethodField(read_only=True)
#     approved_by_details = serializers.SerializerMethodField(read_only=True)
#     supervisors_details = serializers.SerializerMethodField(read_only=True)
#     programme_manager_details = serializers.SerializerMethodField(read_only=True)
#     leave_type_display = serializers.CharField(source='get_leave_type_display', read_only=True)
#     status_display = serializers.CharField(source='get_status_display', read_only=True)
    
#     class Meta:
#         model = LeaveRequest
#         fields = [
#             'id', 'user', 'user_details', 'position', 'leave_type', 'leave_type_display',
#             'leave_type_other', 'status', 'status_display',
#             'start_date', 'end_date', 'num_days', 'reason', 'notes',
#             'supervisors', 'supervisors_details',
#             'approved_by', 'approved_by_details', 'approved_at',
#             'rejection_reason',
#             'programme_manager_approved_by', 'programme_manager_details',
#             'programme_manager_approved', 'programme_manager_approved_at',
#             'created_at', 'updated_at'
#         ]
#         read_only_fields = [
#             'id', 'user', 'status', 'approved_by', 'approved_at',
#             'rejection_reason', 'programme_manager_approved_by',
#             'programme_manager_approved_at',
#             'created_at', 'updated_at', 'leave_type_display', 'status_display'
#         ]
    
#     def get_user_details(self, obj):
#         return {
#             'id': str(obj.user.id),
#             'username': obj.user.username,
#             'email': obj.user.email,
#             'full_name': obj.user.full_name,
#             'department' : obj.user.department,
#             'role' : obj.user.role,
#             'profile_image': obj.user.profile_image.url if obj.user.profile_image else None,
#         }
    
#     def get_approved_by_details(self, obj):
#         if obj.approved_by:
#             return {
#                 'id': str(obj.approved_by.id),
#                 'username': obj.approved_by.username,
#                 'full_name': obj.approved_by.full_name,
#                 'email': obj.approved_by.email
#             }
#         return None
    
#     def get_supervisors_details(self, obj):
#         supervisors = obj.supervisors.all()
#         return [
#             {
#                 'id': str(supervisor.id),
#                 'username': supervisor.username,
#                 'full_name': supervisor.full_name,
#                 'email': supervisor.email
#             }
#             for supervisor in supervisors
#         ]
    
#     def get_programme_manager_details(self, obj):
#         if obj.programme_manager_approved_by:
#             return {
#                 'id': str(obj.programme_manager_approved_by.id),
#                 'username': obj.programme_manager_approved_by.username,
#                 'full_name': obj.programme_manager_approved_by.full_name,
#                 'email': obj.programme_manager_approved_by.email
#             }
#         return None
    
#     def create(self, validated_data):
#         validated_data['user'] = self.context['request'].user
#         return super().create(validated_data)

# # class LeaveApprovalSerializer(serializers.Serializer):
#     action = serializers.ChoiceField(choices=['approve', 'reject'])
#     rejection_reason = serializers.CharField(required=False, allow_blank=True)

# class ProgrammeManagerApprovalSerializer(serializers.Serializer):
#     """Serializer for programme manager approval after leave has been taken"""
#     programme_manager_approved = serializers.BooleanField()
    
#     def validate_programme_manager_approved(self, value):
#         if not isinstance(value, bool):
#             raise serializers.ValidationError("Must be a boolean value")
#         return value

# class LeaveAllocationSerializer(serializers.ModelSerializer):
#     user_details = serializers.SerializerMethodField()
#     annual_remaining = serializers.IntegerField(read_only=True)
#     sick_remaining = serializers.IntegerField(read_only=True)
#     maternity_remaining = serializers.IntegerField(read_only=True)
#     paternity_remaining = serializers.IntegerField(read_only=True)
#     compassionate_remaining = serializers.IntegerField(read_only=True)
#     study_remaining = serializers.IntegerField(read_only=True)
#     other_remaining = serializers.IntegerField(read_only=True)
    
#     class Meta:
#         model = LeaveAllocation
#         fields = [
#             'id', 'user', 'user_details', 'position', 'year',

#             'annual_leave_days', 'annual_used', 'annual_remaining',
#             'annual_left',

#             'sick_leave_days', 'sick_used', 'sick_remaining',

#             'maternity_leave_days', 'maternity_used', 'maternity_remaining',

#             'paternity_leave_days', 'paternity_used', 'paternity_remaining',

#             'compassionate_leave_days', 'compassionate_used', 'compassionate_remaining',

#             'study_leave_days', 'study_used', 'study_remaining',

#             'other_leave_days', 'other_used', 'other_remaining',

#             'carryover_expiry_date',
#             'created_at', 'updated_at'
#         ]
#         read_only_fields = [
#             'id', 'annual_remaining', 'sick_remaining', 'maternity_remaining',
#             'paternity_remaining', 'compassionate_remaining', 'study_remaining',
#             'other_remaining', 'created_at', 'updated_at'
#         ]

#     def get_user_details(self, obj):
#         return {
#             'id': str(obj.user.id),
#             'username': obj.user.username,
#             'email': obj.user.email,
#             'full_name': obj.user.full_name,
#         }

#     def validate(self, data):
#         annual_used = data.get('annual_used', self.instance.annual_used if self.instance else 0)
#         annual_total = data.get('annual_leave_days', self.instance.annual_leave_days if self.instance else 20)

#         if annual_used > annual_total:
#             raise serializers.ValidationError('Annual used cannot exceed allocated days')

#         sick_used = data.get('sick_used', self.instance.sick_used if self.instance else 0)
#         sick_total = data.get('sick_leave_days', self.instance.sick_leave_days if self.instance else 10)

#         if sick_used > sick_total:
#             raise serializers.ValidationError('Sick used cannot exceed allocated days')

#         maternity_used = data.get('maternity_used', self.instance.maternity_used if self.instance else 0)
#         maternity_total = data.get('maternity_leave_days', self.instance.maternity_leave_days if self.instance else 0)

#         if maternity_used > maternity_total:
#             raise serializers.ValidationError('Maternity used cannot exceed allocated days')

#         paternity_used = data.get('paternity_used', self.instance.paternity_used if self.instance else 0)
#         paternity_total = data.get('paternity_leave_days', self.instance.paternity_leave_days if self.instance else 0)

#         if paternity_used > paternity_total:
#             raise serializers.ValidationError('Paternity used cannot exceed allocated days')

#         compassionate_used = data.get('compassionate_used', self.instance.compassionate_used if self.instance else 0)
#         compassionate_total = data.get('compassionate_leave_days', self.instance.compassionate_leave_days if self.instance else 0)

#         if compassionate_used > compassionate_total:
#             raise serializers.ValidationError('Compassionate used cannot exceed allocated days')

#         study_used = data.get('study_used', self.instance.study_used if self.instance else 0)
#         study_total = data.get('study_leave_days', self.instance.study_leave_days if self.instance else 0)

#         if study_used > study_total:
#             raise serializers.ValidationError('Study used cannot exceed allocated days')

#         other_used = data.get('other_used', self.instance.other_used if self.instance else 0)
#         other_total = data.get('other_leave_days', self.instance.other_leave_days if self.instance else 0)

#         if other_used > other_total:
#             raise serializers.ValidationError('Other used cannot exceed allocated days')

#         return data
#     # def validate(self, data):
#     #     annual_used = data.get('annual_used', self.instance.annual_used if self.instance else 0)
#     #     annual_total = data.get('annual_leave_days', self.instance.annual_leave_days if self.instance else 20)

#     #     if annual_used > annual_total:
#     #         raise serializers.ValidationError('Annual used cannot exceed allocated days')

#     #     return data

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


# class ProjectCreateSerializer(serializers.ModelSerializer):
#     accountable_person_id = serializers.PrimaryKeyRelatedField(
#         queryset=User.objects.all(),
#         source='owner',
#         write_only=True
#     )
#     sprint_id = serializers.PrimaryKeyRelatedField(
#         queryset=Sprint.objects.all(),
#         source='sprint',
#         write_only=True,
#         required=False,
#         allow_null=True
#     )

#     class Meta:
#         model = Project
#         fields = [
#             'id',
#             'name',
#             'description',
#             'accountable_person_id',
#             'sprint_id',
#             'priority',
#             'status',
#             'start_date',
#             'end_date',
#             'progress',
#             'created_at',
#         ]
#         read_only_fields = ['id', 'created_at']


# class ProjectCreateSerializer(serializers.ModelSerializer):
#     accountable_person_id = serializers.PrimaryKeyRelatedField(
#         queryset=User.objects.all(),
#         source='owner',
#         write_only=True
#     )
#     sprint_id = serializers.PrimaryKeyRelatedField(
#         queryset=Sprint.objects.all(),
#         source='sprint',
#         write_only=True,
#         required=False,
#         allow_null=True
#     )
#     supervisor_ids = serializers.PrimaryKeyRelatedField(
#         queryset=User.objects.all(), 
#         source='supervisors',
#         many=True,
#         write_only=True,
#         required=False
#     )

#     class Meta:
#         model = Project
#         fields = [
#             'id',
#             'name',
#             'description',
#             'accountable_person_id',
#             'sprint_id',
#             'supervisor_ids',
#             'priority',
#             'status',
#             'start_date',
#             'end_date',
#             'progress',
#             'created_at',
#         ]
#         read_only_fields = ['id', 'created_at']

# class RAssignmentSerializer(serializers.ModelSerializer):
#     user = UserMinimalSerializer(read_only=True)
#     user_role = serializers.CharField(source='raci_role', read_only=True)
    
#     class Meta:
#         model = RACIAssignment
#         fields = ['id', 'user', 'user_role', 'created_at']
#         read_only_fields = ['id', 'created_at']


# class ProjectListSerializer(serializers.ModelSerializer):
#     owner_name = serializers.CharField(source='owner.full_name', read_only=True)
#     collaborator_count = serializers.SerializerMethodField()
#     milestone_count = serializers.SerializerMethodField()
#     document_count = serializers.SerializerMethodField()
#     owner = UserMinimalSerializer(read_only=True)
#     created_by = UserMinimalSerializer(read_only=True)
#     raci_assignments = RAssignmentSerializer(many=True, read_only=True)
#     # supervisors = UserMinimalSerializer(many=True, read_only=True)
#     supervisor_list = serializers.SerializerMethodField()
    
  
#     class Meta:
#         model = Project
#         fields = [
#             'id', 'name', 'owner', 'owner_name', 'created_by', 'supervisors', 'supervisor_list','description', 'priority',
#             'status', 'progress', 'start_date', 'end_date',
#             'collaborator_count', 'milestone_count', 'document_count',
#             'raci_assignments',
#             'created_at', 
#         ]
#         read_only_fields = ['id', 'created_at']
    
#     def get_collaborator_count(self, obj):
#         return obj.raci_assignments.values('user').distinct().count()

#     def get_milestone_count(self, obj):
#         return obj.proj_milestones.count() 

#     def get_document_count(self, obj):
#         return obj.documents.count()
    
#     def get_supervisor_list(self, obj):
#         """Return list of supervisor names"""
#         return obj.supervisor_list

# class MilestoneSerializer(serializers.ModelSerializer):
#     project_name = serializers.CharField(source='project.name', read_only=True)
    
#     class Meta:
#         model = Milestones  
#         fields = [
#             'id', 'project', 'project_name', 'title', 'description',
#             'due_date', 'is_completed', 'completed_at', 'created_at', 'updated_at'
#         ]
#         read_only_fields = ['id', 'created_at', 'updated_at']



# # class ProjectDocumentSerializer(serializers.ModelSerializer):
# #     uploaded_by_name = serializers.CharField(source='uploaded_by.full_name', read_only=True)
# #     file_url = serializers.SerializerMethodField()
    
# #     class Meta:
# #         model = ProjectDocument
# #         fields = [
# #             'id', 'project', 'title', 'description', 'document_type',
# #             'file', 'file_url', 'file_size', 'mime_type', 'external_url',
# #             'uploaded_by', 'uploaded_by_name', 'created_at', 'updated_at'
# #         ]
# #         read_only_fields = ['id', 'created_at', 'updated_at', 'file_url', 'uploaded_by'] 
    
# #     def get_file_url(self, obj):
# #         if obj.file:
# #             return obj.file.url
# #         return None


# class ProjectDocumentSerializer(serializers.ModelSerializer):
#     uploaded_by_name = serializers.CharField(source='uploaded_by.full_name', read_only=True)
#     file_url = serializers.SerializerMethodField()
    
#     # Project details
#     project_name = serializers.CharField(source='project.name', read_only=True)
#     project_status = serializers.CharField(source='project.status', read_only=True)
#     project_owner_name = serializers.CharField(source='project.owner.full_name', read_only=True)
    
#     class Meta:
#         model = ProjectDocument
#         fields = [
#             'id', 'project', 'project_name', 'project_status', 'project_owner_name',
#             'title', 'description', 'document_type',
#             'file', 'file_url', 'file_size', 'mime_type', 'external_url',
#             'uploaded_by', 'uploaded_by_name', 'created_at', 'updated_at'
#         ]
#         read_only_fields = ['id', 'created_at', 'updated_at', 'file_url', 'uploaded_by'] 
    
#     def get_file_url(self, obj):
#         if obj.file:
#             return obj.file.url
#         return None



# class RACIAssignmentSerializer(serializers.ModelSerializer):
#     user_details = serializers.SerializerMethodField(read_only=True)
#     project_details = serializers.SerializerMethodField(read_only=True)
    
#     class Meta:
#         model = RACIAssignment
#         fields = [
#             'id', 'project', 'project_details', 'user', 'user_details', 
#             'raci_role', 'created_at', 'updated_at'
#         ]
#         read_only_fields = ['id', 'created_at', 'updated_at']
    
#     def get_user_details(self, obj):
#         return {
#             'id': str(obj.user.id),
#             'username': obj.user.username,
#             'email': obj.user.email,
#             'full_name': obj.user.full_name
#         }
    
#     def get_project_details(self, obj):
#         return {
#             'id': str(obj.project.id),
#             'name': obj.project.name,
#         }

# class ProjectDetailSerializer(serializers.ModelSerializer):
#     owner_name = serializers.CharField(source='owner.full_name', read_only=True)
#     milestones = MilestoneSerializer(many=True, read_only=True)
#     documents = ProjectDocumentSerializer(many=True, read_only=True)
#     raci_assignments = RACIAssignmentSerializer(many=True, read_only=True)
#     supervisor_list = serializers.SerializerMethodField()
#     supervisors = UserMinimalSerializer(many=True, read_only=True)
    
#     class Meta:
#         model = Project
#         fields = [
#             'id', 'name',  'description', 'owner', 'owner_name', 'supervisors', 'supervisor_list', 'priority',
#             'status', 'progress', 'notify_supervisor', 'comment_notify',
#             'start_date', 'end_date',  'created_at', 'updated_at', 'milestones', 'documents', 'raci_assignments'
#         ]
#         read_only_fields = ['id', 'created_at', 'updated_at']


#     def get_supervisor_list(self, obj):
#         """Return list of supervisor names"""
#         return obj.supervisor_list



# class ProjectCommentSerializer(serializers.ModelSerializer):
#     user = UserMinimalSerializer(read_only=True)
    
#     class Meta:
#         model = ProjectComment
#         fields = ['id', 'project', 'user', 'content', 'created_at', 'updated_at']
#         read_only_fields = ['id', 'user', 'created_at', 'updated_at']


# class ProjectNoteSerializer(serializers.ModelSerializer):
#     user = UserMinimalSerializer(read_only=True)
    
#     class Meta:
#         model = ProjectNote
#         fields = ['id', 'project', 'user', 'title', 'content', 'created_at', 'updated_at']
#         read_only_fields = ['id', 'user', 'created_at', 'updated_at']


# class MilestoneCommentSerializer(serializers.ModelSerializer):
#     user = UserMinimalSerializer(read_only=True)
    
#     class Meta:
#         model = MilestoneComment
#         fields = ['id', 'milestone', 'user', 'content', 'created_at']
#         read_only_fields = ['id', 'user', 'created_at']





# class ProjectReviewCommentSerializer(serializers.ModelSerializer):
#     user_name = serializers.CharField(source='user.full_name', read_only=True)
    
#     class Meta:
#         model = ProjectReviewComment
#         fields = ['id', 'review', 'user', 'user_name', 'comment', 
#                   'attachment_links', 'is_resolved', 'parent_comment', 
#                   'created_at', 'updated_at']
#         read_only_fields = ['user', 'created_at', 'updated_at']


# class ProjectReviewSerializer(serializers.ModelSerializer):
#     project_name = serializers.CharField(source='project.name', read_only=True)
#     project_owner = serializers.CharField(source='project.owner.full_name', read_only=True)
#     reviewer_name = serializers.CharField(source='reviewer.full_name', read_only=True)
#     comments = ProjectReviewCommentSerializer(many=True, read_only=True)
    
#     class Meta:
#         model = ProjectReview
#         fields = ['id', 'project', 'project_name', 'project_owner', 'status', 
#                   'reviewer', 'reviewer_name', 'review_summary', 'submitted_at', 
#                   'reviewed_at', 'is_closed', 'closed_at', 'created_by', 
#                   'created_at', 'updated_at', 'comments']
#         read_only_fields = ['created_by', 'submitted_at', 'reviewed_at', 
#                             'closed_at', 'created_at', 'updated_at']







































































# class CalendarEventSerializer(serializers.ModelSerializer):
#     user_name = serializers.SerializerMethodField()
#     project_name = serializers.SerializerMethodField()
#     milestone_title = serializers.SerializerMethodField()
#     color = serializers.SerializerMethodField()
    
#     class Meta:
#         model = CalendarEvent
#         fields = [
#             'id', 'title', 'description', 'event_type',
#             'start_date', 'end_date', 'all_day',
#             'user', 'user_name', 
#             'project', 'project_name',
#             'milestone', 'milestone_title',
#             'leave_request', 'is_public', 'color',
#             'created_at', 'updated_at'
#         ]
#         read_only_fields = ['id', 'created_at', 'updated_at']
    
#     def get_user_name(self, obj):
#         return obj.user.get_full_name() if obj.user else None
    
#     def get_project_name(self, obj):
#         return obj.project.name if obj.project else None
    
#     def get_milestone_title(self, obj):
#         return obj.milestone.title if obj.milestone else None
    
#     def get_color(self, obj):
#         if obj.color:
#             return obj.color
        
#         # Default colors by event type
#         colors = {
#             'leave': '#FF6B6B',
#             'project_deadline': '#4ECDC4',
#             'milestone': '#45B7D1',
#             'public_holiday': '#FFA07A',
#             'weekend': '#D3D3D3',
#             'meeting': '#95E1D3',
#             'other': '#A8E6CF',
#         }
#         return colors.get(obj.event_type, '#999999')


# class PublicHolidaySerializer(serializers.ModelSerializer):
#     class Meta:
#         model = PublicHoliday
#         fields = ['id', 'name', 'date', 'year', 'is_recurring', 'created_at']
#         read_only_fields = ['id', 'created_at']


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
#     # raci_assignments = TaskRACIAssignmentSerializer(many=True, read_only=True)
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




