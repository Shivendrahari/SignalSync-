# network/api_views.py (updated)
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.decorators import api_view, action
from django.http import HttpResponse
from django.utils import timezone
from datetime import datetime, timedelta
from django.db.models import F
import csv
from pysnmp.hlapi import (
    CommunityData,
    UdpTransportTarget,
    ContextData,
    ObjectType,
    ObjectIdentity,
    getCmd
)
from pysnmp.entity.engine import SnmpEngine
from .models import Device, DeviceStats
from .serializers import DeviceSerializer, DeviceStatsSerializer
import logging

# Setup logging
logger = logging.getLogger(__name__)

# SNMP utility function
def fetch_snmp_data(ip, oid, community='public', version='2c'):
    """
    Fetch SNMP data from a device using the provided OID.
    """
    try:
        logger.debug(f"Attempting SNMP query to {ip} with OID {oid}")
        snmp_version = 0 if version == '1' else 1  # SNMP v1 = 0, SNMP v2c = 1
        iterator = getCmd(
            SnmpEngine(),
            CommunityData(community, mpModel=snmp_version),
            UdpTransportTarget((ip, 161), timeout=2, retries=1),
            ContextData(),
            ObjectType(ObjectIdentity(oid))
        )

        errorIndication, errorStatus, errorIndex, varBinds = next(iterator)

        if errorIndication:
            logger.error(f"SNMP Error for {ip}: {errorIndication}")
            return None
        elif errorStatus:
            logger.error(f"SNMP Error for {ip}: {errorStatus.prettyPrint()}")
            return None

        for varBind in varBinds:
            logger.debug(f"SNMP Response from {ip}: {varBind[0].prettyPrint()} = {varBind[1].prettyPrint()}")
            try:
                return float(varBind[1])  # Convert to float if possible
            except (ValueError, TypeError):
                return str(varBind[1])  # Otherwise, return as string

    except Exception as e:
        logger.error(f"SNMP Request Failed for {ip}: {str(e)}")
        return None


class DeviceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing devices, including SNMP data retrieval.
    """
    queryset = Device.objects.all()
    serializer_class = DeviceSerializer

    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve a device along with real-time SNMP data.
        """
        device = self.get_object()
        snmp_community = getattr(device, 'snmp_community', 'public')
        snmp_version = getattr(device, 'snmp_version', '2c')

        snmp_data = {
            'cpu_usage': fetch_snmp_data(device.ip_address, '1.3.6.1.4.1.2021.11.10.0', snmp_community, snmp_version),
            'temperature': fetch_snmp_data(device.ip_address, '1.3.6.1.4.1.2021.13.16.0', snmp_community, snmp_version),
            'latency': fetch_snmp_data(device.ip_address, '1.3.6.1.2.1.31.1.1.1.10.1', snmp_community, snmp_version),
            'bandwidth': fetch_snmp_data(device.ip_address, '1.3.6.1.2.1.31.1.1.1.15.1', snmp_community, snmp_version),
        }

        response_data = self.get_serializer(device).data
        response_data.update(snmp_data)
        return Response(response_data)

    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """
        Fetch real-time SNMP data and store in DeviceStats model.
        """
        device = self.get_object()

        snmp_data = {
            'cpu_usage': fetch_snmp_data(device.ip_address, '1.3.6.1.4.1.2021.11.10.0', device.snmp_community, device.snmp_version),
            'temperature': fetch_snmp_data(device.ip_address, '1.3.6.1.4.1.2021.13.16.0', device.snmp_community, device.snmp_version),
            'latency': fetch_snmp_data(device.ip_address, '1.3.6.1.2.1.31.1.1.1.10.1', device.snmp_community, device.snmp_version),
            'bandwidth': fetch_snmp_data(device.ip_address, '1.3.6.1.2.1.31.1.1.1.15.1', device.snmp_community, device.snmp_version),
        }

        # Save new SNMP data entry for historical stats
        DeviceStats.objects.create(device=device, **snmp_data)

        return Response(snmp_data)
    
    @action(detail=True, methods=['get'])
    def historical_stats(self, request, pk=None):
        """
        Retrieve historical stats for a specific device.
        Optional query parameters:
        - days: Number of days to look back (default 1)
        - interval: Time interval in minutes for data points (default 5)
        """
        device = self.get_object()
        days = int(request.query_params.get('days', 1))
        interval = int(request.query_params.get('interval', 5))
        
        # Calculate time range
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        # Get stats for the specified period
        stats = DeviceStats.objects.filter(
            device=device,
            timestamp__gte=start_date,
            timestamp__lte=end_date
        ).order_by('timestamp')
        
        # If too many data points, we can sample at the specified interval
        if interval > 1:
            # This is a simplified approach - for production, consider time-based bucketing
            stats = stats.filter(id__in=list(stats.values_list('id', flat=True)[::interval]))
            
        serializer = DeviceStatsSerializer(stats, many=True)
        return Response(serializer.data)


class DeviceStatsViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for retrieving device statistics history.
    """
    queryset = DeviceStats.objects.all()
    serializer_class = DeviceStatsSerializer
    
    def get_queryset(self):
        """
        Optionally filter by device ID and/or date range.
        """
        queryset = DeviceStats.objects.all()
        
        # Filter by device ID if specified
        device_id = self.request.query_params.get('device_id', None)
        if device_id:
            queryset = queryset.filter(device_id=device_id)
            
        # Filter by date range if specified
        start_date = self.request.query_params.get('start_date', None)
        end_date = self.request.query_params.get('end_date', None)
        
        if start_date:
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                queryset = queryset.filter(timestamp__date__gte=start_date)
            except ValueError:
                pass
                
        if end_date:
            try:
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
                queryset = queryset.filter(timestamp__date__lte=end_date)
            except ValueError:
                pass
                
        return queryset

    @action(detail=False, methods=['get'])
    def download(self, request):
        """
        Download device stats as a CSV file for a specific date.
        """
        date_str = request.GET.get('date', str(datetime.today().date()))
        device_id = request.GET.get('device_id', None)
        
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=400)

        # Filter stats by date and optionally by device
        stats_query = DeviceStats.objects.filter(timestamp__date=date_obj)
        if device_id:
            stats_query = stats_query.filter(device_id=device_id)

        # Generate CSV file response
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="device_stats_{date_str}.csv"'
        writer = csv.writer(response)

        # Write CSV headers
        writer.writerow(['Device', 'Timestamp', 'CPU Usage (%)', 'Temperature (°C)', 'Latency (ms)', 'Bandwidth (Mbps)'])

        # Write data rows
        for stat in stats_query:
            writer.writerow([
                stat.device.name, 
                stat.timestamp.strftime('%Y-%m-%d %H:%M:%S'), 
                stat.cpu_usage if stat.cpu_usage is not None else 'N/A',
                stat.temperature if stat.temperature is not None else 'N/A', 
                stat.latency if stat.latency is not None else 'N/A', 
                stat.bandwidth if stat.bandwidth is not None else 'N/A'
            ])

        return response

@api_view(['GET'])
def current_device_stats(request):
    """
    API endpoint to get the latest stats for all devices.
    Used by performance graphs.
    """
    branch = request.session.get('branch', None)
    
    # Filter by branch if provided in session
    devices = Device.objects.all()
    if branch and branch != 'Unknown':
        devices = devices.filter(branch=branch)
    
    # For each device, get the current values
    stats = []
    for device in devices:
        stats.append({
            'device_id': device.id,
            'name': device.name,
            'cpu_usage': device.cpu_usage,
            'temperature': device.temperature,
            'latency': device.latency,
            'bandwidth': device.bandwidth,
            'timestamp': timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        })
    
    return Response(stats)