from django.shortcuts import render

# Create your views here.
from rest_framework.decorators import action
from rest_framework.viewsets import ModelViewSet
from .models import Project, Task, Milestone, LeaveRequest, LeaveAllocation
from .serializers import (
    ProjectListSerializer, ProjectDetailSerializer, TaskListSerializer,
    TaskDetailSerializer, MilestoneSerializer, LeaveRequestSerializer,
    LeaveAllocationSerializer
)
from django.utils import timezone
from rest_framework.permissions import AllowAny, IsAuthenticated



class LeaveRequestViewSet(ModelViewSet):
    """Leave request management"""
    permission_classes = [IsAuthenticated]
    serializer_class = LeaveRequestSerializer
    filter_backends = ['django_filters.rest_framework.DjangoFilterBackend']
    filterset_fields = ['status', 'leave_type', 'user']

    def get_queryset(self):
        user = self.request.user
        if user.is_supervisor() or user.is_admin():
            return LeaveRequest.objects.all()
        return LeaveRequest.objects.filter(user=user)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        leave_request = self.get_object()
        if not (request.user.is_supervisor() or request.user.is_admin()):
            return Response({
                'success': False,
                'message': 'You do not have permission to approve leave requests.'
            }, status=status.HTTP_403_FORBIDDEN)

        leave_request.status = 'approved'
        leave_request.approved_by = request.user
        leave_request.approved_at = timezone.now()
        leave_request.save()

        return Response({
            'success': True,
            'message': 'Leave request approved.',
            'data': LeaveRequestSerializer(leave_request).data
        })

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        leave_request = self.get_object()
        if not (request.user.is_supervisor() or request.user.is_admin()):
            return Response({
                'success': False,
                'message': 'You do not have permission to reject leave requests.'
            }, status=status.HTTP_403_FORBIDDEN)

        leave_request.status = 'rejected'
        leave_request.rejection_reason = request.data.get('reason', '')
        leave_request.save()

        return Response({
            'success': True,
            'message': 'Leave request rejected.',
            'data': LeaveRequestSerializer(leave_request).data
        })



class ProjectViewSet(ModelViewSet):
    """Project CRUD operations"""
    permission_classes = [IsAuthenticated]
    filter_backends = ['django_filters.rest_framework.DjangoFilterBackend']
    filterset_fields = ['status', 'owner']
    search_fields = ['name', 'description']

    def get_queryset(self):
        user = self.request.user
        if user.is_admin():
            return Project.objects.all()
        return Project.objects.filter(owner=user) | Project.objects.filter(collaborators=user)

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ProjectDetailSerializer
        return ProjectListSerializer

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=['post'])
    def add_collaborator(self, request, pk=None):
        project = self.get_object()
        user_id = request.data.get('user_id')
        try:
            user = CustomUser.objects.get(id=user_id)
            project.collaborators.add(user)
            return Response({
                'success': True,
                'message': f'{user.full_name} added as collaborator.'
            })
        except CustomUser.DoesNotExist:
            return Response({
                'success': False,
                'message': 'User not found.'
            }, status=status.HTTP_404_NOT_FOUND)


class TaskViewSet(ModelViewSet):
    """Task CRUD operations"""
    permission_classes = [IsAuthenticated]
    filter_backends = ['django_filters.rest_framework.DjangoFilterBackend']
    filterset_fields = ['project', 'status', 'priority']

    def get_queryset(self):
        return Task.objects.filter(project__collaborators=self.request.user) | \
               Task.objects.filter(project__owner=self.request.user)

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return TaskDetailSerializer
        return TaskListSerializer


class MilestoneViewSet(ModelViewSet):
    """Milestone CRUD operations"""
    permission_classes = [IsAuthenticated]
    serializer_class = MilestoneSerializer

    def get_queryset(self):
        return Milestone.objects.filter(project__collaborators=self.request.user) | \
               Milestone.objects.filter(project__owner=self.request.user)

