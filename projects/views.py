from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from django.db import transaction

from .models import Project, Activity, Milestone, ActivityComment, MilestoneComment, ActivityDocument, SupervisorReview, UserActivityPriority
from .serializers import (
    ProjectCreateSerializer, ProjectListSerializer, ProjectDetailSerializer,
    ActivityCreateSerializer, ActivityListSerializer, ActivityDetailSerializer,
    MilestoneSerializer, ActivityCommentSerializer, MilestoneCommentSerializer,
    ActivityDocumentSerializer, ReorderSerializer, UserActivityPrioritySerializer
)

# class ProjectViewSet(viewsets.ModelViewSet):
#     """
#     Project CRUD operations with role-based access.
#     - Users see projects where they have activities (via RACI roles)
#     - Staff can see all projects
#     """
#     permission_classes = [IsAuthenticated]
#     filter_backends = [DjangoFilterBackend]
#     filterset_fields = ['status', 'priority']
#     search_fields = ['name', 'description']
#     ordering_fields = ['created_at', 'start_date']
#     ordering = ['-created_at']

#     def get_queryset(self):
#         """Filter projects based on user permissions"""
#         user = self.request.user
        
#         if user.is_staff:
#             return Project.objects.all().select_related('created_by', 'sprint')
        
#         # Users see projects where they have activities (through any RACI role)
#         return Project.objects.filter(
#             Q(activities__responsible=user) |
#             Q(activities__accountable=user) |
#             Q(activities__consulted=user) |
#             Q(activities__informed=user)
#         ).distinct().select_related('created_by', 'sprint')

#     def get_serializer_class(self):
#         """Return appropriate serializer based on action"""
#         if self.action == 'create':
#             return ProjectCreateSerializer
#         if self.action == 'retrieve':
#             return ProjectDetailSerializer
#         return ProjectListSerializer

#     def perform_create(self, serializer):
#         """Set the creator when creating a project"""
#         serializer.save(created_by=self.request.user)

#     def destroy(self, request, *args, **kwargs):
#         """Only staff can delete projects"""
#         if not request.user.is_staff:
#             return Response(
#                 {
#                     "success": False,
#                     "message": "Only administrators can delete projects."
#                 },
#                 status=status.HTTP_403_FORBIDDEN
#             )
        
#         project = self.get_object()
#         project_name = project.name
#         self.perform_destroy(project)
        
#         return Response(
#             {
#                 "success": True,
#                 "message": f'Project "{project_name}" deleted successfully.'
#             },
#             status=status.HTTP_200_OK
#         )


# class ActivityViewSet(viewsets.ModelViewSet):
#     """
#     Activity CRUD operations with RACI role-based access.
#     - Users with any RACI role (R/A/C/I) can view activities
#     - Responsible/Accountable can edit
#     - Staff can see all
#     """
#     permission_classes = [IsAuthenticated]
#     filter_backends = [DjangoFilterBackend]
#     filterset_fields = ['status', 'priority', 'project', 'is_complete']
#     search_fields = ['name', 'description']
#     ordering_fields = ['created_at', 'deadline']
#     ordering = ['-created_at']

#     def get_queryset(self):
#         """Filter activities based on user RACI roles"""
#         user = self.request.user
        
#         if user.is_staff:
#             return Activity.objects.all().select_related(
#                 'project', 'responsible', 'accountable'
#             ).prefetch_related('consulted', 'informed')
        
#         # Users see activities where they have any RACI role
#         return Activity.objects.filter(
#             Q(responsible=user) | 
#             Q(accountable=user) | 
#             Q(consulted=user) | 
#             Q(informed=user) 
#         ).distinct().select_related(
#             'project', 'responsible', 'accountable'
#         ).prefetch_related('consulted', 'informed')

#     def get_serializer_class(self):
#         """Return appropriate serializer based on action"""
#         if self.action == 'create':
#             return ActivityCreateSerializer
#         if self.action == 'retrieve':
#             return ActivityDetailSerializer
#         return ActivityListSerializer

#     @action(detail=True, methods=['post'], url_path='mark-complete')
#     def mark_complete(self, request, pk=None):
#         """Mark activity as completed"""
#         activity = self.get_object()
#         activity.status = 'completed'
#         activity.save()
        
#         return Response({
#             'success': True,
#             'message': 'Activity marked as complete',
#             'is_complete': activity.is_complete
#         })

#     @action(detail=True, methods=['get', 'post'])
#     def comments(self, request, pk=None):
#         """Get all comments or create a new comment for an activity"""
#         activity = self.get_object()
        
#         if request.method == 'GET':
#             comments = activity.comments.select_related('user').order_by('-created_at')
#             serializer = ActivityCommentSerializer(comments, many=True)
#             return Response(serializer.data)
        
