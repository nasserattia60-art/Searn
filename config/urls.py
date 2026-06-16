"""
URL configuration for config project.
"""
from django.contrib import admin
from django.urls import path, include
from base import views as base_views

handler404 = base_views.handler404
handler403 = base_views.handler403
handler500 = base_views.handler500

urlpatterns = [
    path('admin/', admin.site.urls),
    path('users/', include('users.urls')),
    path('', include('base.urls')),
    path('class/', include('class.urls')),
]