from django.urls import path

from authz.views import AuditLogView

from . import admin_views, views

urlpatterns = [
    path("auth/register", views.RegisterView.as_view()),
    path("auth/exists/<str:dni>", views.ExistsView.as_view()),
    path("auth/reset-password", views.ResetPasswordView.as_view()),
    path("users", views.UserListView.as_view()),
    path("users/<str:dni>", views.UserDetailView.as_view()),
    path("users/<str:dni>/security/verify-pin", views.VerifyPinView.as_view()),
    path("users/<str:dni>/security/verify-password", views.VerifyPasswordView.as_view()),
    path("admin/users", admin_views.AdminUserListView.as_view()),
    path("admin/users/<str:user_id>", admin_views.AdminUserDetailView.as_view()),
    path("admin/users/<str:user_id>/accounts", admin_views.AdminUserAccountsView.as_view()),
    path(
        "admin/users/<str:user_id>/accounts/<str:account_id>/transfers",
        admin_views.AdminAccountTransfersView.as_view(),
    ),
    path("admin/audit", AuditLogView.as_view()),
]
