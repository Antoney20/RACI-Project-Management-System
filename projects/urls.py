from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views


app_name = 'projects'

router = DefaultRouter()

# Sprint management
router.register(r'sprints', views.SprintViewSet, basename='sprint')

# Core project management
router.register(r'all', views.ProjectViewSet, basename='project')
router.register(r'milestones', views.ProjectMilestoneViewSet, basename='milestone')
router.register(r'members', views.ProjectMemberViewSet, basename='member')
router.register(r'materials', views.ProjectMaterialViewSet, basename='material')
router.register(r'comments', views.ProjectCommentViewSet, basename='comment')

urlpatterns = [
    path('', include(router.urls)),  
]