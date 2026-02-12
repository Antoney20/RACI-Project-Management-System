from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, F, Count
from django.db import transaction
from rest_framework.exceptions import PermissionDenied, ValidationError
from django.utils import timezone
from datetime import timedelta
from django.http import HttpRequest

from rest_framework.viewsets import ViewSet
from rest_framework.permissions import IsAuthenticated 
from django.contrib.auth import get_user_model


from notifications.service import NotificationService
from projects.services.alert import send_admin_review_alert_email, send_supervisor_review_alert_email
from projects.utils.review_service import ActivityReportService
from projects.utils.reviews import create_admin_review, create_or_reset_accountable_review, create_supervisor_review
from projects.utils.roles import is_admin, is_supervisor

from .models import ActivityReview, Notification, Project, Activity, Milestone, ActivityComment, MilestoneComment, ActivityDocument, SupervisorReview, UserActivityPriority,ActivityReviewComment
from .serializers import (
    ActivityReviewSerializer, NotificationSerializer, ProjectCreateSerializer, ProjectListSerializer, ProjectDetailSerializer,
    ActivityCreateSerializer, ActivityListSerializer, ActivityDetailSerializer,
    MilestoneSerializer, ActivityCommentSerializer, MilestoneCommentSerializer,
    ActivityDocumentSerializer, ReorderSerializer, SupervisorReviewSerializer, UserActivityPrioritySerializer
)

import logging
from django.utils import timezone

