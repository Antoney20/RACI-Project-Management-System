from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'chat'

router = DefaultRouter()

router.register(r'groups', views.ChatGroupViewSet, basename='group')
router.register(r'conversations', views.ConversationViewSet, basename='conversation')
router.register(r'messages', views.MessageViewSet, basename='message')
router.register(r'pinned-messages', views.PinnedMessageViewSet, basename='pinned-message')
router.register(r'typing-status', views.TypingStatusViewSet, basename='typing-status')

urlpatterns = [
    path('', include(router.urls)),
]