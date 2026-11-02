from django.urls import path

from . import admin_views, views

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
    # ---- administrator endpoints ----
    path("admin/users", admin_views.AdminUsersView.as_view()),
    path("admin/users/<str:dni>", admin_views.AdminUserDetailView.as_view()),
    path("admin/users/<str:dni>/reset-password", admin_views.AdminUserResetPasswordView.as_view()),
    path("admin/users/<str:dni>/accounts", admin_views.AdminUserAccountsView.as_view()),
    path("admin/users/<str:dni>/cards", admin_views.AdminUserCardsView.as_view()),
    path(
        "admin/users/<str:dni>/accounts/<str:iban>/transfers",
        admin_views.AdminAccountTransfersView.as_view(),
    ),
    path("admin/accounts", admin_views.AdminAccountsView.as_view()),
    path("admin/accounts/<str:iban>", admin_views.AdminAccountDetailView.as_view()),
    path("admin/cards", admin_views.AdminCardsView.as_view()),
    path("admin/cards/<str:pan>", admin_views.AdminCardDetailView.as_view()),
    path("admin/transfers", admin_views.AdminTransfersView.as_view()),
    path("admin/audit-logs", admin_views.AdminAuditLogsView.as_view()),
    path("admin/settings", admin_views.AdminSettingsView.as_view()),
    path("admin/settings/<str:key>", admin_views.AdminSettingDetailView.as_view()),
    path("admin/stats", admin_views.AdminStatsView.as_view()),
]
