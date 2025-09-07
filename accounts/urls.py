from django.urls import path, include
from django.conf import settings
from . import views

app_name = 'accounts'

urlpatterns = [
    path('', views.progress, name='progress'),
]