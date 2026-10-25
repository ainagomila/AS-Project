from django.conf import settings
from django.urls import include, path
from django.contrib.auth import views as auth_views

urlpatterns = [
    path(
        "accounts/login/",
        auth_views.LoginView.as_view(extra_context={"frontend_url": settings.FRONTEND_URL}),
        name="login",
    ),
    path("o/", include("oauth2_provider.urls", namespace="oauth2_provider")),
    path("", include("iam.urls")),
    path("", include("banking.urls")),
    path("", include("payments.urls")),
]
