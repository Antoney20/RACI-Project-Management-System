from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal

from projects.serializers import UserMinimalSerializer
from .models import (
    EmployeeSupervisor, EmployeeContract,
    Holiday, LeaveRequest, LeaveGroup
)

User = get_user_model()


class EmployeeSupervisorSerializer(serializers.ModelSerializer):
    """Employee-Supervisor relationships"""
    supervisor_details = UserMinimalSerializer(source='supervisor', read_only=True)
    employee_details = UserMinimalSerializer(source='employee', read_only=True)
    
    class Meta:
        model = EmployeeSupervisor
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class LeaveGroupSerializer(serializers.ModelSerializer):
    """Leave group definitions with entitlements"""
    
    class Meta:
        model = LeaveGroup
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class HolidaySerializer(serializers.ModelSerializer):
    """Holiday definitions"""
    
    class Meta:
        model = Holiday
        fields = '__all__'
        read_only_fields = ['id']
    



# class EmployeeContractSerializer(serializers.ModelSerializer):
#     """Employee contract with leave entitlements"""
#     user_details = UserMinimalSerializer(source='user', read_only=True)
#     leave_group_name = serializers.CharField(source='leave_group.name', read_only=True)
    
#     class Meta:
#         model = EmployeeContract
#         fields = '__all__'
#         read_only_fields = ['id', 'created_at', 'updated_at']
    
#     def validate(self, data):
#         """Validate contract dates and settings"""
#         start_date = data.get('start_date')
#         end_date = data.get('end_date')
        
#         if start_date and end_date and end_date < start_date:
#             raise serializers.ValidationError({
#                 'end_date': 'End date must be after start date'
#             })
        
#         return data



class EmployeeContractSerializer(serializers.ModelSerializer):
    """Serializer for employee contracts - minimal, preserves existing logic."""
    user_details = UserMinimalSerializer(source='user', read_only=True)
    leave_group_name = serializers.CharField(
        source='leave_group.name',
        read_only=True,
        allow_null=True
    )
    
    class Meta:
        model = EmployeeContract
        fields = [
            'id', 'user', 'user_details', 'payroll_number',
            'contract_type', 'leave_group', 'leave_group_name',
            'is_fte', 'fte_percentage', 'default_week_days',
            'contract_months', 'start_date', 'end_date',
            'is_current', 'is_expired', 'is_forfeited',
            'annual_carried_forward', 'annual_leave_used',
            'sick_leave_used', 'notes', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class LeaveRequestSerializer(serializers.ModelSerializer):
    """Full serializer for leave requests with all details."""
    user_details = UserMinimalSerializer(source='user', read_only=True)
    supervisor_details = UserMinimalSerializer(source='supervisor', read_only=True)
    approved_by_details = UserMinimalSerializer(source='approved_by', read_only=True)
    
    contract_type = serializers.CharField(source='contract.contract_type', read_only=True)
    leave_type_display = serializers.CharField(source='get_leave_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = LeaveRequest
        fields = '__all__'
        read_only_fields = [
            'id', 
            'created_at', 
            'updated_at',
            'approved_by',
            'approved_at',
            'programme_manager_approved',
            'programme_manager_approved_at'
        ]



class LeaveRequestCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating leave requests."""
    
    class Meta:
        model = LeaveRequest
        fields = [
            'id', 
            'user', 
            'contract',
            'leave_type', 
            'start_date', 
            'end_date', 
            'days_requested', 
            'details', 
            'supervisor'
        ]
        read_only_fields = ['id', 'user']
    
    def validate(self, data):
        """Validate leave request dates."""
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError({
                'end_date': 'End date must be after start date'
            })
        
        today = timezone.now().date()
        if start_date and start_date < today:
            raise serializers.ValidationError({
                'start_date': 'Start date cannot be in the past'
            })
        
        return data


class LeaveRequestListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing leave requests."""
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    supervisor_name = serializers.CharField(source='supervisor.get_full_name', read_only=True)
    leave_type_display = serializers.CharField(source='get_leave_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = LeaveRequest
        fields = [
            'id',
            'user',
            'user_name',
            'leave_type',
            'leave_type_display',
            'status',
            'status_display',
            'start_date',
            'end_date',
            'days_requested',
            'supervisor',
            'supervisor_name',
            'created_at'
        ]