#         elif request.method == 'POST':
#             serializer = ActivityCommentSerializer(
#                 data={'activity': activity.id, 'content': request.data.get('content')}
#             )
#             if serializer.is_valid():
#                 serializer.save(user=request.user, activity=activity)
#                 return Response(serializer.data, status=status.HTTP_201_CREATED)
#             return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

#     @action(detail=True, methods=['get', 'post'])
#     def milestones(self, request, pk=None):
#         """Get all milestones or create a new milestone for an activity"""
#         activity = self.get_object()
        
#         if request.method == 'GET':
#             milestones = activity.milestones.all().order_by('due_date')
#             serializer = MilestoneSerializer(milestones, many=True)
#             return Response(serializer.data)
        
#         elif request.method == 'POST':
#             serializer = MilestoneSerializer(
#                 data={'activity': activity.id, **request.data}
#             )
#             if serializer.is_valid():
#                 serializer.save()
#                 return Response(serializer.data, status=status.HTTP_201_CREATED)
#             return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

#     @action(detail=True, methods=['patch'], url_path='update-status')
#     def update_status(self, request, pk=None):
#         """Update activity status and priority"""
#         activity = self.get_object()
        
#         new_status = request.data.get('status')
#         new_priority = request.data.get('priority')
        
#         if new_status:
#             activity.status = new_status
#         if new_priority:
#             activity.priority = new_priority
        
#         activity.save()
        
#         return Response({
#             'success': True,
#             'message': 'Activity updated successfully',
#             'status': activity.status,
#             'priority': activity.priority,
#             'is_complete': activity.is_complete
#         })



