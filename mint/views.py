import logging
from django.shortcuts import render

# Create your views here.
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework import serializers
from rest_framework import viewsets
from rest_framework import status, generics
from django_filters.rest_framework import DjangoFilterBackend
from collections import defaultdict
from datetime import timedelta
from django.core.exceptions import ValidationError
from rest_framework.exceptions import PermissionDenied, NotFound

from mint.services.sprint_service import SprintDetailsService


logger = logging.getLogger(__name__)

from django.db.models import Q, Count


from core.utils.weekdays import calculate_business_days, get_business_days_in_range
# from mint.services.reviews import move_project_to_review
 
  
from .models import (LeaveStatus,
                     Sprint,  LeaveRequest, LeaveAllocation, )
from .serializers import (
    SprintSerializer,
   
)
from django.utils import timezone
from rest_framework.permissions import AllowAny, IsAuthenticated

from django.contrib.auth import get_user_model
User = get_user_model()


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
        
        # if user.is_admin() or user.is_office_admin():
        #     data = Sprint.objects.all()

        #     return data
        
        # if user.is_supervisor():
        #     return Sprint.objects.all()
        
        # # Staff can view all sprints
        # return Sprint.objects.all()
        
    def get_queryset(self):
        user = self.request.user

        if user.is_admin() or user.is_office_admin():
            return Sprint.objects.all()

        if user.is_supervisor():
            return Sprint.objects.all()

        return Sprint.objects.all()

    @action(detail=True, methods=["get"])
    def details(self, request, pk=None):
        """
        Sprint full nested details
        Restricted:
        - Admin: full access
        - Others: only if involved via RACI or project creator
        """

        try:
            data = SprintDetailsService.get_sprint_details(
                request.user,
                pk
            )

            if data is None:
                raise PermissionDenied(
                    "You are not allowed to view this sprint."
                )

            return Response({
                "success": True,
                "data": data
            })

        except Sprint.DoesNotExist:
            raise NotFound("Sprint not found.")
    
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
        if not (self.request.user.is_admin()):
            raise PermissionDenied("Only admins can delete sprints.")
        instance.delete()
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get all active sprints"""
        sprints = self.get_queryset()
        serializer = self.get_serializer(sprints, many=True)
        return Response({'success': True, 'data': serializer.data})





# class ProjectViewSet(viewsets.ModelViewSet):
#     """
#     Project CRUD operations.
#     - Owner and users with RACI assignment can view/edit.
#     - Admin/staff can see all.
#     """
#     permission_classes = [IsAuthenticated]
#     filter_backends = [DjangoFilterBackend]
#     filterset_fields = ['status']
#     search_fields = ['name', 'description']
#     ordering_fields = ['created_at', 'start_date', 'progress']
#     ordering = ['-created_at']

#     def get_queryset(self):
#         user = self.request.user

#         if user.is_staff:  # or user.is_admin() if you have custom method
#             return Project.objects.all().select_related('owner').prefetch_related('raci_assignments__user')

#         # Owner OR has RACI assignment on the project
#         return Project.objects.filter(
#             Q(owner=user) | Q(raci_assignments__user=user)
#         ).distinct().select_related('owner').prefetch_related('raci_assignments__user')

#     def get_serializer_class(self):
#         if self.action == 'create':
#             return ProjectCreateSerializer
#         if self.action == 'retrieve':
#             return ProjectDetailSerializer
#         return ProjectListSerializer


#     def perform_create(self, serializer):
#         serializer.save()


#     # Optional: Custom action to list or add RACI assignments
#     @action(detail=True, methods=['get'])
#     def raci(self, request, pk=None):
#         project = self.get_object()
#         assignments = project.raci_assignments.select_related('user').all()
#         serializer = RACIAssignmentSerializer(assignments, many=True)
#         return Response(serializer.data)

#     @action(detail=True, methods=['post'])
#     def assign_role(self, request, pk=None):
#         """
#         Assign a user a RACI role on this project.
#         Expected data: { "user_id": "uuid", "raci_role": "Responsible" }
#         """
#         project = self.get_object()

#         # Only owner or Accountable/Consulted? Or allow Responsible to invite? Adjust as needed.
#         if not (project.owner == request.user or request.user.is_staff):
#             return Response(
#                 {"detail": "Only project owner or staff can assign roles."},
#                 status=status.HTTP_403_FORBIDDEN
#             )

#         user_id = request.data.get('user_id')
#         raci_role = request.data.get('raci_role')

#         if not user_id or not raci_role:
#             return Response(
#                 {"detail": "user_id and raci_role are required."},
#                 status=status.HTTP_400_BAD_REQUEST
#             )

