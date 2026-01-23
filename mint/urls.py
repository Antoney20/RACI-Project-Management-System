from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'mint'

router = DefaultRouter()
router.register(r'sprints', views.SprintViewSet, basename='sprint')
# router.register(r'leave-requests', views.LeaveRequestViewSet, basename='leave-request')
# router.register(r'leave-allocations', views.LeaveAllocationViewSet, basename='leave-allocation')
# router.register(r'projects', views.ProjectViewSet, basename='project')
# router.register(r'tasks', views.TaskViewSet, basename='task')
# router.register(r'milestones', views.MilestoneViewSet, basename='milestone')
# router.register(r'documents', views.ProjectDocumentViewSet, basename='documents')
# #admin reviews
# router.register(r'project-reviews', views.ProjectReviewViewSet, basename='project-review')
# router.register(r'review-comments', views.ProjectReviewCommentViewSet, basename='review-comment')


urlpatterns = [
    path('', include(router.urls)),
]