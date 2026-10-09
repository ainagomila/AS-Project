from django.urls import path

from . import views

urlpatterns = [
    path("users/<str:dni>/accounts/<str:iban>/transfers", views.TransfersView.as_view()),
]