class ProjectViewSet(viewsets.ModelViewSet):
    """
    Project CRUD operations with role-based access.
    - Users see projects where they have activities (via RACI roles)
    - Only Admin and Supervisor can edit projects
    - Only Admin can delete projects
    - Staff can see all projects (if is_staff=True)
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
        
        # Users see projects where they have activities (through any RACI role)
        return Project.objects.filter(
            Q(activities__responsible=user) |
            Q(activities__accountable=user) |
            Q(activities__consulted=user) |
            Q(activities__informed=user)
        ).distinct().select_related('created_by', 'sprint')

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

    def update(self, request, *args, **kwargs):
        """Only Admin or Supervisor can update projects"""
        user = request.user
        
        if not (user.is_admin() or user.is_supervisor()):
            return Response(
                {
                    "success": False,
                    "message": "Only Admins and Supervisors can edit projects."
                },
                status=status.HTTP_403_FORBIDDEN
            )
        
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        """Only Admin or Supervisor can partially update projects"""
        user = request.user
        
        if not (user.is_admin() or user.is_supervisor()):
            return Response(
                {
                    "success": False,
                    "message": "Only Admins and Supervisors can edit projects."
                },
                status=status.HTTP_403_FORBIDDEN
            )
        
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """Only Admin can delete projects"""
        if not request.user.is_admin():
            return Response(
                {
                    "success": False,
                    "message": "Only Admins can delete projects."
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
    - Only Admin or Supervisor can edit activities
    - Only Admin can delete activities
    - Staff can see all activities (if is_staff=True)
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

    def update(self, request, *args, **kwargs):
        """Only Admin or Supervisor can update activities"""
        user = request.user
        
        if not (user.is_admin() or user.is_supervisor()):
            return Response(
                {
                    "success": False,
                    "message": "Only Admins and Supervisors can edit activities."
                },
                status=status.HTTP_403_FORBIDDEN
            )
        
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        """Only Admin or Supervisor can partially update activities"""
        user = request.user
        
        if not (user.is_admin() or user.is_supervisor()):
            return Response(
                {
                    "success": False,
                    "message": "Only Admins and Supervisors can edit activities."
                },
                status=status.HTTP_403_FORBIDDEN
            )
        
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """Only Admin can delete activities"""
        if not request.user.is_admin():
            return Response(
                {
                    "success": False,
                    "message": "Only Admins can delete activities."
                },
                status=status.HTTP_403_FORBIDDEN
            )
        
        activity = self.get_object()
        activity_name = activity.name
        self.perform_destroy(activity)
        
        return Response(
            {
                "success": True,
                "message": f'Activity "{activity_name}" deleted successfully.'
            },
            status=status.HTTP_200_OK
        )


    @action(detail=True, methods=['post'], url_path='mark-complete')
    def mark_complete(self, request, pk=None):
        """
        Mark activity as completed and trigger supervisor review.
        Only Responsible, Accountable, Admin, or Supervisor can mark complete.
        """
        activity = self.get_object()
        user = request.user
        
        # Check permission: Responsible, Accountable, Admin, or Supervisor
        if not (activity.responsible == user or activity.accountable == user or 
                user.is_admin() or user.is_supervisor()):
            return Response(
                {
                    "success": False,
                    "message": "Only Responsible or Accountable users can mark activity as complete."
                },
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Mark activity as completed
        activity.status = 'completed'
        activity.save()
        
        # Create or update supervisor review
        self._create_supervisor_review(activity)
        
        return Response({
            'success': True,
            'message': 'Activity marked as complete. Supervisor review initiated.',
            'is_complete': activity.is_complete,
            'status': activity.status
        })

    @action(detail=True, methods=['post'], url_path='reorder')
    def reorder(self, request, pk=None):
        """
        Reorder activity within project. Efficient bulk update approach.
        Expects: {"new_order": <integer>}
        """
        activity = self.get_object()
        user = request.user
        
        # Check permission: only Admin or Supervisor can reorder
        if not (user.is_admin() or user.is_supervisor()):
            return Response(
                {
                    "success": False,
                    "message": "Only Admins and Supervisors can reorder activities."
                },
                status=status.HTTP_403_FORBIDDEN
            )
        
        new_order = request.data.get('new_order')
        
        if new_order is None or not isinstance(new_order, int) or new_order < 1:
            return Response(
                {
                    "success": False,
                    "message": "Valid 'new_order' (positive integer) is required."
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get current order
        old_order = activity.order
        
        # No change needed
        if old_order == new_order:
            return Response({
                'success': True,
                'message': 'Activity order unchanged.',
                'order': activity.order
            })
        
        with transaction.atomic():
            if new_order < old_order:
                Activity.objects.filter(
                    project=activity.project,
                    order__gte=new_order,
                    order__lt=old_order
                ).update(order=F('order') + 1)
            else:
                Activity.objects.filter(
                    project=activity.project,
                    order__gt=old_order,
                    order__lte=new_order
                ).update(order=F('order') - 1)
            
            # Update current activity order
            activity.order = new_order
            activity.save(update_fields=['order'])
        
        return Response({
            'success': True,
            'message': f'Activity reordered to position {new_order}.',
            'old_order': old_order,
            'new_order': new_order
        })

    def _create_supervisor_review(self, activity):
        """
        Create supervisor review when activity is marked complete.
        Uses get_or_create to avoid duplicates.
        """
        # Get accountable user as default supervisor
        supervisor = activity.accountable
        
        review, created = SupervisorReview.objects.get_or_create(
            activity=activity,
            defaults={
                'supervisor': supervisor,
                'status': 'not_started'
            }
        )
        
        # If review exists but was previously completed/rejected, reset it
        if not created and review.is_complete:
            review.status = 'not_started'
            review.started_at = None
            review.completed_at = None
            review.is_complete = False
            review.notes = ''
            review.save()
        
        return review


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
            # Only Admin or Supervisor can create milestones
            if not (request.user.is_admin() or request.user.is_supervisor()):
                return Response(
                    {
                        "success": False,
                        "message": "Only Admins and Supervisors can create milestones."
                    },
                    status=status.HTTP_403_FORBIDDEN
                )
            
            serializer = MilestoneSerializer(
                data={'activity': activity.id, **request.data}
            )
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['patch'], url_path='update-status')
    def update_status(self, request, pk=None):
        """Update activity status and priority - only Admin or Supervisor"""
        user = request.user
        
        if not (user.is_admin() or user.is_supervisor()):
            return Response(
                {
                    "success": False,
                    "message": "Only Admins and Supervisors can update activity status."
                },
                status=status.HTTP_403_FORBIDDEN
            )
        
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



class UserActivityPriorityViewSet(viewsets.ModelViewSet):
    """User activity priority management"""
    permission_classes = [IsAuthenticated]
    serializer_class = UserActivityPrioritySerializer
    
    def get_queryset(self):
        return UserActivityPriority.objects.filter(
            user=self.request.user
        ).select_related('activity', 'activity__project').order_by('priority_order')
    
    @action(detail=False, methods=['post'], url_path='reorder')
    def reorder(self, request):
        """Reorder activity: POST {"activity_id": "uuid", "new_order": 1}"""
        serializer = ReorderSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"success": False, "errors": serializer.errors}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        activity_id = serializer.validated_data['activity_id']
        new_order = serializer.validated_data['new_order']
        
        with transaction.atomic():
            # Get or create priority
            priority, created = UserActivityPriority.objects.get_or_create(
                user=request.user, activity_id=activity_id,
                defaults={'priority_order': new_order}
            )
            
            if not created:
                old_order = priority.priority_order
                if old_order != new_order:
                    # Shift other priorities
                    if new_order < old_order:
                        UserActivityPriority.objects.filter(
                            user=request.user, priority_order__gte=new_order, 
                            priority_order__lt=old_order
                        ).update(priority_order=F('priority_order') + 1)
                    else:
                        UserActivityPriority.objects.filter(
                            user=request.user, priority_order__gt=old_order, 
                            priority_order__lte=new_order
                        ).update(priority_order=F('priority_order') - 1)
                    
                    priority.priority_order = new_order
                    priority.save()
        
        return Response({
            "success": True,
            "message": f"Reordered to position {new_order}",
            "priorities": UserActivityPrioritySerializer(
                self.get_queryset(), many=True
            ).data
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