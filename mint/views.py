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
from rest_framework.exceptions import PermissionDenied

from django.db.models import Q

from core.utils.weekdays import calculate_business_days, get_business_days_in_range




from .models import LeaveStatus, Milestones, Project, ProjectDocument, Task,  LeaveRequest, LeaveAllocation, RACIAssignment
from .serializers import (
    ProjectCreateSerializer, ProjectDocumentSerializer, ProjectListSerializer, ProjectDetailSerializer, RACIAssignmentSerializer, TaskListSerializer,
    TaskDetailSerializer, MilestoneSerializer, LeaveRequestSerializer,
    LeaveAllocationSerializer
)
from django.utils import timezone
from rest_framework.permissions import AllowAny, IsAuthenticated



class LeaveRequestViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = LeaveRequestSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'leave_type', 'user']

    def get_queryset(self):
        user = self.request.user

        # Admins & supervisors see everything
        if user.is_supervisor() or user.is_admin():
            return LeaveRequest.objects.all()

        return LeaveRequest.objects.filter(user=user)

    def perform_create(self, serializer):
        user = self.request.user
        start = serializer.validated_data.get("start_date")
        end = serializer.validated_data.get("end_date")

        if LeaveRequest.objects.filter(user=user, status=LeaveStatus.PENDING).exists():
            raise serializers.ValidationError({
                "success": False,
                "status": "failed",
                "message": "You already have a leave request pending review."
            })

        # Check for overlapping approved leaves
        approved_leaves = LeaveRequest.objects.filter(
            user=user,
            status=LeaveStatus.APPROVED,
            start_date__lte=end,
            end_date__gte=start
        )
        
        if approved_leaves.exists():
            raise serializers.ValidationError({
                "success": False,
                "status": "failed",
                "message": "You already have an approved leave overlapping these dates."
            })
        
        # Calculate business days
        num_days = calculate_business_days(start.date(), end.date())
        
        current_year = timezone.now().year

        allocation = user.leave_allocations.filter(year=current_year).first()

        if not allocation:
            raise serializers.ValidationError({
                "success": False,
                "status": "failed",
                "message": "No leave allocation found for this year."
            })

        leave_type = serializer.validated_data.get("leave_type")
        
        # Get remaining days based on leave type
        remaining_days = 0
        if leave_type == "annual":
            remaining_days = allocation.annual_remaining
        elif leave_type == "sick":
            remaining_days = allocation.sick_remaining
        elif leave_type == "special":
            remaining_days = allocation.other_remaining
        elif leave_type == "unpaid":
            remaining_days = 999  # Unlimited unpaid leave
        
        if num_days > remaining_days:
            raise serializers.ValidationError({
                "success": False,
                "status": "failed",
                "message": (
                    f"Insufficient leave balance. You have {remaining_days} days remaining "
                    f"for {leave_type} leave, but requested {num_days} days."
                )
            })

        # Save with calculated business days
        serializer.save(user=user, num_days=num_days)

    def destroy(self, request, *args, **kwargs):
        leave = self.get_object()

        if leave.status in [LeaveStatus.APPROVED, LeaveStatus.REJECTED]:
            return Response({
                "success": False,
                "message": "You cannot delete approved or rejected leave requests."
            }, status=403)

        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        leave = self.get_object()

        if not (request.user.is_supervisor() or request.user.is_admin()):
            return Response({"message": "Not allowed : Permission denied to perform this action"}, status=403)

        if leave.status == LeaveStatus.APPROVED:
            return Response({
                "success": False,
                "message": "This leave request is already approved."
            }, status=400)

        # Update leave allocation to deduct days
        current_year = timezone.now().year
        allocation = leave.user.leave_allocations.filter(year=current_year).first()

        if not allocation:
            return Response({
                "success": False,
                "message": "No leave allocation found for this year."
            }, status=400)

        # Deduct days from allocation based on leave type
        if leave.leave_type == "annual":
            allocation.annual_used += leave.num_days
        elif leave.leave_type == "sick":
            allocation.sick_used += leave.num_days
        elif leave.leave_type == "special":
            allocation.other_used += leave.num_days
        # unpaid leaves don't affect allocation

        allocation.save()

        # Update leave request status
        leave.status = LeaveStatus.APPROVED
        leave.approved_by = request.user
        leave.approved_at = timezone.now()
        leave.save()

        return Response({
            "success": True,
            "message": "Leave approved",
            "data": LeaveRequestSerializer(leave).data
        })
        
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        leave = self.get_object()

        if not (request.user.is_supervisor() or request.user.is_admin()):
            return Response({"message": "Not allowed"}, status=403)

        if leave.status == LeaveStatus.REJECTED:
            return Response({
                "success": False,
                "message": "This leave request is already rejected."
            }, status=400)

        leave.status = LeaveStatus.REJECTED
        leave.rejection_reason = request.data.get("reason", "")
        leave.save()

        return Response({
            "success": True,
            "message": "Leave rejected",
            "data": LeaveRequestSerializer(leave).data
        })

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a leave request and restore days if it was approved"""
        leave = self.get_object()

        if leave.user != request.user and not (request.user.is_supervisor() or request.user.is_admin()):
            return Response({
                "success": False,
                "message": "You can only cancel your own leave."
            }, status=403)

        if leave.status == LeaveStatus.CANCELLED:
            return Response({
                "success": False,
                "message": "This leave request is already cancelled."
            }, status=400)

        # If cancelling an approved leave, restore the days
        if leave.status == LeaveStatus.APPROVED:
            current_year = timezone.now().year
            allocation = leave.user.leave_allocations.filter(year=current_year).first()

            if allocation:
                # Restore days to allocation based on leave type
                if leave.leave_type == "annual":
                    allocation.annual_used = max(0, allocation.annual_used - leave.num_days)
                elif leave.leave_type == "sick":
                    allocation.sick_used = max(0, allocation.sick_used - leave.num_days)
                elif leave.leave_type == "special":
                    allocation.other_used = max(0, allocation.other_used - leave.num_days)

                allocation.save()

        leave.status = LeaveStatus.CANCELLED
        leave.save()

        return Response({
            "success": True,
            "message": "Leave successfully cancelled",
            "data": LeaveRequestSerializer(leave).data
        })

    @action(detail=False, methods=['get'])
    def currently_on_leave(self, request):
        """
        Get all users currently on approved leave today.
        Counts only business days.
        """
        now = timezone.now().date()
        qs = self.get_queryset().filter(
            status=LeaveStatus.APPROVED,
            start_date__lte=now,
            end_date__gte=now
        )
        
        # Filter to only include business days
        current_leave = []
        for leave in qs:
            if leave.start_date.date().weekday() < 5 or leave.end_date.date().weekday() < 5:
                # Check if today is a business day within the leave period
                if now.weekday() < 5:  # Today is a business day
                    current_leave.append(leave)
        
        return Response(LeaveRequestSerializer(current_leave, many=True).data)

    @action(detail=False, methods=['get'])
    def all(self, request):
        """
        Get all leave requests for the current user or all if supervisor/admin.
        """
        user = request.user
        if user.is_supervisor() or user.is_admin():
            qs = LeaveRequest.objects.all()
        else:
            qs = LeaveRequest.objects.filter(user=user)

        return Response(LeaveRequestSerializer(qs, many=True).data)

    @action(detail=False, methods=['get'])
    def by_dates(self, request):
        """
        Get leave requests grouped by business days only.
        Returns a dictionary with dates as keys and leave data as values.
        Only includes business days (Monday-Friday).
        """
        qs = self.get_queryset()
        grouped = defaultdict(list)

        for leave in qs:
            if not leave.start_date or not leave.end_date:
                continue

            # Get only business days in the leave period
            business_days = get_business_days_in_range(
                leave.start_date.date(),
                leave.end_date.date()
            )

            leave_data = LeaveRequestSerializer(leave).data

            # Precompute user details once
            user_info = {
                "user_id": str(leave.user.id),
                "username": leave.user.username,
                "full_name": leave.user.full_name,
                "email": leave.user.email,
            }

            # Add leave to only business days
            for business_day in business_days:
                grouped[str(business_day)].append({
                    "user": user_info,
                    "leave": leave_data
                })
                
        return Response({
            "success": True,
            "grouped_by_date": dict(grouped)
        })

class LeaveAllocationViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = LeaveAllocationSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['year', 'user']

    def get_queryset(self):
        user = self.request.user

        if user.is_admin() or user.is_office_admin():
            return LeaveAllocation.objects.all()

        if user.is_supervisor() or user.is_staff_member():
            return LeaveAllocation.objects.filter(user=user)

        return LeaveAllocation.objects.none()

    def get_object(self):
        obj = super().get_object()
        user = self.request.user

        if user.is_admin() or user.is_office_admin():
            return obj

        if obj.user == user:
            return obj

        raise PermissionDenied("You do not have permission to view this allocation.")

    def permission_denied_message(self):
        return Response(
            {"success": False, "message": "You do not have permission to modify this allocation."},
            status=403
        )

    def perform_create(self, serializer):
        if not (self.request.user.is_admin() or self.request.user.is_office_admin()):
            raise PermissionDenied("You do not have permission to create leave allocations.")
        serializer.save()

    def perform_update(self, serializer):
        if not (self.request.user.is_admin() or self.request.user.is_office_admin()):
            raise PermissionDenied("You do not have permission to update this allocation.")
        serializer.save()

    def perform_destroy(self, instance):
        if not self.request.user.is_admin():
            raise PermissionDenied("Only admin can delete allocations.")
        instance.delete()

    @action(detail=False, methods=['get'])
    def current_year(self, request):
        year = timezone.now().year
        allocations = self.get_queryset().filter(year=year)
        return Response({
            'success': True,
            'year': year,
            'data': self.get_serializer(allocations, many=True).data
        })

    def update(self, request, *args, **kwargs):
        """Override update to give consistent API responses"""
        try:
            partial = kwargs.pop('partial', False)
            instance = self.get_object()   # This will trigger permission_denied correctly

            serializer = self.get_serializer(
                instance,
                data=request.data,
                partial=partial
            )
            serializer.is_valid(raise_exception=True)

            self.perform_update(serializer)

            return Response({
                "success": True,
                "message": "Leave allocation updated successfully.",
                "data": serializer.data
            }, status=200)

        except PermissionDenied:
            return Response({
                "success": False,
                "message": "You do not have permission to modify this leave allocation.",
                "errors": None
            }, status=403)

        except ValidationError as e:
            return Response({
                "success": False,
                "message": "Validation failed.",
                "errors": e.detail
            }, status=400)

        except Exception as e:
            return Response({
                "success": False,
                "message": "Something went wrong while updating leave allocation.",
                "errors": str(e)
            }, status=500)





class ProjectViewSet(viewsets.ModelViewSet):
    """
    Project CRUD operations.
    - Owner and users with RACI assignment can view/edit.
    - Admin/staff can see all.
    """
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status']
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'start_date', 'progress']
    ordering = ['-created_at']

    def get_queryset(self):
        user = self.request.user

        if user.is_staff:  # or user.is_admin() if you have custom method
            return Project.objects.all().select_related('owner').prefetch_related('raci_assignments__user')

        # Owner OR has RACI assignment on the project
        return Project.objects.filter(
            Q(owner=user) | Q(raci_assignments__user=user)
        ).distinct().select_related('owner').prefetch_related('raci_assignments__user')

    def get_serializer_class(self):
        if self.action == 'create':
            return ProjectCreateSerializer
        if self.action == 'retrieve':
            return ProjectDetailSerializer
        return ProjectListSerializer


    # def perform_create(self, serializer):
    #     serializer.save(owner=self.request.user)
    def perform_create(self, serializer):
        serializer.save()


    # Optional: Custom action to list or add RACI assignments
    @action(detail=True, methods=['get'])
    def raci(self, request, pk=None):
        project = self.get_object()
        assignments = project.raci_assignments.select_related('user').all()
        serializer = RACIAssignmentSerializer(assignments, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def assign_role(self, request, pk=None):
        """
        Assign a user a RACI role on this project.
        Expected data: { "user_id": "uuid", "raci_role": "Responsible" }
        """
        project = self.get_object()

        # Only owner or Accountable/Consulted? Or allow Responsible to invite? Adjust as needed.
        if not (project.owner == request.user or request.user.is_staff):
            return Response(
                {"detail": "Only project owner or staff can assign roles."},
                status=status.HTTP_403_FORBIDDEN
            )

        user_id = request.data.get('user_id')
        raci_role = request.data.get('raci_role')

        if not user_id or not raci_role:
            return Response(
                {"detail": "user_id and raci_role are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = CustomUser.objects.get(id=user_id)
        except CustomUser.DoesNotExist:
            return Response(
                {"detail": "User not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        assignment, created = RACIAssignment.objects.update_or_create(
            project=project,
            user=user,
            defaults={'raci_role': raci_role}
        )

        action_text = "created" if created else "updated"
        return Response({
            "success": True,
            "message": f"{user.get_full_name() or user.username} is now {raci_role} on this project.",
            "assignment_id": str(assignment.id)
        })

    @action(detail=True, methods=['delete'])
    def remove_role(self, request, pk=None):
        """
        Remove a user's RACI assignment from project.
        Expected query param or data: user_id
        """
        project = self.get_object()

        if not (project.owner == request.user or request.user.is_staff):
            return Response(
                {"detail": "Only project owner or staff can remove roles."},
                status=status.HTTP_403_FORBIDDEN
            )

        user_id = request.query_params.get('user_id') or request.data.get('user_id')
        if not user_id:
            return Response(
                {"detail": "user_id is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            assignment = project.raci_assignments.get(user_id=user_id)
            assignment.delete()
            return Response({"success": True, "message": "Role assignment removed."})
        except RACIAssignment.DoesNotExist:
            return Response(
                {"detail": "Assignment not found."},
                status=status.HTTP_404_NOT_FOUND
            )

    def destroy(self, request, *args, **kwargs):
        if not request.user.is_staff:
            return Response(
                {
                    "success": False,
                    "message": "You are not allowed to delete this project.",
                    "errors": {
                        "permission": [
                            "Only administrators can delete projects."
                        ]
                    }
                },
                status=status.HTTP_403_FORBIDDEN
            )

        project = self.get_object()
        project_name = project.name
        self.perform_destroy(project)

        return Response(
            {
                "success": True,
                "message": f'Project "{project_name}" was deleted successfully.'
            },
            status=status.HTTP_200_OK
        )

class MilestoneViewSet(viewsets.ModelViewSet):
    """
    Milestones for projects the user has access to (via ownership or RACI)
    """
    serializer_class = MilestoneSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['is_completed']
    ordering_fields = ['due_date', 'created_at']
    ordering = ['due_date']

    def get_queryset(self):
        user = self.request.user

        if user.is_staff:
            return Milestones.objects.all().select_related('project')

        return Milestones.objects.filter(
            Q(project__owner=user) | Q(project__raci_assignments__user=user)
        ).distinct().select_related('project')


class ProjectDocumentViewSet(viewsets.ModelViewSet):
    """
    Documents/Notes for projects the user has access to
    """
    serializer_class = ProjectDocumentSerializer
    permission_classes = [IsAuthenticated]
    # filter_backends = [OrderingFilter]
    ordering = ['-created_at']

    def get_queryset(self):
        user = self.request.user

        if user.is_staff:
            return ProjectDocument.objects.all().select_related('project', 'uploaded_by')

        return ProjectDocument.objects.filter(
            Q(project__owner=user) | Q(project__raci_assignments__user=user)
        ).distinct().select_related('project', 'uploaded_by')

    def perform_create(self, serializer):
        serializer.save(uploaded_by=self.request.user)


class RACIAssignmentViewSet(viewsets.ModelViewSet):
    """
    Optional: Direct CRUD on RACI assignments (if you want fine-grained control)
    """
    serializer_class = RACIAssignmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        if user.is_staff:
            return RACIAssignment.objects.all().select_related('project', 'user')

        # Users can see assignments on projects they are part of
        return RACIAssignment.objects.filter(
            Q(project__owner=user) | Q(project__raci_assignments__user=user) | Q(user=user)
        ).distinct().select_related('project', 'user')



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

