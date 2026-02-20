# apps/security/urls.py
from django.urls import path

from apps.security.views import MenuView

urlpatterns = [
    path("menu/", MenuView.as_view()),
    
]
