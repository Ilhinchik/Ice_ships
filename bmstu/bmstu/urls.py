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
from bmstu_lab.views import *
from django.contrib import admin
from rest_framework import permissions
from django.urls import path, include
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

schema_view = get_schema_view(
   openapi.Info(
      title="Install server software API",
      default_version='v1',
      description="API for installing server software",
      contact=openapi.Contact(email="markovila539@gmail.com"),
      license=openapi.License(name="MIT License"),
   ),
   public=True,
   permission_classes=[permissions.AllowAny,],
)

urlpatterns = [

    path('admin/', admin.site.urls),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    # Набор методов для услуг
    path('api/ships/', search_ships),  # GET
    path('api/ships/<int:ship_id>/', get_ship_by_id),  # GET
    path('api/ships/<int:ship_id>/update/', update_ship),  # PUT
    path('api/ships/<int:ship_id>/update_image/', update_ship_image),  # POST
    path('api/ships/<int:ship_id>/delete/', delete_ship),  # DELETE
    path('api/ships/create/', create_ship),  # POST
    path('api/ships/<int:ship_id>/add_to_icebreaker/', add_ship_to_icebreaker),  # POST

    # Набор методов для заявок
    path('api/icebreakers/', search_icebreakers),  # GET
    path('api/icebreakers/<int:icebreaker_id>/', get_icebreaker_by_id),  # GET
    path('api/icebreakers/<int:icebreaker_id>/update/', update_icebreaker),  # PUT
    path('api/icebreakers/<int:icebreaker_id>/update_status_user/', update_status_user),  # PUT
    path('api/icebreakers/<int:icebreaker_id>/update_status_admin/', update_status_admin),  # PUT
    path('api/icebreakers/<int:icebreaker_id>/delete/', delete_icebreaker),  # DELETE

    # Набор методов для м-м
    path('api/lectures/<int:lecture_id>/specialists/<int:specialist_id>/', get_ship_icebreaker),  # GET
    path('api/icebreakers/<int:icebreaker_id>/update_ship/<int:ship_id>/', update_ship_in_icebreaker),  # PUT
    path('api/icebreakers/<int:icebreaker_id>/delete_ship/<int:ship_id>/', delete_ship_from_icebreaker),  # DELETE

    # Набор методов пользователей
    path('api/users/register/', register), # POST
    path('api/users/login/', login), # POST
    path('api/users/logout/', logout), # POST
    path('api/users/<int:user_id>/update/', update_user), # PUT
]