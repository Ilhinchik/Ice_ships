"""
URL configuration for bmstu project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.urls import path
from bmstu_lab import views
from django.contrib import admin

urlpatterns = [
    path('', views.index, name='home'),
    path('admin/', admin.site.urls),
    path('ships/<int:ship_id>/', views.ship, name='ship'),
    path('ships/<int:ship_id>/add_to_icebreaker/', views.add_ship_to_draft_icebreaker, name="add_ship_to_draft_icebreaker"),
    path('icebreaker/<int:icebreaker_id>/delete/', views.delete_icebreaker, name="delete_icebreaker"),
    path('icebreaker/<int:icebreaker_id>/', views.icebreaker, name='icebreaker'),
]