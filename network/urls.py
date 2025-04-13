# network/urls.py 
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_views import DeviceViewSet, DeviceStatsViewSet, current_device_stats
from .views import device_stats_api, download_device_stats, performance_graph_view
from network.views import register_user
from . import views

router = DefaultRouter()
router.register(r'devices', DeviceViewSet, basename='device')
router.register(r'device-stats', DeviceStatsViewSet, basename='devicestats')

urlpatterns = [
    path('login/', views.user_login, name='user_login'),  # Login page
    path('register/', register_user, name='register_user'),
    path('logout/', views.user_logout, name='logout'),  # Logout functionality
    path('devices/', views.device_list, name='device_list'),  # List of devices
    path('devices/stats/html/', views.stats_html_dashboard, name='stats_html_dashboard'),
    path('add/', views.device_add, name='device_add'),  # Add new device
    path('edit/<int:pk>/', views.device_edit, name='device_edit'),  # Edit device
    path('delete/<int:pk>/', views.device_delete, name='device_delete'),  # Delete device
    path('import/', views.import_csv, name='import_csv'),  # Import devices from CSV
    path('save-notifications/', views.save_notification_preferences, name='save_notifications'),
    path('alerts/', views.alerts_notifications_view, name='alerts_notifications'),
    
    # Performance graph URLs
    path('performance_graph/', performance_graph_view, name='performance_graph'),
    path('devices/stats/', views.device_stats_api, name='device_stats'),  # New URL for device stats page
    path('api/device-stats/', device_stats_api, name='api-device-stats'),
    path('api/current-stats/', current_device_stats, name='current-stats'),
    path('download_stats/', download_device_stats, name='download_stats'),
    
    # API routes
    path('api/', include(router.urls)),
]