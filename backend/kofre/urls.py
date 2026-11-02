from django.urls import include, path

from iam.login_views import LoginView

urlpatterns = [
    path("accounts/login/", LoginView.as_view(), name="login"),
    path("o/", include("oauth2_provider.urls", namespace="oauth2_provider")),
    path("", include("iam.urls")),
    path("", include("banking.urls")),
    path("", include("payments.urls")),
]
