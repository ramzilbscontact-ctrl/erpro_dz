from django.urls import path
from apps.authentication import views

urlpatterns = [
    path('register/', views.RegisterView.as_view(), name='auth-register'),
    path('login/', views.LoginView.as_view(), name='auth-login'),
    path('logout/', views.LogoutView.as_view(), name='auth-logout'),
    path('refresh/', views.TokenRefreshView.as_view(), name='auth-refresh'),
    path('me/', views.MeView.as_view(), name='auth-me'),
    path('change-password/', views.ChangePasswordView.as_view(), name='auth-change-password'),
    path('2fa/setup/', views.TOTPSetupView.as_view(), name='auth-2fa-setup'),
    path('2fa/disable/', views.TOTPDisableView.as_view(), name='auth-2fa-disable'),
    path('google/', views.GoogleAuthView.as_view(), name='auth-google'),
]
