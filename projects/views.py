from rest_framework import status
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied, ValidationError
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from django.utils import timezone

from .models import Sprint, Project, ProjectMilestone, ProjectMember, ProjectMaterial, ProjectComment
from .serializers import (
    SprintSerializer, ProjectListSerializer, ProjectDetailSerializer,
    ProjectMilestoneSerializer, ProjectMemberSerializer,
    ProjectMaterialSerializer, ProjectCommentSerializer
)


class SprintViewSet(ModelViewSet):
    """
    Sprint/Timeline management
    
    Access:
    - Admin/Office Admin: Full access
    - Supervisor: View all, create/update sprints in their department
    - Staff: View only
    """
    permission_classes = [IsAuthenticated]
    serializer_class = SprintSerializer

    
    def get_queryset(self):
        user = self.request.user
        
        if user.is_admin() or user.is_office_admin():
            data = Sprint.objects.all()

            return data
        
        if user.is_supervisor():
            return Sprint.objects.all()
        
        # Staff can view all sprints
        return Sprint.objects.all()
    
    def perform_create(self, serializer):
        user = self.request.user
        if not (user.is_admin() or user.is_office_admin() or user.is_supervisor()):
            raise PermissionDenied("Only admins and supervisors can create sprints.")
        serializer.save()
    
    def perform_update(self, serializer):
        user = self.request.user
        if not (user.is_admin() or user.is_office_admin() or user.is_supervisor()):
            raise PermissionDenied("Only admins and supervisors can update sprints.")
        serializer.save()
    
    def perform_destroy(self, instance):
        if not (self.request.user.is_admin() or self.request.user.is_office_admin()):
            raise PermissionDenied("Only admins can delete sprints.")
        instance.delete()
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get all active sprints"""
        sprints = self.get_queryset()
        serializer = self.get_serializer(sprints, many=True)
        return Response({'success': True, 'data': serializer.data})


class ProjectViewSet(ModelViewSet):
    """
    Project management with RACI-based visibility
    
    Visibility Rules:
    - Admin: All projects
    - Office Admin: All projects in department
    - Supervisor: Projects where assigned (any RACI role)
    - Staff: Projects where assigned
    - External: Projects where Consulted/Informed
    """
    permission_classes = [IsAuthenticated]
    # filter_backends = [DjangoFilterBackend]
    # filterset_fields = ['status', 'priority', 'sprint', 'accountable_person']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ProjectListSerializer
        return ProjectDetailSerializer
    
    def get_queryset(self):
        user = self.request.user
        
        # Admin sees everything
        if user.is_admin():
            return Project.objects.select_related('accountable_person', 'sprint', 'created_by')
        
        # Office admin sees department projects
        if user.is_office_admin():
            return Project.objects.filter(
                Q(accountable_person__department=user.department) |
                Q(members__user=user)
            ).distinct().select_related('accountable_person', 'sprint', 'created_by')
        
        # Supervisor/Staff/External see assigned projects
        return Project.objects.filter(
            Q(accountable_person=user) |
            Q(members__user=user)
        ).distinct().select_related('accountable_person', 'sprint', 'created_by')
    
    def perform_create(self, serializer):
        user = self.request.user
        if not (user.is_admin() or user.is_office_admin() or user.is_supervisor()):
            raise PermissionDenied("Only admins and supervisors can create projects.")
        serializer.save()
    
    def perform_update(self, serializer):
        user = self.request.user
        project = self.get_object()
        
        # Only admins, office admins, or accountable person can update
        if not (user.is_admin() or user.is_office_admin() or project.accountable_person == user):
            raise PermissionDenied("Only project accountable person or admins can update this project.")
        
        serializer.save()
    
    def perform_destroy(self, instance):
        user = self.request.user
        if not (user.is_admin() or user.is_office_admin()):
            raise PermissionDenied("Only admins can delete projects.")
        instance.delete()
    
    @action(detail=False, methods=['get'])
    def my_projects(self, request):
        """Get projects where user is involved"""
        user = request.user
        projects = Project.objects.filter(
            Q(accountable_person=user) |
            Q(members__user=user)
        ).distinct()
        serializer = self.get_serializer(projects, many=True)
        return Response({'success': True, 'data': serializer.data})
    
    @action(detail=False, methods=['get'])
    def overdue(self, request):
        """Get overdue projects"""
        today = timezone.now().date()
        projects = self.get_queryset().filter(
            end_date__lt=today,
            status__in=['not_started', 'in_progress', 'on_hold']
        )
        serializer = self.get_serializer(projects, many=True)
        return Response({'success': True, 'data': serializer.data})
    
    @action(detail=True, methods=['post'])
    def update_progress(self, request, pk=None):
        """Update project progress percentage"""
        project = self.get_object()
        user = request.user
        
        if not (user.is_admin() or user.is_office_admin() or project.accountable_person == user):
            raise PermissionDenied("Only accountable person or admins can update progress.")
        
        progress = request.data.get('progress_percentage')
        if progress is None or not (0 <= int(progress) <= 100):
            raise ValidationError("Progress must be between 0 and 100.")
        
        project.progress_percentage = progress
        project.save()
        
        serializer = self.get_serializer(project)
        return Response({
            'success': True,
            'message': 'Progress updated successfully.',
            'data': serializer.data
        })


class ProjectMilestoneViewSet(ModelViewSet):
    """
    Milestone/subtask management
    
    Access: Same as parent project
    """
    permission_classes = [IsAuthenticated]
    serializer_class = ProjectMilestoneSerializer

    def get_queryset(self):
        user = self.request.user
        print("***** ", user)
        
        if user.is_admin():
            return ProjectMilestone.objects.all()
        
        # Filter by accessible projects
        accessible_projects = Project.objects.filter(
            Q(accountable_person=user) |
            Q(members__user=user)
        ).values_list('id', flat=True)
        
        return ProjectMilestone.objects.filter(
            project_id__in=accessible_projects
        ).select_related('project', 'assigned_to')
    
    def perform_create(self, serializer):
        project = serializer.validated_data['project']
        print("project", project)
        user = self.request.user
        
        if not (user.is_admin() or user.is_office_admin() or project.accountable_person == user):
            raise PermissionDenied("Only project accountable person or admins can add milestones.")
        
        serializer.save()
    
    def perform_update(self, serializer):
        milestone = self.get_object()
        user = self.request.user
        
        if not (user.is_admin() or user.is_office_admin() or 
                milestone.project.accountable_person == user or 
                milestone.assigned_to == user):
            raise PermissionDenied("Only assigned person or project owner can update this milestone.")
        
        serializer.save()
    
    @action(detail=True, methods=['post'])
    def mark_complete(self, request, pk=None):
        """Mark milestone as completed"""
        milestone = self.get_object()
        milestone.status = 'completed'
        milestone.completed_at = timezone.now()
        milestone.save()
        
        serializer = self.get_serializer(milestone)
        return Response({
            'success': True,
            'message': 'Milestone marked as complete.',
            'data': serializer.data
        })


class ProjectMemberViewSet(ModelViewSet):
    """
    Project team member management
    
    Access: Project accountable person and admins
    """
    permission_classes = [IsAuthenticated]
    serializer_class = ProjectMemberSerializer
    # filter_backends = [DjangoFilterBackend]
    # filterset_fields = ['project', 'user', 'raci_role']
    
    def get_queryset(self):
        user = self.request.user
        
        if user.is_admin():
            return ProjectMember.objects.select_related('project', 'user', 'assigned_by')
        
        accessible_projects = Project.objects.filter(
            Q(accountable_person=user) |
            Q(members__user=user)
        ).values_list('id', flat=True)
        
        return ProjectMember.objects.filter(
            project_id__in=accessible_projects
        ).select_related('project', 'user', 'assigned_by')
    
    def perform_create(self, serializer):
        project = serializer.validated_data['project']
        user = self.request.user
        
        if not (user.is_admin() or user.is_office_admin() or project.accountable_person == user):
            raise PermissionDenied("Only project accountable person or admins can add members.")
        
        serializer.save()
    
    def perform_destroy(self, instance):
        user = self.request.user
        if not (user.is_admin() or user.is_office_admin() or instance.project.accountable_person == user):
            raise PermissionDenied("Only project accountable person or admins can remove members.")
        instance.delete()


class ProjectMaterialViewSet(ModelViewSet):
    """Project materials (files/links) management"""
    permission_classes = [IsAuthenticated]
    serializer_class = ProjectMaterialSerializer
    # filter_backends = [DjangoFilterBackend]
    # filterset_fields = ['project', 'material_type']
    
    def get_queryset(self):
        user = self.request.user
        
        if user.is_admin():
            return ProjectMaterial.objects.select_related('project', 'uploaded_by')
        
        accessible_projects = Project.objects.filter(
            Q(accountable_person=user) |
            Q(members__user=user)
        ).values_list('id', flat=True)
        
        return ProjectMaterial.objects.filter(
            project_id__in=accessible_projects
        ).select_related('project', 'uploaded_by')
    
    def perform_create(self, serializer):
        project = serializer.validated_data['project']
        user = self.request.user
        
        if not (user.is_admin() or user.is_office_admin() or 
                project.accountable_person == user or
                project.members.filter(user=user).exists()):
            raise PermissionDenied("Only project members can upload materials.")
        
        serializer.save()


class ProjectCommentViewSet(ModelViewSet):
    """Project comments with threading"""
    permission_classes = [IsAuthenticated]
    serializer_class = ProjectCommentSerializer
    # filter_backends = [DjangoFilterBackend]
    # filterset_fields = ['project', 'parent']
    
    def get_queryset(self):
        user = self.request.user
        
        if user.is_admin():
            return ProjectComment.objects.select_related('project', 'user', 'parent')
        
        accessible_projects = Project.objects.filter(
            Q(accountable_person=user) |
            Q(members__user=user)
        ).values_list('id', flat=True)
        
        return ProjectComment.objects.filter(
            project_id__in=accessible_projects
        ).select_related('project', 'user', 'parent')
    
    def perform_create(self, serializer):
        project = serializer.validated_data['project']
        user = self.request.user
        
        if not (user.is_admin() or user.is_office_admin() or 
                project.accountable_person == user or
                project.members.filter(user=user).exists()):
            raise PermissionDenied("Only project members can comment.")
        
        serializer.save()
    
    def perform_update(self, serializer):
        comment = self.get_object()
        if comment.user != self.request.user and not self.request.user.is_admin():
            raise PermissionDenied("You can only edit your own comments.")
        serializer.save()
    
    def perform_destroy(self, instance):
        if instance.user != self.request.user and not self.request.user.is_admin():
            raise PermissionDenied("You can only delete your own comments.")
        instance.delete()