#         try:
#             user = User.objects.get(id=user_id)
#         except  User.DoesNotExist:
#             return Response(
#                 {"detail": "User not found."},
#                 status=status.HTTP_404_NOT_FOUND
#             )

#         assignment, created = RACIAssignment.objects.update_or_create(
#             project=project,
#             user=user,
#             defaults={'raci_role': raci_role}
#         )

#         action_text = "created" if created else "updated"
#         return Response({
#             "success": True,
#             "message": f"{user.email or user.username} is now {raci_role} on this project.",
#             "assignment_id": str(assignment.id)
#         })


#     @action(detail=True, methods=['delete'])
#     def remove_role(self, request, pk=None):
#         """
#         Remove a user's RACI assignment from project.
#         Expected query param or data: user_id
#         """
#         project = self.get_object()

#         if not (project.owner == request.user or request.user.is_staff):
#             return Response(
#                 {"detail": "Only project owner or staff can remove roles."},
#                 status=status.HTTP_403_FORBIDDEN
#             )

#         user_id = request.query_params.get('user_id') or request.data.get('user_id')
#         if not user_id:
#             return Response(
#                 {"detail": "user_id is required."},
#                 status=status.HTTP_400_BAD_REQUEST
#             )

#         try:
#             assignment = project.raci_assignments.get(user_id=user_id)
#             assignment.delete()
#             return Response({"success": True, "message": "Role assignment removed."})
#         except RACIAssignment.DoesNotExist:
#             return Response(
#                 {"detail": "Assignment not found."},
#                 status=status.HTTP_404_NOT_FOUND
#             )

#     def destroy(self, request, *args, **kwargs):
#         if not request.user.is_staff:
#             return Response(
#                 {
#                     "success": False,
#                     "message": "You are not allowed to delete this project.",
#                     "errors": {
#                         "permission": [
#                             "Only administrators can delete projects."
#                         ]
#                     }
#                 },
#                 status=status.HTTP_403_FORBIDDEN
#             )

#         project = self.get_object()
#         project_name = project.name
#         self.perform_destroy(project)

#         return Response(
#             {
#                 "success": True,
#                 "message": f'Project "{project_name}" was deleted successfully.'
#             },
#             status=status.HTTP_200_OK
#         )


#     #  new to manipulate


#     @action(detail=True, methods=['get', 'post'])
#     def comments(self, request, pk=None):
#         """Get all comments or create a new comment for a specific project"""
#         project = self.get_object()
        
#         if request.method == 'GET':
#             comments = project.comments.filter(project=project.id).select_related('user').order_by('-created_at')
#             serializer = ProjectCommentSerializer(comments, many=True)
#             return Response(serializer.data)
        
#         elif request.method == 'POST':
#             serializer = ProjectCommentSerializer(data={
#                 'project': project.id, 
#                 'content': request.data.get('content'),
#                 **request.data
#             })
#             if serializer.is_valid():
#                 serializer.save(user=request.user, project=project)
#                 return Response(serializer.data, status=status.HTTP_201_CREATED)
#             return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



#     @action(detail=True, methods=['get', 'post'])
#     def notes(self, request, pk=None):
#         """Get all notes or create a new note for a project"""
#         project = self.get_object()
        
#         if request.method == 'GET':
#             notes = project.notes.all()
#             serializer = ProjectNoteSerializer(notes, many=True)
#             return Response(serializer.data)
        
#         elif request.method == 'POST':
#             serializer = ProjectNoteSerializer(data={'project': project.id, **request.data})
#             if serializer.is_valid():
#                 serializer.save(user=request.user)
#                 return Response(serializer.data, status=status.HTTP_201_CREATED)
#             return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


#     @action(detail=True, methods=['patch'], url_path='update_progress')
#     def update_progress(self, request, pk=None):
#         """Update project progress and/or status"""
#         project = self.get_object()
        
#         progress = request.data.get('progress')
#         status_value = request.data.get('status')
        
#         if progress is not None:
#             project.progress = progress
#         if status_value:
#             project.status = status_value
        
#         project.save()
        
#         return Response({
#             'success': True,
#             'message': 'Progress updated successfully',
#             'progress': project.progress,
#             'status': project.status
#         })


#     @action(detail=True, methods=['post'], url_path='mark_complete')
#     def mark_complete(self, request, pk=None):
#         """Mark project as completed"""
#         project = self.get_object()
#         project.status = 'completed'
#         project.progress = 100.0
#         project.save()
#         move_project_to_review(project)

        
#         return Response({
#             'success': True,
#             'message': 'Project marked as complete'
#         })


