from django.urls import path

from .main import Main


urlpatterns = [
    path('', Main.as_view(), name="main"),
]
