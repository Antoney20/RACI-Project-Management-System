from django.urls import include, path
from . import views
from rest_framework.routers import DefaultRouter


app_name = 'accounts'


router = DefaultRouter()
router.register(r'users', views.ManageUserViewSet, basename='manage-user')
router.register(r'profile', views.UserProfileViewSet, basename='user-profile')
router.register(r'settings', views.UserSettingsViewSet, basename='user-settings')
router.register(r'dashboard', views.DashboardStatsViewSet, basename='dashboard')  



urlpatterns = [
    path('auth/register/', views.RegisterView.as_view(), name='register'),
    path('auth/login/', views.LoginView.as_view(), name='login'),
    path('auth/logout/', views.LogoutView.as_view(), name='logout'),
    
    path('auth/verify/<uuid:user_id>/<str:token>/', views.EmailVerifyView.as_view(), name='email-verify'),
    
    path('auth/device/verify/', views.VerifyDeviceView.as_view(), name='device-verify'),
    path('auth/password-reset/', views.PasswordResetRequestView.as_view(), name='password-reset-request'),
    path('auth/password-reset-confirm/', views.PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
    path('auth/change-password/', views.ChangePasswordView.as_view(), name='change-password'),
    
    path('invite/', views.InviteUserView.as_view(), name='create-invite'),
    # path('invite/list/', views.ListInvitesView.as_view(), name='list-invites'),

    path('invite/verify/<str:token>/', views.VerifyInviteView.as_view(), name='verify-invite'),
    
    path('invite/accept/', views.AcceptInviteView.as_view(), name='accept-invite'),
    # User profile
    path('user/me/', views.user_me, name='user-me'),
    path('all/users/', views.user_list, name='user-list'),
    path('', include(router.urls)),
    
    # path('dashboard/', views.DashboardView.as_view(), name='dashboard'),

]
