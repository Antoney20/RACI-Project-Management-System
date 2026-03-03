
import logging
import uuid
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
from django.shortcuts import get_object_or_404
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.conf import settings
from django.utils import timezone
from rest_framework.parsers import MultiPartParser, FormParser

from django.db.models import Q,F, Count, Sum

from accounts.permissions import IsSupervisorOrAdmin
from accounts.service.stats import DashboardStatsService
from accounts.service.team import MyTeamService
from accounts.utils.client import get_client_ip, get_user_agent, parse_user_agent
from employee.models import EmployeeSupervisor
from mint.models import LeaveAllocation, LeaveRequest
# MilestoneComment, Project, ProjectComment 


from .models import CustomUser, LoginAttempt, TrustedDevice, UserStatus
from .serializers import (
    AcceptInviteSerializer, CustomUserSerializer, InviteSerializer, LoginAttemptSerializer, ProfileImageSerializer, RegisterSerializer, LoginSerializer, TrustedDeviceSerializer, UserProfileSerializer, UserSerializer, UserDetailSerializer, UserListSerializer,
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
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        ip_address = get_client_ip(request)
        user_agent = get_user_agent(request)
        browser, os = parse_user_agent(user_agent)

        username_or_email = serializer.validated_data['username_or_email']
        password = serializer.validated_data['password']
        device_id = serializer.validated_data['device_id']

        user = CustomUser.objects.filter(
            Q(username__iexact=username_or_email) |
            Q(email__iexact=username_or_email)
        ).first()

        # ---------- USER NOT FOUND ----------
        if not user:
            LoginAttempt.objects.create(
                user=None,
                device_id=device_id,
                ip_address=ip_address,
                user_agent=user_agent,
                browser=browser,
                os=os,
                device_type=serializer.validated_data.get('device_type', 'other'),
                status='failed',
                payload={"reason": "user_not_found"},
            )
            return Response(
                {"success": False, "message": "Invalid credentials"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # ---------- INACTIVE ACCOUNT ----------
        if not user.is_active:
            LoginAttempt.objects.create(
                user=user,
                device_id=device_id,
                ip_address=ip_address,
                user_agent=user_agent,
                browser=browser,
                os=os,
                device_type=serializer.validated_data.get('device_type', 'other'),
                status='failed',
                payload={"reason": "inactive_account"},
            )
            return Response(
                {"success": False, "message": "Account inactive"},
                status=status.HTTP_403_FORBIDDEN
            )

        # ---------- WRONG PASSWORD ----------
        if not user.check_password(password):
            LoginAttempt.objects.create(
                user=user,
                device_id=device_id,
                ip_address=ip_address,
                user_agent=user_agent,
                browser=browser,
                os=os,
                device_type=serializer.validated_data.get('device_type', 'other'),
                status='failed',
                payload={"reason": "invalid_password"},
            )

            TrustedDevice.objects.filter(
                user=user,
                device_id=device_id
            ).update(failure_count=F('failure_count') + 1)

            return Response(
                {"success": False, "message": "Invalid credentials"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # ---------- TRUSTED DEVICE ----------
        device, _ = TrustedDevice.objects.get_or_create(
            user=user,
            device_id=device_id,
            defaults={
                'device_name': serializer.validated_data.get('device_name', ''),
                'device_type': serializer.validated_data.get('device_type', 'other'),
                'ip_address': ip_address,
                'user_agent': user_agent,
                'browser': browser,
                'os': os,
                'is_trusted': True,
            }
        )

        # ---------- SUSPICIOUS DEVICE ----------
        if device.is_suspicious:
            LoginAttempt.objects.create(
                user=user,
                device_id=device_id,
                ip_address=ip_address,
                user_agent=user_agent,
                browser=browser,
                os=os,
                device_type=device.device_type,
                status='blocked',
                payload={"reason": "device_flagged"},
            )

            return Response(
                {
                    "success": False,
                    "message": "Suspicious activity detected",
                    "needs_verification": True,
                    "verification_token": str(device.verification_token),
                },
                status=status.HTTP_403_FORBIDDEN
            )

        # ---------- SUCCESS ----------
        device.reset_failures()
        device.ip_address = ip_address
        device.user_agent = user_agent
        device.browser = browser
        device.os = os
        device.save(update_fields=[
            'ip_address', 'user_agent', 'browser', 'os', 'last_used_at'
        ])

        LoginAttempt.objects.create(
            user=user,
            device_id=device_id,
            ip_address=ip_address,
            user_agent=user_agent,
            browser=browser,
            os=os,
            device_type=device.device_type,
            status='success',
            payload={"login": "success"},
        )

        refresh = RefreshToken.for_user(user)
        login(request, user)

        return Response(
            {
                "success": True,
                "tokens": {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                },
            },
            status=status.HTTP_200_OK
        )


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
            # email_sent = send_invite_email(
            #     invite_user=invite_user,
            #     invite_link=invite_link,
            #     invited_by=request.user
            # )
            
            
            try:
                send_invite_email(
                    invite_user=invite_user,
                    invite_link=invite_link,
                    invited_by=request.user
                )
            except Exception as exc:
                logger.exception("Invite email failed", exc_info=exc)

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


class VerifyDeviceView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        token = request.data.get("token")

        try:
            device = TrustedDevice.objects.get(verification_token=token)
        except TrustedDevice.DoesNotExist:
            return Response({"success": False, "message": "Invalid or expired link"}, status=400)

        if device.is_expired_verification:
            return Response({"success": False, "message": "Verification link expired"}, status=410)

        if device.is_trusted:
            return Response({"success": True, "message": "Device already verified"}, status=200)

        if not TrustedDevice.can_add_more(device.user):
            return Response({
                "success": False,
                "message": "Maximum number of trusted devices reached. Please remove one first."
            }, status=403)

        device.is_trusted = True
        device.is_suspicious = False
        device.verification_token = None
        device.verification_expires_at = None
        device.save()

        return Response({
            "success": True,
            "message": "Device verified successfully. You can now log in."
        }, status=200)


class UserProfileViewSet(viewsets.GenericViewSet):
    """
    User profile management (current user)
    - GET    /accounts/profile/
    - PATCH  /accounts/profile/
    - POST   /accounts/profile/upload_image/
    - POST   /accounts/profile/change_password/
    """
    permission_classes = [IsAuthenticated]
    serializer_class = UserProfileSerializer

    # 🔑 Always operate on the current user
    def get_object(self):
        return self.request.user

    def get_queryset(self):
        return CustomUser.objects.filter(id=self.request.user.id)

    def list(self, request, *args, **kwargs):
        """Get current user profile"""
        serializer = self.get_serializer(self.get_object())
        return Response(serializer.data)

    def partial_update(self, request, *args, **kwargs):
        """Update user profile fields"""
        serializer = self.get_serializer(
            self.get_object(),
            data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @action(
        detail=False,
        methods=['post'],
        parser_classes=[MultiPartParser, FormParser],
        serializer_class=ProfileImageSerializer,
        url_path='upload_image'
    )
    def upload_image(self, request):
        """Upload/update profile image"""
        serializer = self.get_serializer(
            self.get_object(),
            data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({
            'message': 'Profile image updated successfully',
            'profile_image': serializer.data.get('profile_image')
        })

    @action(
        detail=False,
        methods=['post'],
        serializer_class=ChangePasswordSerializer,
        url_path='change_password'
    )
    def change_password(self, request):
        """Change user password"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = self.get_object()
        old_password = serializer.validated_data['old_password']
        new_password = serializer.validated_data['new_password']

        if not check_password(old_password, user.password):
            return Response(
                {'old_password': 'Current password is incorrect'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.set_password(new_password)
        user.force_password_change = False
        user.save(update_fields=['password', 'force_password_change'])

        return Response({
            'message': 'Password changed successfully'
        })



class UserSettingsViewSet(viewsets.GenericViewSet):
    """
    User settings and security management
    - GET devices: List trusted devices
    - POST devices/block: Block a device
    - GET activities: Last 10 login attempts
    - GET security_status: Email verification and account status
    """
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def devices(self, request):
        """List user's trusted devices"""
        devices = TrustedDevice.objects.filter(user=request.user)
        serializer = TrustedDeviceSerializer(devices, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='devices/block')
    def block_device(self, request):
        """Block a trusted device"""
        device_id = request.data.get('device_id')
        if not device_id:
            return Response(
                {'error': 'device_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            device = TrustedDevice.objects.get(
                user=request.user,
                device_id=device_id
            )
            device.is_trusted = False
            device.is_suspicious = True
            device.save(update_fields=['is_trusted', 'is_suspicious'])

            return Response({
                'message': 'Device blocked successfully',
                'device_id': device_id
            })
        except TrustedDevice.DoesNotExist:
            return Response(
                {'error': 'Device not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['get'])
    def activities(self, request):
        """Get last 10 login attempts"""
        attempts = LoginAttempt.objects.filter(
            user=request.user
        ).order_by('-created_at')[:10]
        
        serializer = LoginAttemptSerializer(attempts, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def security_status(self, request):
        """Get account security status"""
        user = request.user
        return Response({
            'email_verified': user.is_email_verified,
            'email_verified_at': user.email_verified_at,
            'account_status': user.status,
            'is_active': user.is_active,
            'force_password_change': user.force_password_change,
            'last_login': user.last_login_at,
            'failed_login_attempts': user.failed_login_attempts,
            'account_locked': user.account_locked_until is not None,
            'account_locked_until': user.account_locked_until,
        })





class DashboardStatsViewSet(viewsets.ViewSet):
    """
    Dashboard.
    
    Provides role-based dashboard data in a single call.
    """
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        """
        Get dashboard stats for current user.
        """
        user = request.user
        
        try:
            stats = DashboardStatsService.get_stats(user)
            
            return Response({
                'success': True,
                'user': {
                    'name': user.get_full_name() or user.username,
                    'email': user.email,
                    'role': getattr(user, 'role', 'staff'),
                },
                'data': stats,
                'generated_at': None  
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(
                f"Dashboard stats failed for user {user.id}: {e}",
                exc_info=True
            )
            
            return Response({
                'success': False,
                'error': 'Failed to generate dashboard statistics',
                'detail': str(e) if request.user.is_staff else None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    


class MyTeamView(APIView):
    """
    Team overview - all key stats in one call.
    
    GET /myteam/
    Returns:
        - Team member count
        - Members on leave today
        - Pending leave requests
        - Pending reviews
        - Overdue activities count
    """
    permission_classes = [IsSupervisorOrAdmin]
    
    def get(self, request):
        try:
            team_members = MyTeamService.get_team_members(request.user)
            leave_requests = MyTeamService.get_team_leave_requests(
                request.user,
                status_filter='pending'
            )
            pending_reviews = MyTeamService.get_pending_reviews(request.user)
            
            # Quick stats
            on_leave_count = sum(1 for m in team_members if m['on_leave']['status'])
            overdue_activities = sum(m['activities']['overdue'] for m in team_members)
            
            return Response({
                'success': True,
                'summary': {
                    'total_members': len(team_members),
                    'on_leave_today': on_leave_count,
                    'pending_leave_requests': len(leave_requests),
                    'pending_reviews': len(pending_reviews),
                    'overdue_activities': overdue_activities
                },
                'members_preview': team_members[:5],  # First 5 for overview
                'pending_leave_requests': leave_requests[:5],
                'pending_reviews': pending_reviews[:5]
            })
        
        except Exception as e:
            logger.error(f"MyTeam overview failed: {e}", exc_info=True)
            return Response({
                'success': False,
                'error': 'Failed to load team overview'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MyTeamMembersView(APIView):
    """
    Team member management.
    
    GET /myteam/members/ - List all members with detailed stats
    POST /myteam/members/ - Add new member to team
    """
    permission_classes = [IsSupervisorOrAdmin]
    
    def get(self, request):
        """List all team members with full details"""
        try:
            members = MyTeamService.get_team_members(request.user)
            
            return Response({
                'success': True,
                'count': len(members),
                'members': members
            })
        
        except Exception as e:
            logger.error(f"MyTeam members list failed: {e}", exc_info=True)
            return Response({
                'success': False,
                'error': 'Failed to load team members'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def post(self, request):
        """Add new member to team"""
        try:
            employee_id = request.data.get('employee_id')
            
            if not employee_id:
                return Response({
                    'success': False,
                    'error': 'employee_id is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if employee exists
            employee = get_object_or_404(User, id=employee_id)
            
            # Check if relationship already exists
            existing = EmployeeSupervisor.objects.filter(
                employee=employee,
                supervisor=request.user
            ).first()
            
            if existing:
                if existing.is_active:
                    return Response({
                        'success': False,
                        'error': 'This employee is already in your team'
                    }, status=status.HTTP_400_BAD_REQUEST)
                else:
                    # Reactivate
                    existing.is_active = True
                    existing.save()
                    relationship = existing
            else:
                # Create new relationship
                relationship = EmployeeSupervisor.objects.create(
                    employee=employee,
                    supervisor=request.user,
                    is_active=True
                )
            
            return Response({
                'success': True,
                'message': f'{employee.get_full_name()} added to your team',
                'relationship_id': str(relationship.id)
            }, status=status.HTTP_201_CREATED)
        
        except User.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Employee not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        except Exception as e:
            logger.error(f"Add team member failed: {e}", exc_info=True)
            return Response({
                'success': False,
                'error': 'Failed to add team member'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MyTeamMemberDetailView(APIView):
    """
    Individual team member management.
    
    DELETE /myteam/members/<relationship_id>/ - Remove from team
    """
    permission_classes = [IsSupervisorOrAdmin]
    
    def delete(self, request, relationship_id):
        """Remove member from team (soft delete)"""
        try:
            relationship = get_object_or_404(
                EmployeeSupervisor,
                id=relationship_id,
                supervisor=request.user
            )
            
            relationship.is_active = False
            relationship.save()
            
            return Response({
                'success': True,
                'message': 'Team member removed'
            })
        
        except Exception as e:
            logger.error(f"Remove team member failed: {e}", exc_info=True)
            return Response({
                'success': False,
                'error': 'Failed to remove team member'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MyTeamLeaveRequestsView(APIView):
    """
    Team leave request management.
    
    GET /myteam/leave-requests/?status=pending
    """
    permission_classes = [IsSupervisorOrAdmin]
    
    def get(self, request):
        try:
            status_filter = request.query_params.get('status', None)
            
            leave_requests = MyTeamService.get_team_leave_requests(
                request.user,
                status_filter=status_filter
            )
            
            return Response({
                'success': True,
                'count': len(leave_requests),
                'leave_requests': leave_requests
            })
        
        except Exception as e:
            logger.error(f"Team leave requests failed: {e}", exc_info=True)
            return Response({
                'success': False,
                'error': 'Failed to load leave requests'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MyTeamActivitiesView(APIView):
    """
    Team activities tracking.
    
    GET /myteam/activities/?status=in_progress&overdue_only=true
    """
    permission_classes = [IsSupervisorOrAdmin]
    
    def get(self, request):
        try:
            filters = {}
            
            if request.query_params.get('status'):
                filters['status'] = request.query_params.get('status')
            
            if request.query_params.get('overdue_only') == 'true':
                filters['overdue_only'] = True
            
            activities = MyTeamService.get_team_activities(request.user, filters)
            
            return Response({
                'success': True,
                'count': len(activities),
                'activities': activities
            })
        
        except Exception as e:
            logger.error(f"Team activities failed: {e}", exc_info=True)
            return Response({
                'success': False,
                'error': 'Failed to load team activities'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MyTeamReviewsView(APIView):
    """
    Pending supervisor reviews.
    
    GET /myteam/reviews/
    """
    permission_classes = [IsSupervisorOrAdmin]
    
    def get(self, request):
        try:
            reviews = MyTeamService.get_pending_reviews(request.user)
            
            return Response({
                'success': True,
                'count': len(reviews),
                'reviews': reviews
            })
        
        except Exception as e:
            logger.error(f"Team reviews failed: {e}", exc_info=True)
            return Response({
                'success': False,
                'error': 'Failed to load pending reviews'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)





