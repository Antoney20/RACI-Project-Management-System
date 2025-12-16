from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'mint'

router = DefaultRouter()
router.register(r'leave-requests', views.LeaveRequestViewSet, basename='leave-request')
router.register(r'leave-allocations', views.LeaveAllocationViewSet, basename='leave-allocation')
router.register(r'projects', views.ProjectViewSet, basename='project')
router.register(r'tasks', views.TaskViewSet, basename='task')
router.register(r'milestones', views.MilestoneViewSet, basename='milestone')
router.register(r'documents', views.ProjectDocumentViewSet, basename='documents')


urlpatterns = [
    path('', include(router.urls)),
]