from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('auth/register/', views.RegisterView.as_view(), name='register'),
    path('auth/login/', views.LoginView.as_view(), name='login'),
    path('auth/logout/', views.LogoutView.as_view(), name='logout'),
    
    path('auth/verify/<uuid:user_id>/<str:token>/', views.EmailVerifyView.as_view(), name='email-verify'),
    
    path('auth/password-reset/', views.PasswordResetRequestView.as_view(), name='password-reset-request'),
    path('auth/password-reset-confirm/', views.PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
    path('auth/change-password/', views.ChangePasswordView.as_view(), name='change-password'),
    
    # User profile
    path('user/me/', views.user_me, name='user-me'),
]
