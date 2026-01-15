
import logging
from rest_framework import status, generics,  viewsets, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework.views import APIView
from rest_framework import serializers

from rest_framework.decorators import action
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenBlacklistView as SimpleJWTTokenBlacklistView
from django.contrib.auth import authenticate, login
from django.contrib.auth.tokens import default_token_generator, PasswordResetTokenGenerator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.conf import settings
from django.utils import timezone

from django.db.models import Q, Count, Sum

from mint.models import LeaveAllocation, LeaveRequest
# MilestoneComment, Project, ProjectComment 


from .models import CustomUser, UserStatus
from .serializers import (
    AcceptInviteSerializer, CustomUserSerializer, InviteSerializer, RegisterSerializer, LoginSerializer, UserSerializer, UserDetailSerializer, UserListSerializer,
    PasswordResetRequestSerializer, PasswordResetConfirmSerializer,
    EmailVerifySerializer, ChangePasswordSerializer, LogoutSerializer
)
from core.services.emails_auth import (
    send_password_reset_email, send_password_change_confirmation
)
from core.services.invited import send_invite_email, send_invite_success_email

from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

logger = logging.getLogger(__name__)

class RegisterView(generics.CreateAPIView):
    """
    User registration - creates inactive account pending secretariate approval
    Sends acknowledgment email to user and notification to secretariate
    """
    queryset = CustomUser.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            user = serializer.save()
            user.is_active = False
            # user.status = UserStatus.PENDING
            user.verification_token = default_token_generator.make_token(user)
            user.save()

            # Send emails
            # send_user_acknowledgment_email(user)
            # send_secretariate_notification_email(user)

            logger.info(f"New user registered (pending verification): {user.email}")

            return Response({
                'success': True,
                'message': 'Registration successful. .',
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Registration error: {str(e)}")
            return Response({
                'success': False,
                'message': 'Registration failed. Please try again.',
                'errors': getattr(e, 'detail', str(e))
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class LoginView(APIView):
    """
    User login - returns access and refresh tokens
    Accepts username or email with password
    """
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            serializer = LoginSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            user = serializer.validated_data['user']

            # Generate tokens
            refresh = RefreshToken.for_user(user)
            access_token = refresh.access_token

            # Update last login
            user.last_login_at = timezone.now()
            user.failed_login_attempts = 0
            user.save(update_fields=['last_login_at', 'failed_login_attempts'])

            login(request, user)
            logger.info(f"User logged in: {user.email}")

            return Response({
                'success': True,
                'message': 'Login successful',
                'user': UserDetailSerializer(user).data,
                'tokens': {
                    'access': str(access_token),
                    'refresh': str(refresh)
                }
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            return Response({
                'success': False,
                'message': 'Login failed. Please try again.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class LogoutView(APIView):
    """User logout - blacklists refresh token"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            serializer = LogoutSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            refresh_token = serializer.validated_data['refresh']
            token = RefreshToken(refresh_token)
            token.blacklist()

            logger.info(f"User logged out: {request.user.email}")

            return Response({
                'success': True,
                'message': 'Logout successful'
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Logout error: {str(e)}")
            return Response({
                'success': False,
                'message': 'Logout failed. Please try again.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PasswordResetRequestView(generics.GenericAPIView):
    """Request password reset - sends email with reset link"""
    permission_classes = [AllowAny]
    serializer_class = PasswordResetRequestSerializer

    def post(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            email_or_username = serializer.validated_data['email_or_username'].strip()

            try:
                if '@' in email_or_username:
                    user = CustomUser.objects.get(email=email_or_username)
                else:
                    user = CustomUser.objects.get(username=email_or_username)
            except CustomUser.DoesNotExist:
                logger.warning(f"Password reset requested for non-existent user: {email_or_username}")
                # For security, don't reveal if user exists
                return Response({
                    'success': True,
                    'message': 'If an account exists with this information, you will receive a password reset email.'
                }, status=status.HTTP_200_OK)

            # Generate token
            token_generator = PasswordResetTokenGenerator()
            token = token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))

            # Create reset link
            frontend_url = getattr(settings, 'FRONTEND_URL', 'https://cema-africa.uonbi.ac.ke')
            reset_link = f"{frontend_url}/auth/reset-password?uid={uid}&token={token}"

            # Send email
            email_sent = send_password_reset_email(user, reset_link)

            if email_sent:
                logger.info(f"Password reset email sent to: {user.email}")
                return Response({
                    'success': True,
                    'message': 'If an account exists with this information, you will receive a password reset email.'
                }, status=status.HTTP_200_OK)
            else:
                logger.error(f"Failed to send password reset email to: {user.email}")
                return Response({
                    'success': False,
                    'message': 'Failed to send reset email. Please try again later.'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Exception as e:
            logger.error(f"Password reset request error: {str(e)}")
            return Response({
                'success': False,
                'message': 'An error occurred. Please try again.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PasswordResetConfirmView(generics.GenericAPIView):
    """Confirm password reset with token"""
    permission_classes = [AllowAny]
    serializer_class = PasswordResetConfirmSerializer

    def post(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            uid = serializer.validated_data['uid']
            token = serializer.validated_data['token']
            new_password = serializer.validated_data['new_password']

            # Decode user ID
            try:
                user_id = force_str(urlsafe_base64_decode(uid))
                user = CustomUser.objects.get(pk=user_id)
            except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
                return Response({
                    'success': False,
                    'message': 'Invalid reset link'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Validate token
            token_generator = PasswordResetTokenGenerator()
            if not token_generator.check_token(user, token):
                return Response({
                    'success': False,
                    'message': 'Invalid or expired reset link. Please request a new password reset.'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Set new password
            user.set_password(new_password)
            user.save()

            logger.info(f"Password reset successful for user: {user.email}")
            send_password_change_confirmation(user)

            return Response({
                'success': True,
                'message': 'Password has been reset successfully. You can now login with your new password.'
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Password reset confirm error: {str(e)}")
            return Response({
                'success': False,
                'message': 'An error occurred. Please try again.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_me(request):
    """Get current user profile"""
    return Response({
        'success': True,
        'user': UserDetailSerializer(request.user).data
    }, status=status.HTTP_200_OK)


class ChangePasswordView(generics.GenericAPIView):
    """Change password for authenticated user"""
    permission_classes = [IsAuthenticated]
    serializer_class = ChangePasswordSerializer

    def post(self, request):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            user = request.user
            old_password = serializer.validated_data['old_password']
            new_password = serializer.validated_data['new_password']

            if not user.check_password(old_password):
                return Response({
                    'success': False,
                    'message': 'Old password is incorrect.'
                }, status=status.HTTP_400_BAD_REQUEST)

            user.set_password(new_password)
            user.force_password_change = False
            user.save()

            logger.info(f"Password changed by user: {user.email}")
            send_password_change_confirmation(user)

            return Response({
                'success': True,
                'message': 'Password changed successfully.'
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Change password error: {str(e)}")
            return Response({
                'success': False,
                'message': 'An error occurred. Please try again.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class EmailVerifyView(generics.GenericAPIView):
    """Email link verification view: GET for validation, PATCH/PUT for approve/reject"""
    permission_classes = [AllowAny]
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer

    def get(self, request, user_id, token):
        """Validate token and return user data for review (no action taken)"""
        try:
            user = CustomUser.objects.get(id=user_id)
        except CustomUser.DoesNotExist:
            return Response({
                'success': False,
                'message': 'User not found.'
            }, status=status.HTTP_404_NOT_FOUND)

        # Verify token
        if not default_token_generator.check_token(user, token):
            return Response({
                'success': False,
                'message': 'Invalid or expired token.'
            }, status=status.HTTP_400_BAD_REQUEST)

   
        return Response({
            'success': True,
            'message': 'Token valid. User pending approval.',
            'user': UserSerializer(user).data
        }, status=status.HTTP_200_OK)

    def patch(self, request, user_id, token):
        """Handle user activation/approval via PATCH"""
        return self._handle_action(request, user_id, token)

    def put(self, request, user_id, token):
        """Alias for PATCH - handle user activation/approval via PUT"""
        return self._handle_action(request, user_id, token)

    def _handle_action(self, request, user_id, token):
        """Shared logic for approve/reject actions"""
        action = request.data.get('action')
        
        if action not in ['approve', 'reject']:
            return Response({
                'success': False,
                'message': 'Invalid action. Must be "approve" or "reject".'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = CustomUser.objects.get(id=user_id)
        except CustomUser.DoesNotExist:
            return Response({
                'success': False,
                'message': 'User not found.'
            }, status=status.HTTP_404_NOT_FOUND)

        # Verify token
        if not default_token_generator.check_token(user, token):
            return Response({
                'success': False,
                'message': 'Invalid or expired token.'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Check if user already processed
        if user.is_active and user.status == UserStatus.ACTIVE:
            return Response({
                'success': False,
                'message': 'User account has already been activated.'
            }, status=status.HTTP_400_BAD_REQUEST)

        if action == 'approve':
            user.is_active = True
            user.status = UserStatus.ACTIVE
            user.save()
            # send_verification_success_email(user)
            message = 'User account approved and activated successfully.'
            logger.info(f"User approved via email verification: {user.email}")
            
        else:  # reject
            user.status = UserStatus.BLOCKED  # Or UserStatus.REJECTED if defined
            user.is_active = False
            user.save()
            # send_rejection_email(user)
            message = 'User account rejected.'
            logger.info(f"User rejected via email verification: {user.email}")

        return Response({
            'success': True,
            'message': message,
            'user': UserSerializer(user).data
        }, status=status.HTTP_200_OK)



class ManageUserViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing users
    List, retrieve, update, block/unblock users
    """
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        """Use different serializer for list view"""
        if self.action == 'list':
            return UserListSerializer
        return CustomUserSerializer

    def get_queryset(self):
        """Filter queryset based on user role"""
        user = self.request.user

        if user.is_admin() or user.role == 'office_admin':
            return CustomUser.objects.all().order_by('-created_at')
        
        if user.is_supervisor():
            return CustomUser.objects.filter(
                Q(created_by=user) | Q(id=user.id)
            ).order_by('-created_at')
        
        return CustomUser.objects.filter(id=user.id)

    def update(self, request, *args, **kwargs):
        """Update user with permission check"""
        if not self._can_edit_users(request.user):
            return Response({
                "success": False,
                "message": "You don't have permission to edit users"
            }, status=status.HTTP_403_FORBIDDEN)
        
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            
            return Response({
                "success": True,
                "message": "User updated successfully",
                "data": serializer.data
            })
        except Exception as e:
            return Response({
                "success": False,
                "message": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def block(self, request, pk=None):
        """Block a user (admin/office_admin only)"""
        if not request.user.is_admin() and request.user.role != 'office_admin':
            return Response({
                "success": False,
                "message": "Permission denied"
            }, status=status.HTTP_403_FORBIDDEN)
        
        user = self.get_object()
        user.status = "blocked"
        user.is_active = False
        user.save()
        
        return Response({
            "success": True,
            "message": f"{user.username} has been blocked"
        })

    @action(detail=True, methods=['post'])
    def unblock(self, request, pk=None):
        """Unblock a user (admin/office_admin only)"""
        if not request.user.is_admin() and request.user.role != 'office_admin':
            return Response({
                "success": False,
                "message": "Permission denied"
            }, status=status.HTTP_403_FORBIDDEN)
        
        user = self.get_object()
        user.status = "active"
        user.is_active = True
        user.save()
        
        return Response({
            "success": True,
            "message": f"{user.username} has been unblocked"
        })

    def _can_edit_users(self, user):
        """Check if user can edit other users"""
        return user.is_admin() or user.role == 'office_admin'


class InviteUserView(generics.CreateAPIView):
    """
    Create and send invite to a new user
    POST /api/accounts/invite/
    """
    serializer_class = InviteSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        # Check if user has permission to invite
        if not (request.user.is_superuser or request.user.role in ['admin', 'office_admin']):
            return Response({
                "success": False,
                "message": "You do not have permission to invite users"
            }, status=status.HTTP_403_FORBIDDEN)

        serializer = self.get_serializer(data=request.data)
        
        try:
            serializer.is_valid(raise_exception=True)
            
            # Save invite user via serializer
            invite_user = serializer.save()
            
            # Generate invite link - Fixed variable name
            invite_link = f"{settings.FRONTEND_URL}/auth/accept-invite/{invite_user.invite_token}/"
            email_sent = send_invite_email(
                invite_user=invite_user,
                invite_link=invite_link,
                invited_by=request.user
            )

            return Response({
                "success": True,
                "message": "Invitation created successfully",
                "data": {
                    "user_id": invite_user.id,
                    "invite_link": invite_link,
                    "email": invite_user.email,
                    "role": invite_user.role,
                    "expires_at": invite_user.invite_expires_at.isoformat() if invite_user.invite_expires_at else None
                }
            }, status=status.HTTP_201_CREATED)
            
        except serializers.ValidationError as e:
            return Response({
                "success": False,
                "message": "Validation failed",
                "errors": e.detail
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            return Response({
                "success": False,
                "message": f"Failed to create invite: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class VerifyInviteView(generics.GenericAPIView):
    """
    Verify if an invite token is valid and return invite details
    GET /api/accounts/invite/verify/{token}/
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, token, *args, **kwargs):
        try:
            user = CustomUser.objects.get(
                invite_token=token,
                is_invited=True,
                is_active=False
            )
            
            # Check if invite has expired
            if user.invite_expires_at and user.invite_expires_at < timezone.now():
                return Response({
                    "is_valid": False,
                    "message": "This invitation link has expired. Please contact your administrator for a new invitation."
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Return invite details
            invited_by_name = "Unknown"
            if user.invited_by:
                invited_by_name = f"{user.invited_by.first_name} {user.invited_by.last_name}".strip() or user.invited_by.email
            
            return Response({
                "is_valid": True,
                "email": user.email,
                "role": user.role,
                "department": user.department or "",
                "position": user.position or "",
                "invited_by": invited_by_name,
                "invited_at": user.invited_at.isoformat() if hasattr(user, 'invited_at') and user.invited_at else None
            }, status=status.HTTP_200_OK)
            
        except CustomUser.DoesNotExist:
            return Response({
                "is_valid": False,
                "message": "Invalid invitation link. This link may have already been used or does not exist."
            }, status=status.HTTP_404_NOT_FOUND)


class AcceptInviteView(generics.GenericAPIView):
    """
    Accept an invite and activate user account
    POST /api/accounts/invite/accept/
    """
    serializer_class = AcceptInviteSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        
        try:
            serializer.is_valid(raise_exception=True)
            user = serializer.save()
            
            send_invite_success_email(user)
            
            return Response({
                "success": True,
                "message": "Account activated successfully! You can now log in.",
                "user_id": str(user.id),
                "email": user.email,
                "username": user.username
            }, status=status.HTTP_200_OK)
            
        except serializers.ValidationError as e:
            # Handle validation errors
            errors = {}
            if isinstance(e.detail, dict):
                errors = e.detail
            else:
                errors = {"error": str(e.detail)}
            
            return Response({
                "success": False,
                "message": "Validation failed",
                "errors": errors
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except CustomUser.DoesNotExist:
            return Response({
                "success": False,
                "message": "Invalid or expired invitation token"
            }, status=status.HTTP_404_NOT_FOUND)
            
        except Exception as e:
            return Response({
                "success": False,
                "message": f"An error occurred: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_list(request):
    """Return all users — admin, office admin, supervisor, staff."""
    users = CustomUser.objects.all()
    serializer = UserSerializer(users, many=True)
    return Response(serializer.data)






# class DashboardView(APIView):
#     """Unified dashboard - shows different data based on user role"""
#     permission_classes = [IsAuthenticated]
    
#     def get(self, request):
#         user = request.user
#         is_admin = user.is_staff or user.is_superuser
        
#         if is_admin:
#             return Response(self._get_admin_dashboard())
#         else:
#             return Response(self._get_user_dashboard(user))
    
#     def _get_user_dashboard(self, user):
#         """Dashboard for regular users"""
#         today = timezone.now()
#         current_year = today.year
        
#         # Projects
#         user_projects = Project.objects.filter(
#             Q(owner=user) | Q(raci_assignments__user=user)
#         ).distinct()
        
#         projects_list = []
#         for project in user_projects:
#             is_overdue = False
#             days_overdue = 0
            
#             if project.end_date and project.end_date < today:
#                 if project.status not in ['completed', 'cancelled']:
#                     is_overdue = True
#                     days_overdue = (today - project.end_date).days
            
#             duration = None
#             if project.start_date and project.end_date:
#                 duration = (project.end_date - project.start_date).days
            
#             projects_list.append({
#                 'id': str(project.id),
#                 'name': project.name,
#                 'status': project.status,
#                 'priority': project.priority,
#                 'duration_days': duration,
#                 'start_date': project.start_date,
#                 'end_date': project.end_date,
#                 'is_overdue': is_overdue,
#                 'days_overdue': days_overdue,
#                 'progress': project.progress,
#             })
        
#         # Leave stats
#         try:
#             leave_allocation = LeaveAllocation.objects.get(
#                 user=user, year=current_year
#             )
#             leave_stats = {
#                 'annual_total': leave_allocation.annual_leave_days,
#                 'annual_used': leave_allocation.annual_used,
#                 'annual_remaining': leave_allocation.annual_remaining,
#                 'sick_total': leave_allocation.sick_leave_days,
#                 'sick_used': leave_allocation.sick_used,
#                 'sick_remaining': leave_allocation.sick_remaining,
#             }
#         except LeaveAllocation.DoesNotExist:
#             leave_stats = {
#                 'annual_total': 0,
#                 'annual_used': 0,
#                 'annual_remaining': 0,
#                 'sick_total': 0,
#                 'sick_used': 0,
#                 'sick_remaining': 0,
#             }
        
#         # Recent activities
#         activities = self._get_user_activities(user)
        
#         return {
#             'user': {
#                 'id': user.id,
#                 'username': user.username,
#                 'full_name': user.get_full_name() or f"{user.first_name} {user.last_name}",
#                 'email': user.email,
#                 'last_login': user.last_login,
#             },
#             'projects': {
#                 'total': user_projects.count(),
#                 'list': projects_list,
#             },
#             'leave': leave_stats,
#             'recent_activities': activities,
#         }
    
#     def _get_admin_dashboard(self):
#         """Dashboard for admin users"""
#         today = timezone.now()
#         current_year = today.year
        
#         # All projects
#         all_projects = Project.objects.all()
#         projects_by_status = all_projects.values('status').annotate(
#             count=Count('id')
#         )
        
#         # Overdue projects
#         overdue_projects = []
#         for project in all_projects.filter(status__in=['pending', 'in_progress']):
#             if project.end_date and project.end_date < today:
#                 days_overdue = (today - project.end_date).days
#                 overdue_projects.append({
#                     'id': str(project.id),
#                     'name': project.name,
#                     'owner': project.owner.get_full_name(),
#                     'days_overdue': days_overdue,
#                     'end_date': project.end_date,
#                     'status': project.status,
#                 })
        
#         # Leave stats
#         leave_allocations = LeaveAllocation.objects.filter(year=current_year)
#         total_annual_allocated = leave_allocations.aggregate(
#             Sum('annual_leave_days')
#         )['annual_leave_days__sum'] or 0
        
#         total_annual_used = leave_allocations.aggregate(
#             Sum('annual_used')
#         )['annual_used__sum'] or 0
        
#         # Current leaves
#         current_leaves = LeaveRequest.objects.filter(
#             status='approved',
#             start_date__lte=today,
#             end_date__gte=today
#         ).select_related('user')
        
#         people_on_leave = [{
#             'user_id': leave.user.id,
#             'user': leave.user.get_full_name(),
#             'leave_type': leave.get_leave_type_display(),
#             'start_date': leave.start_date,
#             'end_date': leave.end_date,
#         } for leave in current_leaves]
        
#         pending_leaves = LeaveRequest.objects.filter(
#             status='pending'
#         ).count()
        
#         # User stats
#         total_users = User.objects.count()
#         active_users = User.objects.filter(is_active=True).count()
        
#         # Recent activities
#         activities = self._get_admin_activities()
        
#         return {
#             'overview': {
#                 'total_users': total_users,
#                 'active_users': active_users,
#                 'total_projects': all_projects.count(),
#                 'overdue_projects_count': len(overdue_projects),
#                 'people_on_leave_count': len(people_on_leave),
#                 'pending_leave_requests': pending_leaves,
#             },
#             'projects': {
#                 'total': all_projects.count(),
#                 'by_status': list(projects_by_status),
#                 'overdue': overdue_projects,
#             },
#             'leave': {
#                 'total_annual_allocated': total_annual_allocated,
#                 'total_annual_used': total_annual_used,
#                 'total_annual_remaining': total_annual_allocated - total_annual_used,
#                 'current_leaves': people_on_leave,
#                 'pending_requests': pending_leaves,
#             },
#             'recent_activities': activities,
#         }
    
#     def _get_user_activities(self, user):
#         """Get recent activities for a user"""
#         activities = []
        
#         # Recent comments
#         recent_project_comments = ProjectComment.objects.filter(
#             user=user
#         ).select_related('project').order_by('-created_at')[:5]
        
#         recent_milestone_comments = MilestoneComment.objects.filter(
#             user=user
#         ).select_related('milestone').order_by('-created_at')[:5]
        
#         # Recent leave requests
#         recent_leaves = LeaveRequest.objects.filter(
#             user=user
#         ).order_by('-created_at')[:5]
        
#         for comment in recent_project_comments:
#             activities.append({
#                 'type': 'comment',
#                 'action': 'Commented on project',
#                 'target': comment.project.name,
#                 'timestamp': comment.created_at,
#                 'details': comment.content[:100]
#             })
        
#         for comment in recent_milestone_comments:
#             activities.append({
#                 'type': 'milestone_comment',
#                 'action': 'Commented on milestone',
#                 'target': comment.milestone.title,
#                 'timestamp': comment.created_at,
#                 'details': comment.content[:100]
#             })
        
#         for leave in recent_leaves:
#             activities.append({
#                 'type': 'leave',
#                 'action': f'Leave request {leave.status}',
#                 'target': leave.get_leave_type_display(),
#                 'timestamp': leave.created_at,
#                 'details': f"{leave.num_days} days"
#             })
        
#         activities.sort(key=lambda x: x['timestamp'], reverse=True)
#         return activities[:10]
    
#     def _get_admin_activities(self):
#         """Get recent activities for admin view"""
#         activities = []
        
#         recent_comments = ProjectComment.objects.select_related(
#             'user', 'project'
#         ).order_by('-created_at')[:10]
        
#         recent_projects = Project.objects.select_related(
#             'owner'
#         ).order_by('-created_at')[:5]
        
#         for comment in recent_comments:
#             activities.append({
#                 'type': 'comment',
#                 'user': comment.user.get_full_name(),
#                 'user_id': comment.user.id,
#                 'action': 'Commented on project',
#                 'target': comment.project.name,
#                 'timestamp': comment.created_at,
#             })
        
#         for project in recent_projects:
#             activities.append({
#                 'type': 'project',
#                 'user': project.owner.get_full_name(),
#                 'user_id': project.owner.id,
#                 'action': 'Created project',
#                 'target': project.name,
#                 'timestamp': project.created_at,
#             })
        
#         activities.sort(key=lambda x: x['timestamp'], reverse=True)
#         return activities[:15]