#     @action(detail=True, methods=['post'], url_path='transfer_ownership')
#     def transfer_ownership(self, request, pk=None):
#         """Transfer project ownership to another user"""
#         project = self.get_object()
#         new_owner_id = request.data.get('new_owner_id')
        
#         if not new_owner_id:
#             return Response(
#                 {'success': False, 'message': 'new_owner_id is required'},
#                 status=status.HTTP_400_BAD_REQUEST
#             )
        
#         try:
#             from django.contrib.auth import get_user_model
#             User = get_user_model()
#             new_owner = User.objects.get(id=new_owner_id)
#             project.owner = new_owner
#             project.save()
            
#             return Response({
#                 'success': True,
#                 'message': f'Ownership transferred to {new_owner.get_full_name()}'
#             })
#         except User.DoesNotExist:
#             return Response(
#                 {'success': False, 'message': 'User not found'},
#                 status=status.HTTP_404_NOT_FOUND
#             )

#     @action(detail=True, methods=['post'], url_path='notify-supervisor')
#     def notify_supervisor(self, request, pk=None):
#         project = self.get_object()
#         message = request.data.get('message', '').strip()

#         if not message:
#             return Response(
#                 {"detail": "Message is required"},
#                 status=status.HTTP_400_BAD_REQUEST
#             )

#         supervisors = project.supervisors.all()

#         if not supervisors.exists():
#             return Response(
#                 {"detail": "This project has no assigned supervisors"},
#                 status=status.HTTP_400_BAD_REQUEST
#             )

#         try:
#             sender_name = request.user.get_full_name() or request.user.email
#             recipient_emails = [s.email for s in supervisors if s.email]

#             # 🔔 MARK AS NOTIFIED (PERSIST)
#             project.notify_supervisor = True
#             project.save(update_fields=["notify_supervisor", "updated_at"])
#             move_project_to_review(project)

#             # 🔍 DEBUG OUTPUT
#             print("==== NOTIFY SUPERVISORS DEBUG ====")
#             print("Project:", project.id, project.name)
#             print("Sender:", sender_name)
#             print("Supervisors:", [s.get_full_name() or s.email for s in supervisors])
#             print("Recipient emails:", recipient_emails)
#             print("Message:")
#             print(message)
#             print("=================================")

#             return Response({
#                 "success": True,
#                 "notified_count": len(recipient_emails),
#                 "notify_supervisor": project.notify_supervisor,
#                 "supervisors": [
#                     s.get_full_name() or s.email for s in supervisors
#                 ],
#             })

#         except Exception as e:
#             print("❌ NOTIFY SUPERVISOR ERROR:", str(e))
#             return Response(
#                 {"detail": str(e)},
#                 status=status.HTTP_500_INTERNAL_SERVER_ERROR
#             )


# class MilestoneViewSet(viewsets.ModelViewSet):
#     """
#     Milestones for projects the user has access to (via ownership or RACI)
#     """
#     serializer_class = MilestoneSerializer
#     permission_classes = [IsAuthenticated]
#     filter_backends = [DjangoFilterBackend]
#     filterset_fields = ['is_completed', 'project'] 
#     ordering_fields = ['due_date', 'created_at']
#     ordering = ['due_date']

#     def get_queryset(self):
#         user = self.request.user

#         if user.is_staff:
#             return Milestones.objects.all().select_related('project')

#         return Milestones.objects.filter(
#             Q(project__owner=user) | Q(project__raci_assignments__user=user)
#         ).distinct().select_related('project')

#     @action(detail=True, methods=['get', 'post'])
#     def comments(self, request, pk=None):
#         """Get all comments or create a new comment for a specific milestone"""
#         milestone = self.get_object()
        
#         if request.method == 'GET':
#             comments = milestone.comments.filter(
#                 milestone_id=milestone.id
#             ).select_related('user').order_by('-created_at')
            
#             serializer = MilestoneCommentSerializer(comments, many=True)
#             return Response(serializer.data)
        
#         elif request.method == 'POST':
#             serializer = MilestoneCommentSerializer(
#                 data={'milestone': milestone.id, 'content': request.data.get('content')}
#             )
#             if serializer.is_valid():
#                 # Explicitly set both user and milestone
#                 serializer.save(user=request.user, milestone=milestone)
#                 return Response(serializer.data, status=status.HTTP_201_CREATED)
#             return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# class ProjectDocumentViewSet(viewsets.ModelViewSet):
#     """
#     ViewSet for project documents with role-based access control.
#     """
#     serializer_class = ProjectDocumentSerializer
#     permission_classes = [IsAuthenticated]
#     ordering = ['-created_at']

