# network/models.py (updated)
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import datetime

# Device model to store device information
class Device(models.Model):
    serial_number = models.CharField(max_length=50, unique=True)  # Unique serial number
    ip_address = models.GenericIPAddressField(unique=True)  # IP must be unique
    name = models.CharField(max_length=255)
    model = models.CharField(max_length=100)
    branch = models.CharField(max_length=100)

    # Device Status
    STATUS_CHOICES = [('Up', 'Up'), ('Down', 'Down'), ('Unknown', 'Unknown')]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Down')
    maintenance_mode = models.BooleanField(default=False)  # Added maintenance mode field
    last_updated = models.DateTimeField(auto_now=True)  # Track when device was last updated

    # SNMP-related fields (latest values)
    cpu_usage = models.FloatField(null=True, blank=True)  # CPU usage as percentage
    temperature = models.FloatField(null=True, blank=True)  # Device temperature in Celsius
    latency = models.FloatField(null=True, blank=True)  # Latency in milliseconds
    bandwidth = models.FloatField(null=True, blank=True)  # Bandwidth usage in Mbps

    # SNMP configuration
    snmp_community = models.CharField(max_length=50, default='public')  # SNMP community string
    snmp_version = models.CharField(max_length=10, choices=[('1', 'v1'), ('2c', 'v2c'), ('3', 'v3')], default='2c')

    class Meta:
        ordering = ['serial_number']  # Devices ordered by serial number (ascending)

    def __str__(self):
        return f"{self.name} ({self.ip_address})"
    
    def get_latest_stats(self, limit=10):
        """Return the most recent stats for this device"""
        return self.stats.all()[:limit]

# Model to store historical SNMP stats for trend analysis
class DeviceStats(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='stats')
    timestamp = models.DateTimeField(default=timezone.now)  # Auto timestamp
    cpu_usage = models.FloatField(null=True, blank=True)
    temperature = models.FloatField(null=True, blank=True)
    latency = models.FloatField(null=True, blank=True)
    bandwidth = models.FloatField(null=True, blank=True)
    
    # Alert fields
    alert_triggered = models.BooleanField(default=False)  # Added alert_triggered field
    alert_message = models.TextField(blank=True)  # Added alert_message field

    class Meta:
        ordering = ['-timestamp']  # Show latest stats first
        indexes = [
            models.Index(fields=['timestamp']),  # Add index for faster date-based queries
            models.Index(fields=['device', 'timestamp']),  # Add composite index
        ]

    def __str__(self):
        return f"{self.device.name} Stats at {self.timestamp}"
    
    @classmethod
    def cleanup_old_records(cls):
        """Delete records older than 30 days"""
        threshold_date = timezone.now() - datetime.timedelta(days=30)
        cls.objects.filter(timestamp__lt=threshold_date).delete()

# NotificationPreference model to store user notification preferences
class NotificationPreference(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    # Store emails as a JSON list 
    emails = models.JSONField(default=list)  # Change to TextField for older DBs
    notification_times = models.JSONField(default=list)  # List of notification times (24-hour format)

    interval = models.PositiveIntegerField(default=30)  # Time interval (minutes) for down device notifications

    class Meta:
        verbose_name_plural = "Notification Preferences"

    def __str__(self):
        return f"Notifications for {self.user.username}"