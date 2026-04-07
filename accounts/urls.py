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
    path('invite/resend/', views.ResendInviteView.as_view(), name='resend-invite'),
    # User profile
    path('user/me/', views.user_me, name='user-me'),
    path('all/users/', views.user_list, name='user-list'),
    path('', include(router.urls)),
    
    # path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
        # Team overview
    path('myteam/', views.MyTeamView.as_view(), name='myteam-overview'),
    
    # Team members management
    path('myteam/members/', views.MyTeamMembersView.as_view(), name='myteam-members'),
    path('myteam/members/<uuid:relationship_id>/', views.MyTeamMemberDetailView.as_view(), name='myteam-member-detail'),
    
    # Team data endpoints
    path('myteam/leave-requests/', views.MyTeamLeaveRequestsView.as_view(), name='myteam-leave-requests'),
    path('myteam/activities/', views.MyTeamActivitiesView.as_view(), name='myteam-activities'),
    path('myteam/reviews/', views.MyTeamReviewsView.as_view(), name='myteam-reviews'),
]



