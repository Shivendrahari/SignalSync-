from django.contrib import admin
from .models import Device, DeviceStats, NotificationPreference

# Custom admin interface for the Device model
@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ('name', 'ip_address', 'serial_number', 'status', 'cpu_usage', 'temperature', 'latency', 'bandwidth')  
    search_fields = ('name', 'ip_address', 'serial_number', 'branch')  
    list_filter = ('status', 'branch')  
    ordering = ('serial_number',)  
#    list_editable = ('status',)  
    readonly_fields = ('cpu_usage', 'temperature', 'latency', 'bandwidth')  

# Custom admin interface for DeviceStats (if historical stats need to be viewed)
@admin.register(DeviceStats)
class DeviceStatsAdmin(admin.ModelAdmin):
    list_display = ('device', 'timestamp', 'cpu_usage', 'temperature', 'latency', 'bandwidth')  
    search_fields = ('device__name', 'timestamp')  
    list_filter = ('device', 'timestamp')  
    ordering = ('-timestamp',)  
    readonly_fields = ('device', 'timestamp', 'cpu_usage', 'temperature', 'latency', 'bandwidth')  
    
admin.site.register(NotificationPreference)