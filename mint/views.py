from django.shortcuts import render

# Create your views here.
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework import viewsets
from rest_framework import status, generics
from django_filters.rest_framework import DjangoFilterBackend
from collections import defaultdict
from datetime import timedelta
from django.core.exceptions import ValidationError




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

        # Block if user has a pending leave
        if LeaveRequest.objects.filter(user=user, status=LeaveStatus.PENDING).exists():
            raise ValidationError("You already have a leave request pending review.")

        overlapping = LeaveRequest.objects.filter(
            user=user,
            status=LeaveStatus.APPROVED,
            start_date__lte=end,
            end_date__gte=start
        )
        if overlapping.exists():
            raise ValidationError("You already have an approved leave overlapping these dates.")

        serializer.save(user=user)

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
        now = timezone.now()
        qs = self.get_queryset().filter(
            status=LeaveStatus.APPROVED,
            start_date__lte=now,
            end_date__gte=now
        )
        return Response(LeaveRequestSerializer(qs, many=True).data)


    @action(detail=False, methods=['get'])
    def all(self, request):
        user = request.user
        if user.is_supervisor() or user.is_admin():
            qs = LeaveRequest.objects.all()
        else:
            qs = LeaveRequest.objects.filter(user=user)

        return Response(LeaveRequestSerializer(qs, many=True).data)


    @action(detail=False, methods=['get'])
    def by_dates(self, request):
        qs = self.get_queryset()
        grouped = defaultdict(list)

        for leave in qs:
            if not leave.start_date or not leave.end_date:
                continue

            cursor = leave.start_date.date()
            end = leave.end_date.date()

            leave_data = LeaveRequestSerializer(leave).data

            # Precompute user details once
            user_info = {
                "user_id": str(leave.user.id),
                "username": leave.user.username,
                "full_name": leave.user.full_name,
                "email": leave.user.email,
            }

            while cursor <= end:
                grouped[str(cursor)].append({
                    "user": user_info,
                    "leave": leave_data
                })
                cursor += timedelta(days=1)
                
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

