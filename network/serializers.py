# network/serializers.py
from rest_framework import serializers
from .models import Device, DeviceStats

class DeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = '__all__'
        
class DeviceStatsSerializer(serializers.ModelSerializer):
    device_name = serializers.CharField(source='device.name', read_only=True)

    class Meta:
        model = DeviceStats
        fields = ['device', 'device_name', 'timestamp', 'cpu_usage', 'temperature', 'latency', 'bandwidth']