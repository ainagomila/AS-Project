from django.urls import include, path

urlpatterns = [
    path("", include("iam.urls")),
    path("", include("banking.urls")),
    path("", include("payments.urls")),
]
