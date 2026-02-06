"""
Handles operations and business logic for:
- Employee-Supervisor relationships
- Employment contracts
- Leave allocations
- Holidays
- Leave requests and approvals
"""

import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q,Sum
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_date
from datetime import date, timedelta

from accounts.models import CustomUser
from employee.utils.timesheet import AttendanceService



logger = logging.getLogger(__name__)

User = get_user_model()


from employee.utils.leave_logic import calculate_working_days, get_leave_balance, validate_leave_request
from core.services.leave_emails import (notify_supervisor_leave_request, send_leave_approved_email, send_leave_cancelled_email, send_leave_rejected_email )
from projects.serializers import UserMinimalSerializer

from .models import (
    EmployeeSupervisor, EmployeeContract, 
    Holiday, LeaveRequest, LeaveGroup, LeaveStatus
)
from .serializers import (
    EmployeeSupervisorSerializer,
    EmployeeContractSerializer,
    
    HolidaySerializer,
    LeaveGroupSerializer,
    LeaveRequestCreateSerializer,
    LeaveRequestSerializer,
)


class EmployeeSupervisorViewSet(viewsets.ModelViewSet):
    """Manage employee-supervisor relationships"""
    serializer_class = EmployeeSupervisorSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        
        if user.is_staff:
            return EmployeeSupervisor.objects.all()
        return EmployeeSupervisor.objects.filter(
            Q(employee=user) | Q(supervisor=user)
        )
    
    
    @action(detail=False, methods=['get'])
    def my_supervisors(self, request):
        """Get current user's active supervisors"""
        supervisors = self.get_queryset().filter(
            employee=request.user,
            is_active=True
        )
        serializer = self.get_serializer(supervisors, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def my_team(self, request):
        """Get employees supervised by current user"""
        team = self.get_queryset().filter(
            supervisor=request.user,
            is_active=True
        )
        serializer = self.get_serializer(team, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='available-supervisors')
    def available_supervisors(self, request):
        """
        List all users with role=supervisor
        Used when assigning supervisors to employees
        """
        supervisors = User.objects.filter(
            role='supervisor'
            # is_active=True
        )
        serializer = UserMinimalSerializer(supervisors, many=True)
        return Response(serializer.data)




class LeaveGroupViewSet(viewsets.ModelViewSet):
    """Manage leave groups and entitlements"""
    serializer_class = LeaveGroupSerializer
    permission_classes = [IsAuthenticated]
    queryset = LeaveGroup.objects.all()
    
    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.is_staff:
            qs = qs.filter(is_active=True)
        return qs


class HolidayViewSet(viewsets.ModelViewSet):
    """Manage company and public holidays"""
    serializer_class = HolidaySerializer
    permission_classes = [IsAuthenticated]
    queryset = Holiday.objects.all()
    
    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        """Get upcoming holidays"""
        today = timezone.now().date()
        holidays = Holiday.objects.filter(date__gte=today).order_by('date')[:10]
        serializer = self.get_serializer(holidays, many=True)
        return Response(serializer.data)


# class EmployeeContractViewSet(viewsets.ModelViewSet):
#     """Manage employment contracts"""
#     serializer_class = EmployeeContractSerializer
#     permission_classes = [IsAuthenticated]
    
    
#     def get_queryset(self):
#         if self.request.user.is_staff:
#             return EmployeeContract.objects.select_related(
#                 'user', 'leave_group'
#             ).order_by('-is_current', '-start_date', 'user__first_name')
#         return EmployeeContract.objects.filter(user=self.request.user)
    
#     @action(detail=False, methods=['get'], url_path='all')
#     def all_contracts(self, request):
#         """Staff-only endpoint to get ALL contracts with full details"""
#         if not request.user.is_staff:
#             return Response({"detail": "Not authorized"}, status=403)
            
#         queryset = self.get_queryset()
#         serializer = self.get_serializer(queryset, many=True)
#         return Response(serializer.data)
    
#     def perform_create(self, serializer):
#         """Create contract and initialize leave allocation"""
#         contract = serializer.save()
#     #     self._initialize_leave_allocation(contract)
    
    
#     @action(detail=False, methods=['get'])
#     def current(self, request):
#         """Get current active contract for user"""
#         contract = self.get_queryset().filter(
#             user=request.user,
#             is_current=True
#         ).first()
        
#         if not contract:
#             return Response(
#                 {'detail': 'No active contract found'},
#                 status=status.HTTP_404_NOT_FOUND
#             )
        
#         serializer = self.get_serializer(contract)
#         return Response(serializer.data)

class EmployeeContractViewSet(viewsets.ModelViewSet):
    """
    Manage employment contracts with role-based permissions.
    
    Roles:
    - admin: Full access
    - office_admin: Create and Read only
    - Others: Read own contracts only
    """
    serializer_class = EmployeeContractSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Preserve existing queryset logic."""
        user = self.request.user
        if user.role in ['admin', 'office_admin']:
            return EmployeeContract.objects.select_related(
                'user', 'leave_group'
            ).order_by('-is_current', '-start_date', 'user__first_name')
        return EmployeeContract.objects.filter(user=user)
    
    def create(self, request, *args, **kwargs):
        """Only admin and office_admin can create."""
        if request.user.role not in ['admin', 'office_admin']:
            return Response(
                {'detail': 'Not authorized to perform this action'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().create(request, *args, **kwargs)
    
    def update(self, request, *args, **kwargs):
        """Only admin can update."""
        if request.user.role != 'admin':
            return Response(
                {'detail': 'Not authorized to perform this action'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().update(request, *args, **kwargs)
    
    def partial_update(self, request, *args, **kwargs):
        """Only admin can update."""
        if request.user.role != 'admin':
            return Response(
                {'detail': 'Not authorized to perform this action'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().partial_update(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        """Only admin can delete."""
        if request.user.role != 'admin':
            return Response(
                {'detail': 'Not authorized to perform this action'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)
    
    @action(detail=False, methods=['get'], url_path='all')
    def all_contracts(self, request):
        """Get all contracts - admin and office_admin only."""
        if request.user.role not in ['admin', 'office_admin']:
            return Response(
                {'detail': 'Not authorized'},
                status=status.HTTP_403_FORBIDDEN
            )
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def current(self, request):
        """Get current active contract for user - preserve existing logic."""
        contract = self.get_queryset().filter(
            user=request.user,
            is_current=True
        ).first()
        
        if not contract:
            return Response(
                {'detail': 'No active contract found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = self.get_serializer(contract)
        return Response(serializer.data)
    
    
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Deactivate contract - admin only."""
        if request.user.role != 'admin':
            return Response(
                {'detail': 'Not authorized to perform this action'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        contract = self.get_object()
        contract.is_current = False
        contract.save(update_fields=['is_current', 'updated_at'])
        
        serializer = self.get_serializer(contract)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate contract - admin only."""
        if request.user.role != 'admin':
            return Response(
                {'detail': 'Not authorized to perform this action'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        contract = self.get_object()
        contract.is_current = True
        contract.save(update_fields=['is_current', 'updated_at'])
        
        serializer = self.get_serializer(contract)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def mark_expired(self, request, pk=None):
        """Mark contract as expired - admin only."""
        if request.user.role != 'admin':
            return Response(
                {'detail': 'Not authorized to perform this action'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        contract = self.get_object()
        contract.is_expired = True
        contract.is_current = False
        contract.save(update_fields=['is_expired', 'is_current', 'updated_at'])
        
        serializer = self.get_serializer(contract)
        return Response(serializer.data)
    
    def perform_create(self, serializer):
        """Preserve existing create logic."""
        contract = serializer.save()

class LeaveRequestViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing leave requests.
    """
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return LeaveRequestCreateSerializer
        return LeaveRequestSerializer
    
    def get_queryset(self):
        user = self.request.user
        base_qs = LeaveRequest.objects.select_related('user', 'contract', 'supervisor')

        if user.is_admin():
            return base_qs

        # if user.is_supervisor():
        #     return base_qs.filter(supervisor=user)  

        return base_qs.filter(user=user)


    def create(self, request, *args, **kwargs):
        """
        Create a new leave request with validation.
        
        The backend automatically calculates days_requested based on:
        - ANNUAL: Working days (excludes weekends + holidays)
        - Others: Calendar days (includes weekends + holidays)
        
        Frontend should NOT send days_requested - it will be ignored.
        """
        user = request.user 
        
        # Get active contract
        contract = EmployeeContract.objects.filter(
            user=user,
            is_current=True,
            is_expired=False
        ).first()
        
        if not contract:
            return Response(
                {'error': 'No active contract found'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get request data
        leave_type = request.data.get('leave_type', 'ANNUAL').upper() 
        start_date = request.data.get('start_date')
        end_date = request.data.get('end_date')
        
        if not start_date or not end_date:
            return Response(
                {'error': 'Both start_date and end_date are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        days_requested = calculate_working_days(
            start_date,
            end_date,
            default_week_days=contract.default_week_days,
            leave_type=leave_type  
        )
        
        # Validate request
        is_valid, error_msg = validate_leave_request(
            user=user,
            contract=contract,
            leave_type=leave_type,
            start_date=start_date,
            end_date=end_date,
            days_requested=Decimal(str(days_requested))
        )
        
        if not is_valid:
            return Response(
                {'error': error_msg},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        data = request.data.copy()
        data['contract'] = contract.id
        data['days_requested'] = str(days_requested)
        
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=user) 
        
        try:
            notify_supervisor_leave_request(serializer.instance)
        except Exception as exc:
            logger.warning(
                f"Supervisor notification failed for leave {serializer.instance.id}: {exc}",
                exc_info=True,
            )
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)
        
    
    
    
    @action(detail=False, methods=['get'])
    def balance(self, request):
        """Get leave balance for current user."""
        user = request.user
        leave_type = request.query_params.get('leave_type', 'ANNUAL')
        
        # Get active contract
        contract = EmployeeContract.objects.filter(
            user=user,
            is_current=True,
            is_expired=False
        ).first()
        
        balance = get_leave_balance(user, contract, leave_type)
        
        return Response({
            'leave_type': leave_type,
            'balance': balance,
            'contract_id': str(contract.id) if contract else None
        })
    
    @action(detail=False, methods=['get'])
    def all_balances(self, request):
        """Get all leave balances for current user."""
        user = request.user

        contract = EmployeeContract.objects.filter(
            user=user,
            is_current=True,
            is_expired=False
        ).first()
        
        if not contract:
            return Response(
                {'error': 'No active contract found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        leave_types = ['ANNUAL', 'SICK', 'MATERNITY', 'PATERNITY', 'COMPASSIONATE', 'STUDY']
        balances = {}
        
        for leave_type in leave_types:
            balances[leave_type.lower()] = get_leave_balance(user, contract, leave_type)
            
        contract_info = {
                "contract_id": str(contract.id),
                "payroll_number": contract.payroll_number or "Not assigned",
                "contract_type": contract.contract_type,
                "start_date": contract.start_date.isoformat(),
                "end_date": contract.end_date.isoformat() if contract.end_date else None,
                "is_ongoing": contract.end_date is None,
               
            }
        
        return Response({
            'contract': contract_info,
            'balances': balances
        })
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve a leave request (supervisor only)."""
        leave_request = self.get_object()
        user = request.user
    
        if leave_request.supervisor != user and not user.is_admin():
            return Response(
                {'error': 'You are not authorized to approve this request'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        
        # Approve the request
        leave_request.status = 'APPROVED'
        leave_request.approved_by = user
        leave_request.approved_at = timezone.now()
        leave_request.supervisor_notes = request.data.get('notes', '')
        leave_request.save()
        
        try:
            send_leave_approved_email(leave)
        except Exception as exc:
            logger.warning(
                f"Leave approval email failed for leave : {exc}",
                exc_info=True,
            )
        
        serializer = self.get_serializer(leave_request)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject a leave request (supervisor only)."""
        leave_request = self.get_object()
        user = request.user
        
        if leave_request.supervisor != user and not user.is_admin():
            return Response(
                {'error': 'You are not authorized to reject this request'},
                status=status.HTTP_403_FORBIDDEN
   
                 )
        
 
        # Get rejection reason
        rejection_reason = request.data.get('rejection_reason')
        if not rejection_reason:
            return Response(
                {'error': 'Rejection reason is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Reject the request
        leave_request.status = 'REJECTED'
        leave_request.approved_by = user
        leave_request.approved_at = timezone.now()
        leave_request.rejection_reason = rejection_reason
        leave_request.supervisor_notes = request.data.get('notes', '')
        leave_request.save()
        
        try:
            send_leave_rejected_email(leave)
        except Exception as exc:
            logger.warning(
                f"Leave rejection email failed for leave : {exc}",
                exc_info=True,
            )
        
        serializer = self.get_serializer(leave_request)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel own leave request (if pending)."""
        leave_request = self.get_object()
        user = request.user
        
        if leave_request.user != user:
            return Response(
                {'error': 'You can only cancel your own requests'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if can be cancelled
        if leave_request.status not in ['PENDING', 'APPROVED']:
            return Response(
                {'error': 'Only pending or approved requests can be cancelled'},
                status=status.HTTP_400_BAD_REQUEST
            )
        # Cancel the request
        leave_request.status = 'CANCELLED'
        leave_request.save()
        
        try:
            send_leave_cancelled_email(leave)
        except Exception as exc:
            logger.warning(
                f"Leave cancellation email for leave {leave.id}: {exc}",
                exc_info=True,
            )
        

        serializer = self.get_serializer(leave_request)
        return Response(serializer.data)
    
    
    
    @action(detail=False, methods=['get'])
    def all_employees_balances(self, request):
        """Get leave balances for all employees (admin and office admin only)."""
        user = request.user

        if not (user.is_admin() or user.is_office_admin()):
            return Response(
                {'error': 'You are not authorized to access this information'},
                status=status.HTTP_403_FORBIDDEN
            )

        leave_types = ['ANNUAL', 'SICK', 'MATERNITY', 'PATERNITY', 'COMPASSIONATE', 'STUDY']
        # activ_contracts = EmployeeContract.objects.filter(
        #     is_current=True, is_expired=False
        # ).select_related('user')
        all_contracts = EmployeeContract.objects.select_related('user')
        all_balances = []
        for contract in all_contracts:
            balances = {}
            for leave_type in leave_types:
                balances[leave_type.lower()] = get_leave_balance(contract.user, contract, leave_type)
            employee_info = {
                'user_id': contract.user.id,
                'username': contract.user.username,
                'full_name': contract.user.get_full_name() if hasattr(contract.user, 'get_full_name') else f"{contract.user.first_name} {contract.user.last_name}",
                'email': contract.user.email,
                'contract': {
                    "contract_id": str(contract.id),
                    "payroll_number": contract.payroll_number or "Not assigned",
                    "contract_type": contract.contract_type,
                    "start_date": contract.start_date.isoformat(),
                    "end_date": contract.end_date.isoformat() if contract.end_date else None,
                    "is_ongoing": contract.end_date is None,
                },
                'balances': balances
            }
            all_balances.append(employee_info)
        return Response({'employees': all_balances})
    
    


class AttendanceViewSet(viewsets.ViewSet):
    """
    ViewSet for attendance operations.
    """
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        """
        Get daily attendance for all active users (excluding external members).
        Attendance starts from each user's creation date.
        
        Query Parameters:
        - start_date: Start date for attendance range (default: 2026-01-01)
        - end_date: End date for attendance range (default: today)
        """
        # Parse dates
        start_date = parse_date(request.query_params.get('start_date', '')) or date(2026, 1, 1)
        end_date = parse_date(request.query_params.get('end_date', ''))
        
        # Get all active users, excluding external members
        users = CustomUser.objects.filter(
            is_active=True,
            is_external_member=False
        ).select_related()  # Optimize query
        
        attendance_data = []
        for user in users:
            data = AttendanceService.get_attendance(str(user.id), start_date, end_date)
            
            # Only include if no error occurred
            if 'error' not in data:
                attendance_data.append(data)
        
        return Response(attendance_data)
    
    def retrieve(self, request, pk=None):
        """
        Get attendance for a specific user.
        
        Query Parameters:
        - start_date: Start date for attendance range
        - end_date: End date for attendance range
        """
        # Parse dates
        start_date = parse_date(request.query_params.get('start_date', ''))
        end_date = parse_date(request.query_params.get('end_date', ''))
        
        # Get attendance for specific user
        data = AttendanceService.get_attendance(pk, start_date, end_date)
        
        if 'error' in data:
            return Response(data, status=404)
        
        return Response(data)
    
  
  
    
    
     
     
     
     
     