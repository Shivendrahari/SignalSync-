# network/tasks.py (updated)
from celery import shared_task
import logging
from .models import Device, DeviceStats
from .api_views import fetch_snmp_data  # Ensure correct import

# Setup logging
logger = logging.getLogger(__name__)

@shared_task
def update_snmp_data():
    """
    Periodically updates SNMP data for all devices.
    Stores historical records in DeviceStats.
    Runs as a scheduled Celery task.
    """
    devices = Device.objects.all()
    
    for device in devices:
        try:
            # Ensure SNMP settings are available
            snmp_community = device.snmp_community or "public"
            snmp_version = device.snmp_version or "2c"

            # Fetch SNMP data safely
            try:
                cpu_usage = fetch_snmp_data(device.ip_address, '1.3.6.1.4.1.2021.11.10.0', snmp_community, snmp_version)
                device.cpu_usage = cpu_usage
            except Exception as e:
                logger.error(f"Failed to fetch CPU usage for {device.name}: {e}")
                cpu_usage = None

            try:
                temperature = fetch_snmp_data(device.ip_address, '1.3.6.1.4.1.2021.13.16.0', snmp_community, snmp_version)
                device.temperature = temperature
            except Exception as e:
                logger.error(f"Failed to fetch temperature for {device.name}: {e}")
                temperature = None

            try:
                latency = fetch_snmp_data(device.ip_address, '1.3.6.1.2.1.31.1.1.1.10.1', snmp_community, snmp_version)
                device.latency = latency
            except Exception as e:
                logger.error(f"Failed to fetch latency for {device.name}: {e}")
                latency = None

            try:
                bandwidth = fetch_snmp_data(device.ip_address, '1.3.6.1.2.1.31.1.1.1.15.1', snmp_community, snmp_version)
                device.bandwidth = bandwidth
            except Exception as e:
                logger.error(f"Failed to fetch bandwidth for {device.name}: {e}")
                bandwidth = None

            # Save updated device stats
            device.save()
            
            # Create historical record
            DeviceStats.objects.create(
                device=device,
                cpu_usage=cpu_usage,
                temperature=temperature,
                latency=latency,
                bandwidth=bandwidth
            )
        
        except Exception as e:
            logger.error(f"Error updating SNMP data for {device.name}: {e}")
logger = logging.getLogger(__name__)

@shared_task
def poll_all_devices():
    devices = Device.objects.all()
    for device in devices:
        try:
            cpu = fetch_snmp_data(device.ip_address, '1.3.6.1.4.1.2021.11.10.0', device.snmp_community, device.snmp_version)
            temp = fetch_snmp_data(device.ip_address, '1.3.6.1.4.1.2021.13.16.0', device.snmp_community, device.snmp_version)
            latency = fetch_snmp_data(device.ip_address, '1.3.6.1.2.1.31.1.1.1.10.1', device.snmp_community, device.snmp_version)
            bandwidth = fetch_snmp_data(device.ip_address, '1.3.6.1.2.1.31.1.1.1.15.1', device.snmp_community, device.snmp_version)

            # Update current stats in Device
            device.cpu_usage = cpu
            device.temperature = temp
            device.latency = latency
            device.bandwidth = bandwidth
            device.save()

            # Log historical stat
            DeviceStats.objects.create(
                device=device,
                cpu_usage=cpu,
                temperature=temp,
                latency=latency,
                bandwidth=bandwidth
            )

        except Exception as e:
            logger.error(f"Polling failed for device {device.ip_address}: {e}")
            
@shared_task
def cleanup_old_stats():
    """
    Clean up device stats older than 30 days.
    Should run daily to keep database size manageable.
    """
    try:
        DeviceStats.cleanup_old_records()
        logger.info("Successfully cleaned up old device stats records")
    except Exception as e:
        logger.error(f"Error cleaning up old stats records: {e}")