#     def get_queryset(self):
#         user = self.request.user
        
#         if user.is_staff:
#             return ProjectDocument.objects.all().select_related(
#                 'project', 'project__owner', 'uploaded_by'
#             )
        
#         return ProjectDocument.objects.filter(
#             Q(project__owner=user) | Q(project__raci_assignments__user=user)
#         ).distinct().select_related(
#             'project', 'project__owner', 'uploaded_by'
#         )

#     def perform_create(self, serializer):
#         serializer.save(uploaded_by=self.request.user)

#     @action(detail=False, methods=['get'])
#     def by_project(self, request):
#         """Get all documents for a specific project"""
#         project_id = request.query_params.get('project_id')
#         if not project_id:
#             return Response(
#                 {'error': 'project_id parameter required'}, 
#                 status=status.HTTP_400_BAD_REQUEST
#             )
        
#         docs = self.get_queryset().filter(project_id=project_id)
#         serializer = self.get_serializer(docs, many=True)
#         return Response(serializer.data)


# class RACIAssignmentViewSet(viewsets.ModelViewSet):
#     """
#     Optional: Direct CRUD on RACI assignments (if you want fine-grained control)
#     """
#     serializer_class = RACIAssignmentSerializer
#     permission_classes = [IsAuthenticated]

#     def get_queryset(self):
#         user = self.request.user

#         if user.is_staff:
#             return RACIAssignment.objects.all().select_related('project', 'user')

#         # Users can see assignments on projects they are part of
#         return RACIAssignment.objects.filter(
#             Q(project__owner=user) | Q(project__raci_assignments__user=user) | Q(user=user)
#         ).distinct().select_related('project', 'user')



# class ProjectReviewViewSet(ModelViewSet):
#     """
#     ViewSet for managing project reviews.
    
#     Access rules:
#     - Admin: sees all completed projects where notify_supervisor=True
#     - Supervisor: sees projects where they are informed (project team member)
#     - Owner: sees their own project reviews
#     """
#     permission_classes = [IsAuthenticated]
#     serializer_class = ProjectReviewSerializer
#     filter_backends = [DjangoFilterBackend]
#     filterset_fields = ['status', 'project', 'reviewer', 'is_closed']

#     def get_queryset(self):
#         """
#         Filter reviews based on user role:
#         - Admin: all reviews for projects with notify_supervisor=True or status of completed
#         - Supervisor/Informed users: reviews for projects they're assigned to
#         - Regular users: their own project reviews
#         """
#         user = self.request.user

                
#         if user.is_admin():
#             return ProjectReview.objects.filter(
#                 project__status__iexact="completed"
#             ) | ProjectReview.objects.filter(
#                 project__notify_supervisor=True
#             )

#         if user.is_supervisor():
#             return ProjectReview.objects.filter(
#                 Q(project__notify_supervisor=True) |
#                 Q(project__status__iexact="completed"),
#                 Q(project__team_members=user) |
#                 Q(project__owner=user)
#             ).distinct()        
                
        
#         return ProjectReview.objects.filter(project__owner=user)

#     def perform_create(self, serializer):
#         """Auto-assign created_by to current user"""
#         serializer.save(created_by=self.request.user)

#     @action(detail=True, methods=['post'])
#     def assign_reviewer(self, request, pk=None):
#         """
#         Assign a reviewer to the project review.
#         Only admin/supervisor can assign reviewers.
#         """
#         review = self.get_object()
        
#         if not (request.user.is_admin() or request.user.is_supervisor()):
#             return Response({"message": "Permission denied"}, status=403)
        
#         reviewer_id = request.data.get('reviewer_id')
#         if not reviewer_id:
#             return Response({"message": "reviewer_id is required"}, status=400)
        
#         review.reviewer_id = reviewer_id
#         review.status = ProjectReviewStatus.ON_REVIEW
#         review.save()
        
#         return Response({
#             "success": True,
#             "message": "Reviewer assigned successfully",
#             "data": ProjectReviewSerializer(review).data
#         })

#     @action(detail=True, methods=['post'])
#     def approve(self, request, pk=None):
#         """
#         Mark review as successfully reviewed.
#         Only assigned reviewer, admin, or supervisor can approve.
#         """
#         review = self.get_object()
        
#         is_reviewer = review.reviewer == request.user
#         is_authorized = request.user.is_admin() or request.user.is_supervisor()
        
#         if not (is_reviewer or is_authorized):
#             return Response({"message": "Permission denied"}, status=403)
        
#         if review.status == ProjectReviewStatus.SUCCESSFULLY_REVIEWED:
#             return Response({"message": "Already approved"}, status=400)
        
