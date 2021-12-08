from .serializers import RegisterSerializer
from dj_rest_auth.app_settings import (
    JWTSerializer, TokenSerializer, create_token,
)
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from dj_rest_auth.models import TokenModel
from rest_framework.generics import CreateAPIView
from .app_settings import register_permission_classes
from django.views.decorators.debug import sensitive_post_parameters
from allauth.account import app_settings as allauth_settings
from django.conf import settings
from rest_framework.response import Response
from rest_framework import status
from dj_rest_auth.utils import jwt_encode
from allauth.account.utils import complete_signup
from .serializers import RegisterSerializer

sensitive_post_parameters_m = method_decorator(
    sensitive_post_parameters('password1', 'password2'),
)

class RegisterView(CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = register_permission_classes()
    token_model = TokenModel
    throttle_scope = 'dj_rest_auth'

    @sensitive_post_parameters_m
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get_response_data(self, user):
        if allauth_settings.EMAIL_VERIFICATION == \
                allauth_settings.EmailVerificationMethod.MANDATORY:
            return {'detail': _('Verification e-mail sent.')}

        if getattr(settings, 'REST_USE_JWT', False):
            data = {
                'user': user,
                'access_token': self.access_token,
                'refresh_token': self.refresh_token,
            }
            return JWTSerializer(data, context=self.get_serializer_context()).data
        else:
            return TokenSerializer(user.auth_token, context=self.get_serializer_context()).data

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)

        return Response(
            self.get_response_data(user),
            status=status.HTTP_201_CREATED,
            headers=headers,
        )

    def perform_create(self, serializer):
        user = serializer.save(self.request)
        if allauth_settings.EMAIL_VERIFICATION != \
                allauth_settings.EmailVerificationMethod.MANDATORY:
            if getattr(settings, 'REST_USE_JWT', False):
                self.access_token, self.refresh_token = jwt_encode(user)
            else:
                create_token(self.token_model, user, serializer)

        complete_signup(
            self.request._request, user,
            allauth_settings.EMAIL_VERIFICATION,
            None,
        )
        return user