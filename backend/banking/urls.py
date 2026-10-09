from django.urls import path

from . import views

urlpatterns = [
    path("users/<str:dni>/accounts", views.AccountListView.as_view()),
    path("users/<str:dni>/accounts/<str:iban>", views.AccountDetailView.as_view()),
    path("users/<str:dni>/cards", views.UserCardsView.as_view()),
    path("users/<str:dni>/accounts/<str:iban>/cards", views.AccountCardsView.as_view()),
    path("users/<str:dni>/accounts/<str:iban>/cards/<str:pan>", views.CardDetailView.as_view()),
    path(
        "users/<str:dni>/accounts/<str:iban>/cards/<str:pan>/security/verify-card",
        views.VerifyCardView.as_view(),
    ),
]
