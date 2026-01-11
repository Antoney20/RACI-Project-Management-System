from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q

from .models import Project, Activity, Milestone, ActivityComment, MilestoneComment, ActivityDocument
from .serializers import (
    ProjectCreateSerializer, ProjectListSerializer, ProjectDetailSerializer,
    ActivityCreateSerializer, ActivityListSerializer, ActivityDetailSerializer,
    MilestoneSerializer, ActivityCommentSerializer, MilestoneCommentSerializer,
    ActivityDocumentSerializer
)


class ProjectViewSet(viewsets.ModelViewSet):
    """
    Project CRUD operations with role-based access.
    - Created by user can view/edit their projects
    - Staff can see all projects
    """
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'priority']
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'start_date']
    ordering = ['-created_at']

    def get_queryset(self):
        """Filter projects based on user permissions"""
        user = self.request.user
        
        if user.is_staff:
            return Project.objects.all().select_related('created_by', 'sprint')
        
        # Users see projects they created
        return Project.objects.filter(
            created_by=user
        ).select_related('created_by', 'sprint')

    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'create':
            return ProjectCreateSerializer
        if self.action == 'retrieve':
            return ProjectDetailSerializer
        return ProjectListSerializer

    def perform_create(self, serializer):
        """Set the creator when creating a project"""
        serializer.save(created_by=self.request.user)

    def destroy(self, request, *args, **kwargs):
        """Only staff can delete projects"""
        if not request.user.is_staff:
            return Response(
                {
                    "success": False,
                    "message": "Only administrators can delete projects."
                },
                status=status.HTTP_403_FORBIDDEN
            )
        
        project = self.get_object()
        project_name = project.name
        self.perform_destroy(project)
        
        return Response(
            {
                "success": True,
                "message": f'Project "{project_name}" deleted successfully.'
            },
            status=status.HTTP_200_OK
        )


class ActivityViewSet(viewsets.ModelViewSet):
    """
    Activity CRUD operations with RACI role-based access.
    - Users with any RACI role (R/A/C/I) can view activities
    - Responsible/Accountable can edit
    - Staff can see all
    """
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'priority', 'project', 'is_complete']
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'deadline']
    ordering = ['-created_at']

    def get_queryset(self):
        """Filter activities based on user RACI roles"""
        user = self.request.user
        
        if user.is_staff:
            return Activity.objects.all().select_related(
                'project', 'responsible', 'accountable'
            ).prefetch_related('consulted', 'informed')
        
        # Users see activities where they have any RACI role
        return Activity.objects.filter(
            Q(responsible=user) | 
            Q(accountable=user) | 
            Q(consulted=user) | 
            Q(informed=user) 
        ).distinct().select_related(
            'project', 'responsible', 'accountable'
        ).prefetch_related('consulted', 'informed')

    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'create':
            return ActivityCreateSerializer
        if self.action == 'retrieve':
            return ActivityDetailSerializer
        return ActivityListSerializer

    @action(detail=True, methods=['post'], url_path='mark-complete')
    def mark_complete(self, request, pk=None):
        """Mark activity as completed"""
        activity = self.get_object()
        activity.status = 'completed'
        activity.save()
        
        return Response({
            'success': True,
            'message': 'Activity marked as complete',
            'is_complete': activity.is_complete
        })

    @action(detail=True, methods=['get', 'post'])
    def comments(self, request, pk=None):
        """Get all comments or create a new comment for an activity"""
        activity = self.get_object()
        
        if request.method == 'GET':
            comments = activity.comments.select_related('user').order_by('-created_at')
            serializer = ActivityCommentSerializer(comments, many=True)
            return Response(serializer.data)
        
        elif request.method == 'POST':
            serializer = ActivityCommentSerializer(
                data={'activity': activity.id, 'content': request.data.get('content')}
            )
            if serializer.is_valid():
                serializer.save(user=request.user, activity=activity)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get', 'post'])
    def milestones(self, request, pk=None):
        """Get all milestones or create a new milestone for an activity"""
        activity = self.get_object()
        
        if request.method == 'GET':
            milestones = activity.milestones.all().order_by('due_date')
            serializer = MilestoneSerializer(milestones, many=True)
            return Response(serializer.data)
        
        elif request.method == 'POST':
            serializer = MilestoneSerializer(
                data={'activity': activity.id, **request.data}
            )
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['patch'], url_path='update-status')
    def update_status(self, request, pk=None):
        """Update activity status and priority"""
        activity = self.get_object()
        
        new_status = request.data.get('status')
        new_priority = request.data.get('priority')
        
        if new_status:
            activity.status = new_status
        if new_priority:
            activity.priority = new_priority
        
        activity.save()
        
        return Response({
            'success': True,
            'message': 'Activity updated successfully',
            'status': activity.status,
            'priority': activity.priority,
            'is_complete': activity.is_complete
        })


