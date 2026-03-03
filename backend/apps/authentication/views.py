"""
Authentication views — login, logout, register, token refresh, me, 2FA.
Token blacklisting uses Redis (no SQL database needed).
"""
from datetime import datetime, timedelta
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from django.conf import settings

from apps.authentication.models import User
from apps.authentication.serializers import (
    LoginSerializer,
    RegisterSerializer,
    UserSerializer,
    ChangePasswordSerializer,
    TOTPSetupSerializer,
)

# ─── Redis-based token blacklist ──────────────────────────────────────────────

def _get_redis():
    """Return a Redis connection using the broker URL."""
    import redis as redis_lib
    return redis_lib.from_url(settings.CELERY_BROKER_URL, decode_responses=True)

def blacklist_token(token_str: str, exp_seconds: int = 604800):
    """Add a token jti to the Redis blacklist with TTL."""
    try:
        r = _get_redis()
        r.setex(f'bl:{token_str[:64]}', exp_seconds, '1')
    except Exception:
        pass  # Redis unavailable — degraded mode, tokens expire naturally

def is_token_blacklisted(token_str: str) -> bool:
    try:
        r = _get_redis()
        return r.exists(f'bl:{token_str[:64]}') == 1
    except Exception:
        return False


# ─── Token helper ─────────────────────────────────────────────────────────────

def get_tokens_for_user(user: User) -> dict:
    """Create a JWT pair that embeds MongoEngine user data as custom claims."""
    refresh = RefreshToken()
    refresh['user_id'] = str(user.id)
    refresh['email'] = user.email
    refresh['role'] = user.role
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


# ─── Views ────────────────────────────────────────────────────────────────────

class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        tokens = get_tokens_for_user(user)
        return Response(
            {'user': UserSerializer(user).data, 'tokens': tokens},
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user: User = serializer.validated_data['user']

        # Update last_login
        User.objects(id=user.id).update_one(set__last_login=datetime.utcnow())
        user.reload()

        tokens = get_tokens_for_user(user)
        return Response({'user': UserSerializer(user).data, 'tokens': tokens})


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Blacklist the refresh token via Redis.
        Client should also discard the short-lived access token.
        """
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response(
                {'detail': 'refresh token is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            blacklist_token(refresh_token)
        except Exception:
            pass
        return Response({'detail': 'Successfully logged out.'})


class TokenRefreshView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response(
                {'detail': 'refresh token is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            old_token = RefreshToken(refresh_token)
            # Check Redis blacklist before rotating
            if is_token_blacklisted(refresh_token):
                return Response({'detail': 'Token has been revoked.'}, status=status.HTTP_401_UNAUTHORIZED)
            # ROTATE_REFRESH_TOKENS is True — blacklist old and issue new pair
            blacklist_token(refresh_token)
            user_id = str(old_token.get('user_id', ''))
            user = User.objects(id=user_id, is_active=True).first()
            if not user:
                return Response(
                    {'detail': 'User not found.'},
                    status=status.HTTP_401_UNAUTHORIZED,
                )
            tokens = get_tokens_for_user(user)
            return Response(tokens)
        except TokenError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_401_UNAUTHORIZED)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)

    def patch(self, request):
        serializer = UserSerializer(
            instance=request.user,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserSerializer(user).data)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from apps.authentication.serializers import hash_password, check_password
        serializer = ChangePasswordSerializer(
            data=request.data, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        new_hash = hash_password(serializer.validated_data['new_password'])
        User.objects(id=request.user.id).update_one(set__password=new_hash)
        return Response({'detail': 'Password updated successfully.'})


class TOTPSetupView(APIView):
    """Step 1: generate secret and QR provisioning URI."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user: User = request.user
        if user.totp_enabled:
            return Response(
                {'detail': '2FA is already enabled.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        secret = user.generate_totp_secret()
        user.save()
        return Response({'totp_uri': user.get_totp_uri(), 'secret': secret})

    def post(self, request):
        """Step 2: confirm the code to activate 2FA."""
        user: User = request.user
        serializer = TOTPSetupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if not user.verify_totp(serializer.validated_data['totp_code']):
            return Response(
                {'detail': 'Invalid TOTP code.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        User.objects(id=user.id).update_one(set__totp_enabled=True)
        return Response({'detail': '2FA enabled successfully.'})


class TOTPDisableView(APIView):
    """Disable 2FA — requires a valid TOTP code to confirm intent."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user: User = request.user
        if not user.totp_enabled:
            return Response(
                {'detail': '2FA is not enabled.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = TOTPSetupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if not user.verify_totp(serializer.validated_data['totp_code']):
            return Response(
                {'detail': 'Invalid TOTP code.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        User.objects(id=user.id).update_one(
            set__totp_enabled=False,
            unset__totp_secret=1,
        )
        return Response({'detail': '2FA disabled successfully.'})


class GoogleAuthView(APIView):
    """
    Authenticate (or register) a user via Google OAuth2 access token.

    POST /api/auth/google/
    Body: { "credential": "<google_access_token>" }

    Flow:
      1. Exchange the access token for user info via Google's userinfo endpoint.
      2. If the user already exists in MongoDB → login.
      3. If the user does not exist → create account automatically (role=viewer).
      4. Return the same JWT pair as the standard login endpoint.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        import requests as http

        access_token = request.data.get('credential', '').strip()
        if not access_token:
            return Response(
                {'detail': 'Google access token is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Call Google's UserInfo endpoint to verify the token and retrieve profile
        try:
            resp = http.get(
                'https://www.googleapis.com/oauth2/v2/userinfo',
                headers={'Authorization': f'Bearer {access_token}'},
                timeout=10,
            )
        except Exception:
            return Response(
                {'detail': 'Could not reach Google servers. Try again.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        if resp.status_code != 200:
            return Response(
                {'detail': 'Invalid or expired Google token.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        id_info = resp.json()
        email = id_info.get('email', '').lower().strip()
        if not email:
            return Response(
                {'detail': 'Google account has no verified email address.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Find or create the user in MongoDB
        user = User.objects(email=email).first()
        if not user:
            import secrets
            user = User(
                email=email,
                password=f'google:{secrets.token_hex(32)}',  # unusable password — Google-only account
                first_name=id_info.get('given_name', ''),
                last_name=id_info.get('family_name', ''),
                role='viewer',
                is_active=True,
            )
            user.save()

        if not user.is_active:
            return Response(
                {'detail': 'Account is disabled. Contact an administrator.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        User.objects(id=user.id).update_one(set__last_login=datetime.utcnow())
        user.reload()

        tokens = get_tokens_for_user(user)
        return Response({'user': UserSerializer(user).data, 'tokens': tokens})
