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

from core.utils.weekdays import calculate_business_days, get_business_days_in_range




from .models import LeaveStatus, Project, Task, Milestone, LeaveRequest, LeaveAllocation
from .serializers import (
    ProjectListSerializer, ProjectDetailSerializer, TaskListSerializer,
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
            remaining_days = allocation.special_remaining
        elif leave_type == "unpaid":
            remaining_days = 000  
        
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

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        leave = self.get_object()

        if leave.status in [LeaveStatus.APPROVED, LeaveStatus.REJECTED]:
            return Response({
                "success": False,
                "message": "You cannot cancel an already approved or rejected leave."
            }, status=400)

        if leave.user != request.user:
            return Response({
                "success": False,
                "message": "You can only cancel your own leave."
            }, status=403)

        leave.status = LeaveStatus.CANCELLED
        leave.save()

        return Response({
            "success": True,
            "message": "Leave successfully cancelled",
            "data": LeaveRequestSerializer(leave).data
        })

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
            return Response({"message": "Not allowed"}, status=403)

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

        leave.status = LeaveStatus.REJECTED
        leave.rejection_reason = request.data.get("reason", "")
        leave.save()

        return Response({
            "success": True,
            "message": "Leave rejected",
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

class LeaveAllocationViewSet(viewsets.ModelViewSet):
    """Manage leave allocations - editable by admin/supervisors"""
    permission_classes = [IsAuthenticated]
    serializer_class = LeaveAllocationSerializer
    filterset_fields = ['year', 'user']

    def get_queryset(self):
        user = self.request.user
        if user.is_admin():
            return LeaveAllocation.objects.all()
        elif user.is_office_admin() or user.is_supervisor():
            return LeaveAllocation.objects.filter(user__in=user.supervised_team.all())
        return LeaveAllocation.objects.filter(user=user)

    def get_object(self):
        obj = super().get_object()
        user = self.request.user
        if user.is_admin() or (user.is_office_admin() or user.is_supervisor()) and obj.user in user.supervised_team.all() or obj.user == user:
            return obj
        self.permission_denied(self.request)

    def perform_create(self, serializer):
        if not self.request.user.is_admin():
            self.permission_denied(self.request)
        serializer.save()

    def perform_update(self, serializer):
        if not (self.request.user.is_admin() or self.request.user.is_office_admin() or self.request.user.is_supervisor()):
            self.permission_denied(self.request)
        serializer.save()

    def perform_destroy(self, instance):
        if not self.request.user.is_admin():
            self.permission_denied(self.request)
        instance.delete()


    @action(detail=False, methods=['get'])
    def current_year(self, request):
        """Get current year allocations"""
        year = timezone.now().year
        allocations = self.get_queryset().filter(year=year)
        return Response({'success': True, 'year': year, 'data': self.get_serializer(allocations, many=True).data})






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