class MilestoneViewSet(viewsets.ModelViewSet):
    """
    Milestone management for activities.
    - Users with access to parent activity can manage milestones
    """
    serializer_class = MilestoneSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'priority', 'is_completed', 'activity']
    ordering_fields = ['due_date', 'created_at']
    ordering = ['due_date']

    def get_queryset(self):
        """Filter milestones based on activity access"""
        user = self.request.user
        
        if user.is_staff:
            return Milestone.objects.all().select_related('activity', 'assigned_to')
        
        # Users see milestones for activities they have access to
        return Milestone.objects.filter(
            Q(activity__responsible=user) | 
            Q(activity__accountable=user) | 
            Q(activity__consulted=user) | 
            Q(activity__informed=user) |
            Q(activity__project__created_by=user) |
            Q(assigned_to=user)
        ).distinct().select_related('activity', 'assigned_to')

    @action(detail=True, methods=['post'], url_path='mark-complete')
    def mark_complete(self, request, pk=None):
        """Mark milestone as completed"""
        milestone = self.get_object()
        milestone.status = 'completed'
        milestone.save()
        
        return Response({
            'success': True,
            'message': 'Milestone marked as complete',
            'is_completed': milestone.is_completed,
            'completed_at': milestone.completed_at
        })

    @action(detail=True, methods=['get', 'post'])
    def comments(self, request, pk=None):
        """Get all comments or create a new comment for a milestone"""
        milestone = self.get_object()
        
        if request.method == 'GET':
            comments = milestone.comments.select_related('user').order_by('-created_at')
            serializer = MilestoneCommentSerializer(comments, many=True)
            return Response(serializer.data)
        
        elif request.method == 'POST':
            serializer = MilestoneCommentSerializer(
                data={'milestone': milestone.id, 'content': request.data.get('content')}
            )
            if serializer.is_valid():
                serializer.save(user=request.user, milestone=milestone)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ActivityDocumentViewSet(viewsets.ModelViewSet):
    """
    Document management for activities.
    - Users with activity access can view/upload documents
    """
    serializer_class = ActivityDocumentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['activity', 'document_type']
    ordering = ['-created_at']

    def get_queryset(self):
        """Filter documents based on activity access"""
        user = self.request.user
        
        if user.is_staff:
            return ActivityDocument.objects.all().select_related(
                'activity', 'uploaded_by'
            )
        
        # Users see documents for activities they have access to
        return ActivityDocument.objects.filter(
            Q(activity__responsible=user) | 
            Q(activity__accountable=user) | 
            Q(activity__consulted=user) | 
            Q(activity__informed=user)
        ).distinct().select_related('activity', 'uploaded_by')

    def perform_create(self, serializer):
        """Set uploader when creating document"""
        serializer.save(uploaded_by=self.request.user)

    @action(detail=False, methods=['get'])
    def by_activity(self, request):
        """Get all documents for a specific activity"""
        activity_id = request.query_params.get('activity_id')
        if not activity_id:
            return Response(
                {'error': 'activity_id parameter required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        docs = self.get_queryset().filter(activity_id=activity_id)
        serializer = self.get_serializer(docs, many=True)
        return Response(serializer.data)