#         review.status = ProjectReviewStatus.SUCCESSFULLY_REVIEWED
#         review.review_summary = request.data.get('summary', review.review_summary)
#         review.reviewed_at = timezone.now()
#         review.save()
        
#         return Response({
#             "success": True,
#             "message": "Review approved successfully",
#             "data": ProjectReviewSerializer(review).data
#         })

#     @action(detail=True, methods=['post'])
#     def request_changes(self, request, pk=None):
#         """
#         Request changes to the project.
#         Only assigned reviewer, admin, or supervisor can request changes.
#         """
#         review = self.get_object()
        
#         is_reviewer = review.reviewer == request.user
#         is_authorized = request.user.is_admin() or request.user.is_supervisor()
        
#         if not (is_reviewer or is_authorized):
#             return Response({"message": "Permission denied"}, status=403)
        
#         review.status = ProjectReviewStatus.CHANGES_REQUESTED
#         review.review_summary = request.data.get('summary', '')
#         review.save()
        
#         return Response({
#             "success": True,
#             "message": "Changes requested",
#             "data": ProjectReviewSerializer(review).data
#         })

#     @action(detail=True, methods=['post'])
#     def close(self, request, pk=None):
#         """
#         Mark review as closed/completed.
#         Only admin or supervisor can close reviews.
#         """
#         review = self.get_object()
        
#         if not (request.user.is_admin() or request.user.is_supervisor()):
#             return Response({"message": "Permission denied"}, status=403)
        
#         if review.is_closed:
#             return Response({"message": "Review already closed"}, status=400)
        
#         review.is_closed = True
#         review.closed_at = timezone.now()
#         review.save()
        
#         return Response({
#             "success": True,
#             "message": "Review closed successfully",
#             "data": ProjectReviewSerializer(review).data
#         })


# class ProjectReviewCommentViewSet(ModelViewSet):
#     """
#     ViewSet for managing comments on project reviews.
    
#     Users can only comment on reviews they have access to.
#     Comments support threading via parent_comment field.
#     """
#     permission_classes = [IsAuthenticated]
#     serializer_class = ProjectReviewCommentSerializer
#     filter_backends = [DjangoFilterBackend]
#     filterset_fields = ['review', 'user', 'is_resolved', 'parent_comment']

#     def get_queryset(self):
#         """Filter comments based on reviews the user can access"""
#         user = self.request.user
        
#         # Get accessible review IDs based on user permissions
#         if user.is_admin():
#             accessible_reviews = ProjectReview.objects.filter(
#                 project__notify_supervisor=True
#             ).values_list('id', flat=True)
#         elif user.is_supervisor():
#             accessible_reviews = ProjectReview.objects.filter(
#                 project__team_members=user
#             ).values_list('id', flat=True) | ProjectReview.objects.filter(
#                 project__owner=user
#             ).values_list('id', flat=True)
#         else:
#             accessible_reviews = ProjectReview.objects.filter(
#                 project__owner=user
#             ).values_list('id', flat=True)
        
#         return ProjectReviewComment.objects.filter(review_id__in=accessible_reviews)

#     def perform_create(self, serializer):
#         """Auto-assign user to current user"""
#         serializer.save(user=self.request.user)

#     @action(detail=True, methods=['post'])
#     def resolve(self, request, pk=None):
#         """
#         Mark a comment as resolved.
#         Only comment author, reviewer, admin, or supervisor can resolve.
#         """
#         comment = self.get_object()
#         review = comment.review
        
#         is_author = comment.user == request.user
#         is_reviewer = review.reviewer == request.user
#         is_authorized = request.user.is_admin() or request.user.is_supervisor()
        
#         if not (is_author or is_reviewer or is_authorized):
#             return Response({"message": "Permission denied"}, status=403)
        
#         comment.is_resolved = True
#         comment.save()
        
#         return Response({
#             "success": True,
#             "message": "Comment marked as resolved successfully",
#             "data": ProjectReviewCommentSerializer(comment).data
#         })















# class TaskViewSet(ModelViewSet):
#     """Task CRUD operations"""
#     permission_classes = [IsAuthenticated]
#     filter_backends = ['django_filters.rest_framework.DjangoFilterBackend']
#     filterset_fields = ['project', 'status', 'priority']

#     def get_queryset(self):
#         return Task.objects.filter(project__collaborators=self.request.user) | \
#                Task.objects.filter(project__owner=self.request.user)

#     def get_serializer_class(self):
#         if self.action == 'retrieve':
#             return TaskDetailSerializer
#         return TaskListSerializer

