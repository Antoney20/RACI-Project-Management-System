from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'projects'

router = DefaultRouter()

# RACI project management
router.register(r'projects', views.ProjectViewSet, basename='project')
router.register(r'activities', views.ActivityViewSet, basename='activity')
router.register(r'milestones', views.MilestoneViewSet, basename='milestone')
router.register(r'documents', views.ActivityDocumentViewSet, basename='document')
router.register(r'user-priorities', views.UserActivityPriorityViewSet, basename='user-priority')
router.register(r"activity-reviews", views.ActivityReviewViewSet, basename="activity-reviews")
router.register(r"activity-reports", views.ActivityReportsViewSet, basename="activity-reports")

urlpatterns = [
    path('v2/', include(router.urls)),
]