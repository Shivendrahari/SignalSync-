# network/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Device, DeviceStats

class DeviceStatsConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time device stats
    """
    async def connect(self):
        # Get the device ID from the URL
        self.device_id = self.scope['url_route']['kwargs'].get('device_id')
        
        # Create a unique group name for this connection
        self.room_group_name = f"device_stats_{self.device_id}" if self.device_id else "all_devices_stats"
        
        # Join the room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        # Accept the connection
        await self.accept()
        
        # Send initial data
        if self.device_id:
            device_stats = await self.get_device_stats(self.device_id)
            await self.send(text_data=json.dumps(device_stats))
        else:
            all_stats = await self.get_all_devices_stats()
            await self.send(text_data=json.dumps(all_stats))
    
    async def disconnect(self, close_code):
        # Leave the room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        """
        Receive message from WebSocket (client to server)
        """
        data = json.loads(text_data)
        message_type = data.get('type')
        
        if message_type == 'get_stats':
            device_id = data.get('device_id', self.device_id)
            if device_id:
                device_stats = await self.get_device_stats(device_id)
                await self.send(text_data=json.dumps(device_stats))
            else:
                all_stats = await self.get_all_devices_stats()
                await self.send(text_data=json.dumps(all_stats))
    
    async def device_stats_update(self, event):
        """
        Receive message from room group (server to clients)
        """
        # Send the updated stats to the WebSocket
        await self.send(text_data=json.dumps(event['data']))
    
    @database_sync_to_async
    def get_device_stats(self, device_id):
        """
        Get latest stats for a specific device
        """
        try:
            device = Device.objects.get(id=device_id)
            latest_stats = DeviceStats.objects.filter(device=device).first()
            
            if latest_stats:
                return {
                    'device_id': device.id,
                    'name': device.name,
                    'ip_address': device.ip_address,
                    'model': device.model,
                    'status': device.status,
                    'maintenance_mode': device.maintenance_mode,
                    'cpu_usage': latest_stats.cpu_usage,
                    'temperature': latest_stats.temperature,
                    'latency': latest_stats.latency,
                    'bandwidth': latest_stats.bandwidth,
                    'timestamp': latest_stats.timestamp.isoformat(),
                    'alert_triggered': latest_stats.alert_triggered,
                    'alert_message': latest_stats.alert_message if latest_stats.alert_triggered else None
                }
            else:
                return {
                    'device_id': device.id,
                    'name': device.name,
                    'ip_address': device.ip_address,
                    'model': device.model,
                    'status': device.status,
                    'maintenance_mode': device.maintenance_mode,
                    'cpu_usage': device.cpu_usage,
                    'temperature': device.temperature,
                    'latency': device.latency,
                    'bandwidth': device.bandwidth,
                    'timestamp': device.last_updated.isoformat(),
                    'alert_triggered': False,
                    'alert_message': None
                }
        except Device.DoesNotExist:
            return {'error': f'Device with ID {device_id} not found'}
    
    @database_sync_to_async
    def get_all_devices_stats(self):
        """
        Get latest stats for all devices
        """
        devices = Device.objects.all()
        result = []
        
        for device in devices:
            latest_stats = DeviceStats.objects.filter(device=device).first()
            
            device_data = {
                'device_id': device.id,
                'name': device.name,
                'ip_address': device.ip_address,
                'model': device.model,
                'status': device.status,
                'maintenance_mode': device.maintenance_mode
            }
            
            if latest_stats:
                device_data.update({
                    'cpu_usage': latest_stats.cpu_usage,
                    'temperature': latest_stats.temperature,
                    'latency': latest_stats.latency,
                    'bandwidth': latest_stats.bandwidth,
                    'timestamp': latest_stats.timestamp.isoformat(),
                    'alert_triggered': latest_stats.alert_triggered,
                    'alert_message': latest_stats.alert_message if latest_stats.alert_triggered else None
                })
            else:
                device_data.update({
                    'cpu_usage': device.cpu_usage,
                    'temperature': device.temperature,
                    'latency': device.latency,
                    'bandwidth': device.bandwidth,
                    'timestamp': device.last_updated.isoformat(),
                    'alert_triggered': False,
                    'alert_message': None
                })
                
            result.append(device_data)
            
        return {'devices': result}