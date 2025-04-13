# myproject/urls.py
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from network.api_views import DeviceViewSet
from django.views.generic import RedirectView
from network.views import register_user, user_login
from network import views

# Register API routes
router = DefaultRouter()
router.register(r'devices', DeviceViewSet)

urlpatterns = [
    path('', RedirectView.as_view(url='/device_list/', permanent=False)),
    path('admin/', admin.site.urls),  # Admin panel
    
    # API endpoints managed by Django Rest Framework router
    path('api/', include(router.urls)),

    # Authentication URLs
    path('login/', views.user_login, name='login'),
    path('register/', register_user, name='register_user'),
    path('logout/', views.user_logout, name='logout'),

    # Device management URLs
    path('device_list/', views.device_list, name='device_list'),
    path('add/', views.device_add, name='device_add'),
    path('edit/<int:pk>/', views.device_edit, name='device_edit'),
    path('delete/<int:pk>/', views.device_delete, name='device_delete'),
    path('import/', views.import_csv, name='import_csv'),

    # Include network app URLs
    path('network/', include('network.urls')),  # Changed to prevent root conflict
]
