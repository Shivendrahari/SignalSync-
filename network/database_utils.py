# network/database_utils.py

import os
import sqlite3
from django.conf import settings
from network.models import Device  # Use Django ORM instead of raw SQL
import logging

# Setup logging
logger = logging.getLogger(__name__)

# Function to insert a new device into the database
def insert_device(name, ip_address, serial_number, status):
    """
    Inserts a new device into the database.
    Uses Django ORM instead of direct SQLite queries.
    """
    try:
        device, created = Device.objects.get_or_create(
            serial_number=serial_number,
            defaults={'name': name, 'ip_address': ip_address, 'status': status}
        )
        if created:
            logger.info(f"Device {name} inserted successfully!")
        else:
            logger.warning(f"Device {name} already exists in the database.")
    except Exception as e:
        logger.error(f"Failed to insert device {name}: {e}")

# Function to retrieve all devices from the database
def get_devices():
    """
    Retrieves all devices from the database.
    Uses Django ORM instead of raw SQL queries.
    """
    try:
        devices = Device.objects.all().values('name', 'ip_address', 'serial_number', 'status')
        device_list = list(devices)  # Convert queryset to list of dictionaries
        logger.info(f"Retrieved {len(device_list)} devices from the database.")
        return device_list
    except Exception as e:
        logger.error(f"Failed to retrieve devices: {e}")
        return []

# Function to update device status
def update_device_status(serial_number, new_status):
    """
    Updates the status of a device in the database.
    """
    try:
        device = Device.objects.filter(serial_number=serial_number).first()
        if device:
            device.status = new_status
            device.save()
            logger.info(f"Updated status for {device.name} to {new_status}.")
        else:
            logger.warning(f"Device with serial number {serial_number} not found.")
    except Exception as e:
        logger.error(f"Failed to update device status: {e}")

# Function to delete a device
def delete_device(serial_number):
    """
    Deletes a device from the database.
    """
    try:
        device = Device.objects.filter(serial_number=serial_number).first()
        if device:
            device.delete()
            logger.info(f"Deleted device {device.name} (Serial: {serial_number}).")
        else:
            logger.warning(f"Device with serial number {serial_number} not found.")
    except Exception as e:
        logger.error(f"Failed to delete device: {e}")