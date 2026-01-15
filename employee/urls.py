"""
URL configuration for employee leave management app.

Routes:
- /supervisors/ - Employee-supervisor relationships
- /leave-groups/ - Leave group definitions
- /contracts/ - Employment contracts
- /allocations/ - Leave allocations and balances
- /holidays/ - Company/public holidays
- /leave-requests/ - Leave requests and approvals

Custom Actions:
- GET /supervisors/my_supervisors/ - Get user's supervisors
- GET /supervisors/my_team/ - Get supervised employees
- GET /contracts/current/ - Get current active contract
- GET /allocations/my_balance/ - Get comprehensive leave balance
- GET /holidays/upcoming/ - Get upcoming holidays
- POST /leave-requests/{id}/approve_reject/ - Approve/reject request
- GET /leave-requests/pending_approvals/ - Get requests to approve
- GET /leave-requests/my_requests/ - Get user's leave requests
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    EmployeeSupervisorViewSet,
    LeaveGroupViewSet,
    EmployeeContractViewSet,
    HolidayViewSet,
    LeaveRequestViewSet
)

app_name = 'employee'

router = DefaultRouter()

router.register(r'supervisors', EmployeeSupervisorViewSet, basename='supervisor')
router.register(r'leave-groups', LeaveGroupViewSet, basename='leave-group')
router.register(r'contracts', EmployeeContractViewSet, basename='contract')
# router.register(r'allocations', LeaveAllocationViewSet, basename='allocation')
router.register(r'holidays', HolidayViewSet, basename='holiday')
router.register(r'leave-requests', LeaveRequestViewSet, basename='leave-request')

urlpatterns = [
    path('v3/', include(router.urls)),
]