logger = logging.getLogger(__name__)
User = get_user_model()


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
        
        return Project.objects.filter(
            Q(created_by=user) |
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
        
        self._create_accountable_review(activity)
        
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

    def _create_accountable_review(self, activity):
        return create_or_reset_accountable_review(activity)

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
            Q(created_by=user) |
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
            Q(created_by=user) |
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



class NewActivityReviewViewSet(viewsets.ModelViewSet):
    """
    Activity Review Workflow

    Levels:
        1. Accountable Review
        2. Supervisor Review
        3. Admin Review

    Workflow:
        - Activity completed → Accountable review created (status='submitted')
        - Accountable approves + marks complete → Supervisor review created (status='submitted')
        - Supervisor approves + marks complete → Admin review created (status='submitted')
        - Admin approves + marks complete → Activity marked approved

    Status Flow:
        submitted → approved/rejected → mark_complete (triggers next level)

    Access Rules:

    - Admin / Office Admin:
        - See ALL reviews
        - Can perform ANY action

    - Accountable:
        - Can see accountable-level reviews
        - Only for activities where they are the accountable user

    - Supervisor:
        - Can see:
            • Supervisor-level reviews
            • Reviews where they are reviewer
            • Reviews where they are consulted or informed


    General Rules:
        - Any assigned reviewer can:
            • Start review (optional)
            • Approve review
            • Reject review
            • Mark review complete (required to progress)
        - No admin-only rejection
    """

    serializer_class = ActivityReviewSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        qs = ActivityReview.objects.select_related(
            "activity__project",
            "activity__responsible",
            "activity__accountable",
            "reviewer"
        ).prefetch_related(
            "activity__consulted",
            "activity__informed"
        )

        # Admin sees everything
        if is_admin(user):
            return qs

        # Accountable-level reviews
        accountable_qs = qs.filter(
            review_level="accountable",
            activity__accountable=user
        )

        # Supervisor visibility
        if is_supervisor(user):
            supervisor_qs = qs.filter(
                Q(review_level="supervisor") |
                Q(reviewer=user) |
                Q(activity__consulted=user) |
                Q(activity__informed=user)
            )

            return (accountable_qs | supervisor_qs).distinct()

        return accountable_qs.distinct()

    @action(detail=True, methods=["post"])
    def start(self, request, pk=None):
        """Optional: Start reviewing (changes status from 'submitted' to 'started')"""
        review = self.get_object()
        user = request.user

        if review.status not in ["submitted", "not_started"]:
            raise ValidationError("Review already started or completed")

        if not is_admin(user) and review.reviewer != user:
            raise PermissionDenied("You are not assigned to this review")

        review.status = "started"
        review.started_at = timezone.now()
        review.save()

        return Response({
            "detail": "Review started",
            "review": self.get_serializer(review).data
        })



    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        review = self.get_object()
        user = request.user

        if not is_admin(user) and review.reviewer != user:
            raise PermissionDenied("You are not assigned to this review")

        if review.status in ["approved", "rejected"]:
            raise ValidationError("Review already completed")

        # 1️⃣ Save approval state
        review.status = "approved"
        review.decision = "approved"
        review.decided_at = timezone.now()
        review.save()

        # 2️⃣ Create comment (NOT assign)
        comment_text = request.data.get("comments")
        if comment_text:
            ActivityReviewComment.objects.create(
                review=review,
                author=user,
                comment=comment_text
            )

        # 3️⃣ Response
        if review.review_level == "accountable":
            return Response({
                "detail": "Accountable review approved",
                "review": self.get_serializer(review).data
            })

        return Response({
            "detail": "Review approved. Click 'Mark Complete' to proceed.",
            "review": self.get_serializer(review).data
        })

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        """Reject the review"""
        review = self.get_object()
        user = request.user

        if not is_admin(user) and review.reviewer != user:
            raise PermissionDenied("You are not assigned to this review")

        if review.status in ["approved", "rejected"]:
            raise ValidationError("Review already completed")

        review.status = "rejected"
        review.decision = "rejected"
        review.decided_at = timezone.now()
        review.save()

        return Response({
            "detail": "Review rejected",
            "review": self.get_serializer(review).data
        })

    @action(detail=True, methods=["post"])
    def mark_complete(self, request, pk=None):
        review = self.get_object()
        user = request.user

        if not is_admin(user) and review.reviewer != user:
            raise PermissionDenied("You are not assigned to this review")

        if review.status == "completed":
            raise ValidationError("Review already completed")

        reviewer_id = request.data.get("reviewer_id")
        comments = request.data.get("comments")

        if review.review_level == "accountable":

            if not reviewer_id:
                raise ValidationError("Please select a supervisor to review next")

            try:
                supervisor = User.objects.get(id=reviewer_id)
            except User.DoesNotExist:
                raise ValidationError("Selected supervisor not found")

            review.status = "completed"
            review.next_reviewer_id = reviewer_id
            review.completed_at = timezone.now()
            review.save()

            comment_text = request.data.get("comments")
            if comment_text:
                ActivityReviewComment.objects.create(
                    review=review,
                    author=request.user,
                    comment=comment_text
                )

            create_supervisor_review(review.activity, supervisor)

            return Response({
                "detail": "Accountable review completed. Supervisor review created.",
                "review": self.get_serializer(review).data
            })
        if not review.decision:
            raise ValidationError(
                "Please approve or reject the review before marking it complete"
            )

        if review.review_level == "supervisor" and review.decision == "approved":
            if not reviewer_id:
                raise ValidationError("Please select an admin to review next")

            try:
                selected_admin = User.objects.get(id=reviewer_id)
                if selected_admin.role not in ["admin", "office_admin"]:
                    raise ValidationError("Selected user must be an admin")
                review.next_reviewer_id = reviewer_id
            except User.DoesNotExist:
                raise ValidationError("Selected admin not found")


        comment_text = request.data.get("comments")

        if comment_text:
            ActivityReviewComment.objects.create(
                review=review,
                author=request.user,
                comment=comment_text
            )

        review.status = "completed"
        review.is_complete = True
        review.completed_at = timezone.now()
        review.save()

        if review.decision == "approved":
            self._progress_to_next_level(review)

        return Response({
            "detail": "Review completed successfully",
            "review": self.get_serializer(review).data
        })



    def _progress_to_next_level(self, review):
        activity = review.activity

        if review.review_level == "supervisor":
            admin_id = review.next_reviewer_id

            if not admin_id:
                logger.warning(f"No admin selected for activity {activity.id}")
                return

            try:
                admin = User.objects.get(id=admin_id)
            except User.DoesNotExist:
                logger.error(f"Admin {admin_id} not found")
                return

            create_admin_review(activity, admin)

        elif review.review_level == "admin":
            activity.status = "approved"
            activity.save()



    @action(detail=False, methods=["get"])
    def admin_desk(self, request):
        """Get all pending admin reviews"""
        if not is_admin(request.user):
            raise PermissionDenied("Admin access required")

        reviews = self.get_queryset().filter(
            review_level="admin",
            # status__in=["submitted", "started"], 
            # is_complete=False
        )
        return Response(self.get_serializer(reviews, many=True).data)

    @action(detail=False, methods=["get"])
    def supervisor_desk(self, request):
        """Get all pending supervisor reviews for current user"""
        user = request.user
        
        if not is_supervisor(user) and not is_admin(user):
            raise PermissionDenied("Supervisor or Admin access required")

        reviews = self.get_queryset().filter(
            review_level="supervisor",
            reviewer=user,
            is_complete=False
        ).order_by('-submitted_at')
        
        return Response(self.get_serializer(reviews, many=True).data)

    @action(detail=False, methods=["get"])
    def accountable_desk(self, request):
        """Get all pending accountable reviews for current user"""
        user = request.user
        
        reviews = self.get_queryset().filter(
            review_level="accountable",
            activity__accountable=user,
            is_complete=False
        ).order_by('-submitted_at')
        
        return Response(self.get_serializer(reviews, many=True).data)

    @action(detail=False, methods=["get"])
    def my_pending_reviews(self, request):
        """Get all pending reviews assigned to current user across all levels"""
        user = request.user
        
        reviews = self.get_queryset().filter(
            reviewer=user,
            is_complete=False
        ).order_by('review_level', '-submitted_at')
        
        return Response(self.get_serializer(reviews, many=True).data)


    
class ActivityReviewViewSet(ModelViewSet):
    """
    ViewSet for managing activity reviews.
    Access rules:
    - Admin / Office Admin:
        - See ALL activity reviews
        - Can do ANYTHING (start any review, approve, update notes, etc.)
    - Supervisor:
        - Only activities where they are CONSULTED or INFORMED
        - Or where they are the reviewer
    - Staff:
        - No access
    """

    serializer_class = SupervisorReviewSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        qs = SupervisorReview.objects.select_related(
            "activity__project",
            "activity__responsible",
            "reviewer"
        ).prefetch_related(
            "activity__consulted",
            "activity__informed"
        )

        # Admin sees everything
        if is_admin(user):
            return qs

        if is_supervisor(user):
            return qs.filter(
                Q(reviewer=user) |
                Q(activity__consulted=user) |
                Q(activity__informed=user)
            ).distinct()

        return SupervisorReview.objects.none()

    @action(detail=True, methods=["post"])
    def supervisor_approve(self, request, pk=None):
        """
        Supervisor approves their review.
        Can optionally escalate to admin immediately.
        Admins can also approve supervisor reviews.
        """
        review = self.get_object()
        user = request.user

        # Admins can do anything, supervisors need to be consulted/informed
        if not is_admin(user):
            if not is_supervisor(user):
                raise PermissionDenied("Only supervisors or admins can approve")
            
            # Check if supervisor is consulted or informed
            is_consulted = review.activity.consulted.filter(id=user.id).exists()
            is_informed = review.activity.informed.filter(id=user.id).exists()
            
            if not (is_consulted or is_informed):
                raise PermissionDenied("You must be consulted or informed on this activity")

        if review.review_level != "supervisor":
            raise ValidationError("Not a supervisor review")

        if review.is_supervisor_approved:
            raise ValidationError("Review already approved")

        move_to_admin = request.data.get('move_to_admin', False)

        # Approve the supervisor review
        review.is_supervisor_approved = True
        review.supervisor_approved_at = timezone.now()
        review.status = "completed"
        
        if move_to_admin:
            review.move_to_admin = True
        
        review.save()

        # If escalating, create admin review
        if move_to_admin:
            admin_review, created = SupervisorReview.objects.get_or_create(
                activity=review.activity,
                review_level="admin",
                defaults={
                    "status": "not_started",
                    "reviewer": None  
                }
            )
            
            return Response({
                "detail": "Supervisor approved and escalated to admin",
                "supervisor_review": self.get_serializer(review).data,
                "admin_review": self.get_serializer(admin_review).data
            })

        return Response({
            "detail": "Supervisor approved. Review closed.",
            "review": self.get_serializer(review).data
        })

    @action(detail=True, methods=["post"])
    def move_to_admin(self, request, pk=None):
        """
        Escalate an approved supervisor review to admin.
        Can only be done after supervisor approval.
        Admins can also escalate.
        """
        review = self.get_object()
        user = request.user

        # Admins can do anything, supervisors need to be consulted/informed
        if not is_admin(user):
            if not is_supervisor(user):
                raise PermissionDenied("Only supervisors or admins can escalate")
            
            # Check if supervisor is consulted or informed
            is_consulted = review.activity.consulted.filter(id=user.id).exists()
            is_informed = review.activity.informed.filter(id=user.id).exists()
            
            if not (is_consulted or is_informed):
                raise PermissionDenied("You must be consulted or informed on this activity")

        if review.review_level != "supervisor":
            raise ValidationError("Only supervisor reviews can be escalated")

        if not review.is_supervisor_approved:
            raise ValidationError("Supervisor must approve before escalating")

        if review.move_to_admin:
            raise ValidationError("Review already escalated to admin")

        # Mark as escalated
        review.move_to_admin = True
        review.save()

        # Create admin review
        admin_review, created = SupervisorReview.objects.get_or_create(
            activity=review.activity,
            review_level="admin",
            defaults={
                "status": "not_started",
                "reviewer": None
            }
        )

        if not created and admin_review.status == "completed":
            raise ValidationError("Admin review already completed")

        return Response({
            "detail": "Moved to admin review",
            "supervisor_review": self.get_serializer(review).data,
            "admin_review": self.get_serializer(admin_review).data
        })

    @action(detail=True, methods=["post"])
    def admin_approve(self, request, pk=None):
        """
        Admin approves the review. This closes the entire review process.
        Only admins can approve admin reviews.
        """
        review = self.get_object()
        user = request.user

        if not is_admin(user):
            raise PermissionDenied("Only admins can approve admin reviews")

        if review.review_level != "admin":
            raise ValidationError("Not an admin review")

        if review.is_admin_approved:
            raise ValidationError("Review already approved")

        # Approve admin review
        review.is_admin_approved = True
        review.admin_approved_at = timezone.now()
        review.status = "completed"
        review.is_complete = True
        review.save()

        return Response({
            "detail": "Admin approved. Review process complete.",
            "review": self.get_serializer(review).data
        })

    @action(detail=True, methods=["post"])
    def start_review(self, request, pk=None):
        """
        Start a review (change status from not_started to started).
        - Admins can start any review
        - Supervisors can start reviews if they are consulted or informed
        """
        review = self.get_object()
        user = request.user

        if review.status != "not_started":
            raise ValidationError(f"Review already {review.status}")

        # Admins can start any review
        if is_admin(user):
            review.status = "started"
            review.reviewer = user
            review.save()
            
            return Response({
                "detail": "Review started",
                "review": self.get_serializer(review).data
            })

        # Supervisors can only start supervisor reviews if consulted/informed
        if review.review_level == "supervisor" and is_supervisor(user):
            is_consulted = review.activity.consulted.filter(id=user.id).exists()
            is_informed = review.activity.informed.filter(id=user.id).exists()
            
            if is_consulted or is_informed:
                review.status = "started"
                review.reviewer = user
                review.save()
                
                return Response({
                    "detail": "Review started",
                    "review": self.get_serializer(review).data
                })
        
        raise PermissionDenied(
            "You must be consulted or informed on this activity to start the review"
        )

    @action(detail=True, methods=["patch"])
    def update_notes(self, request, pk=None):
        """
        Update review notes.
        - Admins can update any review notes
        - Supervisors can update notes if they are consulted or informed
        """
        review = self.get_object()
        user = request.user

        # Admins can update any notes
        if is_admin(user):
            notes = request.data.get('notes', '')
            review.notes = notes
            review.save()
            
            return Response({
                "detail": "Notes updated",
                "review": self.get_serializer(review).data
            })

        # Supervisors can update notes if consulted/informed
        if review.review_level == "supervisor" and is_supervisor(user):
            is_consulted = review.activity.consulted.filter(id=user.id).exists()
            is_informed = review.activity.informed.filter(id=user.id).exists()
            
            if is_consulted or is_informed:
                notes = request.data.get('notes', '')
                review.notes = notes
                review.save()
                
                return Response({
                    "detail": "Notes updated",
                    "review": self.get_serializer(review).data
                })
        
        raise PermissionDenied(
            "You must be consulted or informed on this activity to update review notes"
        )


class ActivityReportsViewSet(ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        user = request.user

        if user.role not in ['admin', 'supervisor']:
            return Response(
                {'error': 'You do not have permission to view reports.'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            report_data = ActivityReportService.compile_report(user)
            return Response(report_data, status=status.HTTP_200_OK)
        except ValueError as ve:
            return Response({'error': str(ve)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            return Response({'error': f'Failed to: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
   
   
    
    


class NotificationViewSet(ViewSet):
    """
    Notification management viewset
    
    Endpoints:
    - list: Get all notifications for current user
    - unread: Get unread notifications
    - mark_read: Mark notification as read
    - mark_all_read: Mark all notifications as read
    - stats: Get notification statistics
    - project_status: Get project status summary
    """
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        """Get all notifications for current user"""
        user = request.user
        
        # Query params
        is_read = request.query_params.get('is_read')
        notification_type = request.query_params.get('type')
        limit = int(request.query_params.get('limit', 50))
        
        # Build query
        queryset = Notification.objects.filter(recipient=user)
        
        if is_read is not None:
            queryset = queryset.filter(is_read=is_read.lower() == 'true')
        
        if notification_type:
            queryset = queryset.filter(notification_type=notification_type)
        
        notifications = queryset[:limit]
        
        serializer = NotificationSerializer(notifications, many=True)
        
        return Response({
            'count': queryset.count(),
            'unread_count': queryset.filter(is_read=False).count(),
            'notifications': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def unread(self, request):
        """Get only unread notifications"""
        user = request.user
        limit = int(request.query_params.get('limit', 20))
        
        notifications = Notification.objects.filter(
            recipient=user,
            is_read=False
        )[:limit]
        
        serializer = NotificationSerializer(notifications, many=True)
        
        return Response({
            'count': notifications.count(),
            'notifications': serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark a notification as read"""
        try:
            notification = Notification.objects.get(
                id=pk,
                recipient=request.user
            )
            notification.mark_read()
            
            return Response({
                'message': 'Notification marked as read',
                'notification': NotificationSerializer(notification).data
            })
        except Notification.DoesNotExist:
            return Response(
                {'error': 'Notification not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """Mark all notifications as read for current user"""
        user = request.user
        
        updated = Notification.objects.filter(
            recipient=user,
            is_read=False
        ).update(is_read=True)
        
        return Response({
            'message': f'Marked {updated} notifications as read',
            'count': updated
        })
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get notification statistics"""
        user = request.user
        
        # Overall counts
        total = Notification.objects.filter(recipient=user).count()
        unread = Notification.objects.filter(recipient=user, is_read=False).count()
        
        # By type
        by_type = Notification.objects.filter(
            recipient=user
        ).values('notification_type').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Recent (last 7 days)
        seven_days_ago = timezone.now() - timedelta(days=7)
        recent = Notification.objects.filter(
            recipient=user,
            created_at__gte=seven_days_ago
        ).count()
        
        # Urgent unread (activity overdue, leave pending for supervisors)
        urgent_unread = Notification.objects.filter(
            recipient=user,
            is_read=False,
            notification_type__in=['activity_overdue', 'leave_pending', 'contract_expiring']
        ).count()
        
        return Response({
            'total': total,
            'unread': unread,
            'recent_7_days': recent,
            'urgent_unread': urgent_unread,
            'by_type': list(by_type),
            'summary': {
                'read_rate': round((total - unread) / total * 100, 1) if total > 0 else 0,
                'avg_per_day': round(recent / 7, 1)
            }
        })
    
    @action(detail=False, methods=['get'])
    def project_status(self, request):
        """Get project status summary for user"""
        user = request.user
        
        summary = NotificationService.generate_project_status_update(user)
        
        return Response({
            'user': user.get_full_name() or user.username,
            'generated_at': timezone.now(),
            'projects': summary
        })
    
    @action(detail=False, methods=['delete'])
    def clear_old(self, request):
        """Delete old read notifications (older than 30 days)"""
        user = request.user
        
        thirty_days_ago = timezone.now() - timedelta(days=30)
        
        deleted_count, _ = Notification.objects.filter(
            recipient=user,
            is_read=True,
            created_at__lt=thirty_days_ago
        ).delete()
        
        return Response({
            'message': f'Deleted {deleted_count} old notifications',
            'count': deleted_count
        })
    
    @action(detail=False, methods=['get'])
    def by_category(self, request):
        """Get notifications grouped by category"""
        user = request.user
        
        categories = {
            'leave': ['leave_pending', 'leave_approved', 'leave_rejected'],
            'activities': ['activity_assigned', 'activity_due', 'activity_overdue'],
            'reviews': ['review_needed', 'review_completed'],
            'contracts': ['contract_expiring', 'contract_expired'],
            'projects': ['project_status']
        }
        
        result = {}
        
        for category, types in categories.items():
            notifications = Notification.objects.filter(
                recipient=user,
                notification_type__in=types,
                is_read=False
            ).order_by('-created_at')[:10]
            
            result[category] = {
                'count': notifications.count(),
                'notifications': NotificationSerializer(notifications, many=True).data
            }
        
        return Response(result)


class AdminNotificationViewSet(ViewSet):
    """
    Admin-only notification management
    
    Endpoints:
    - trigger_reminders: Manually trigger all reminder notifications
    - send_pending: Send all pending notifications
    - system_stats: Get system-wide notification statistics
    """
    permission_classes = [IsAuthenticated]
    
    def _check_admin(self, user):
        """Check if user is admin"""
        if not hasattr(user, 'role') or user.role != 'admin':
            return False
        return True
    
    @action(detail=False, methods=['post'])
    def trigger_reminders(self, request):
        """Manually trigger all reminder notifications"""
        if not self._check_admin(request.user):
            return Response(
                {'error': 'Admin access required'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        results = {}
        
        # Leave reminders
        results['pending_leaves'] = NotificationService.notify_pending_leave_approvals()
        
        # Activity reminders
        results['activities_due'] = NotificationService.notify_activity_due_soon()
        results['activities_overdue'] = NotificationService.notify_overdue_activities()
        
        # Review reminders
        results['pending_reviews'] = NotificationService.notify_pending_reviews()
        
        # Contract reminders
        results['expiring_contracts'] = NotificationService.notify_expiring_contracts()
        
        return Response({
            'message': 'Reminders triggered successfully',
            'results': results,
            'total_created': sum(r.get('created', 0) for r in results.values())
        })
    
    @action(detail=False, methods=['post'])
    def send_pending(self, request):
        """Send all pending notifications via email"""
        if not self._check_admin(request.user):
            return Response(
                {'error': 'Admin access required'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        results = NotificationService.send_pending_notifications()
        
        return Response({
            'message': 'Pending notifications processed',
            'sent': results['sent'],
            'failed': results['failed']
        })
    
    @action(detail=False, methods=['get'])
    def system_stats(self, request):
        """Get system-wide notification statistics"""
        if not self._check_admin(request.user):
            return Response(
                {'error': 'Admin access required'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Total notifications
        total = Notification.objects.count()
        unread = Notification.objects.filter(is_read=False).count()
        pending_send = Notification.objects.filter(is_sent=False).count()
        
        # By type
        by_type = Notification.objects.values(
            'notification_type'
        ).annotate(
            total=Count('id'),
            unread=Count('id', filter=Q(is_read=False))
        ).order_by('-total')
        

        failed = Notification.objects.filter(
            is_sent=False,
            retry_count__gte=NotificationService.MAX_RETRIES
        ).count()
        
        return Response({
            'total_notifications': total,
            'unread': unread,
            'pending_send': pending_send,
            'failed_sends': failed,
            'by_type': list(by_type),
            'system_health': {
                'send_success_rate': round((total - failed) / total * 100, 1) if total > 0 else 100,
                'read_rate': round((total - unread) / total * 100, 1) if total > 0 else 0
            }
        })












    
