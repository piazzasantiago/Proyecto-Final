from django.urls import path

from . import views

urlpatterns = [
    path("auth/login/", views.login, name="login"),
    path("auth/me/", views.me, name="me"),
    path("auth/logout/", views.logout, name="logout"),
]
