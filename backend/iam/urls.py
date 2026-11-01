from django.urls import path

from . import admin_views, views

urlpatterns = [
    path("auth/register", views.RegisterView.as_view()),
    path("auth/reset-password", views.ResetPasswordView.as_view()),
    path("users", views.UserListView.as_view()),
    path("users/<str:dni>", views.UserDetailView.as_view()),
    path("users/<str:dni>/security/verify-pin", views.VerifyPinView.as_view()),
    path("users/<str:dni>/security/verify-password", views.VerifyPasswordView.as_view()),
    path("admin/users", admin_views.AdminUserListView.as_view()),
    path("admin/users/<str:dni>", admin_views.AdminUserDetailView.as_view()),
    path("admin/users/<str:dni>/accounts", admin_views.AdminUserAccountsView.as_view()),
    path(
        "admin/users/<str:dni>/accounts/<str:iban>/transfers",
        admin_views.AdminAccountTransfersView.as_view(),
    ),
]
