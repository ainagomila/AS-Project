from django.urls import path

from . import views

urlpatterns = [
    path("auth/register", views.RegisterView.as_view()),
    path("auth/login", views.LoginView.as_view()),
    path("auth/logout", views.LogoutView.as_view()),
    path("auth/validate", views.ValidateView.as_view()),
    path("auth/exists/<str:dni>", views.ExistsView.as_view()),
    path("auth/reset-password", views.ResetPasswordView.as_view()),
    path("users", views.UserListView.as_view()),
    path("users/<str:dni>", views.UserDetailView.as_view()),
    path("users/<str:dni>/security/verify-pin", views.VerifyPinView.as_view()),
    path("users/<str:dni>/security/verify-password", views.VerifyPasswordView.as_view()),
]
