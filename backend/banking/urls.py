from django.urls import path

from . import views

urlpatterns = [
    path("users/<str:dni>/accounts", views.AccountListView.as_view()),
    path("users/<str:dni>/accounts/<str:iban>", views.AccountDetailView.as_view()),
]
