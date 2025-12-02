from datetime import timezone
import logging
from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenBlacklistView as SimpleJWTTokenBlacklistView
from django.contrib.auth import authenticate, login
from django.contrib.auth.tokens import default_token_generator, PasswordResetTokenGenerator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.conf import settings

from .models import CustomUser, UserStatus
from .serializers import (
    RegisterSerializer, LoginSerializer, UserSerializer, UserDetailSerializer,
    PasswordResetRequestSerializer, PasswordResetConfirmSerializer,
    EmailVerifySerializer, ChangePasswordSerializer, LogoutSerializer
)
# from .utils import (
#     send_user_acknowledgment_email, send_secretariate_notification_email,
#     send_verification_success_email, send_rejection_email,
#     send_password_reset_email, send_password_change_confirmation
# )

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
            user.status = UserStatus.INACTIVE
            user.verification_token = default_token_generator.make_token(user)
            user.save()

            # Send emails
            send_user_acknowledgment_email(user)
            send_secretariate_notification_email(user)

            logger.info(f"New user registered (pending verification): {user.email}")

            return Response({
                'success': True,
                'message': 'Registration successful. Please wait for CEMA-Africa secretariate approval.',
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Registration error: {str(e)}")
            return Response({
                'success': False,
                'message': 'Registration failed. Please try again.',
                'errors': getattr(e, 'detail', str(e))
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class EmailVerifyView(generics.GenericAPIView):
    """
    Email verification view for secretariate approval/rejection
    GET: Validate token and return user data for review
    PATCH/PUT: Approve or reject user registration
    """
    permission_classes = [AllowAny]
    queryset = CustomUser.objects.all()
    serializer_class = EmailVerifySerializer

    def get(self, request, user_id, token):
        """Validate token and return user data for review"""
        try:
            user = CustomUser.objects.get(id=user_id)
        except CustomUser.DoesNotExist:
            return Response({
                'success': False,
                'message': 'User not found.'
            }, status=status.HTTP_404_NOT_FOUND)

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
        """Handle user approval/rejection via PATCH"""
        return self._handle_action(request, user_id, token)

    def put(self, request, user_id, token):
        """Handle user approval/rejection via PUT"""
        return self._handle_action(request, user_id, token)

    def _handle_action(self, request, user_id, token):
        """Shared logic for approve/reject actions"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        action = serializer.validated_data['action']
        rejection_reason = serializer.validated_data.get('rejection_reason', '')

        try:
            user = CustomUser.objects.get(id=user_id)
        except CustomUser.DoesNotExist:
            return Response({
                'success': False,
                'message': 'User not found.'
            }, status=status.HTTP_404_NOT_FOUND)

        if not default_token_generator.check_token(user, token):
            return Response({
                'success': False,
                'message': 'Invalid or expired token.'
            }, status=status.HTTP_400_BAD_REQUEST)

        if user.is_active and user.status == UserStatus.ACTIVE:
            return Response({
                'success': False,
                'message': 'User account has already been activated.'
            }, status=status.HTTP_400_BAD_REQUEST)

        if action == 'approve':
            user.is_active = True
            user.status = UserStatus.ACTIVE
            user.is_email_verified = True
            user.email_verified_at = timezone.now()
            user.save()
            send_verification_success_email(user)
            message = 'User account approved and activated successfully.'
            logger.info(f"User approved: {user.email}")

        else:  # reject
            user.status = UserStatus.BLOCKED
            user.is_active = False
            user.save()
            send_rejection_email(user, rejection_reason)
            message = 'User account rejected.'
            logger.info(f"User rejected: {user.email}")

        return Response({
            'success': True,
            'message': message,
            'user': UserSerializer(user).data
        }, status=status.HTTP_200_OK)


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
