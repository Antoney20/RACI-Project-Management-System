from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'mint'

router = DefaultRouter()
router.register(r'sprints', views.SprintViewSet, basename='sprint')

urlpatterns = [
    path('', include(router.urls)),
]