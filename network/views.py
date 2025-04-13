# network/views.py 
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from .models import Device, DeviceStats, NotificationPreference
from .forms import DeviceForm
from django.contrib.auth.forms import UserCreationForm
import csv
import json
from datetime import datetime, timedelta
from ping3 import ping
import logging
from pysnmp.hlapi import SnmpEngine, CommunityData, UdpTransportTarget, ContextData, ObjectType, ObjectIdentity, getCmd
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt

# Setup logging
logger = logging.getLogger(__name__)

# User registration view
def register_user(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}! You can now log in.')
            return redirect('login')
    else:
        form = UserCreationForm()
    return render(request, 'register.html', {'form': form})

# SNMP utility function
def fetch_snmp_data(ip, oid, community='public', version='2c'):
    try:
        snmp_version = 0 if version == '1' else 1  # SNMP v1 = 0, v2c = 1
        iterator = getCmd(
            SnmpEngine(),
            CommunityData(community, mpModel=snmp_version),
            UdpTransportTarget((ip, 161), timeout=2, retries=1),
            ContextData(),
            ObjectType(ObjectIdentity(oid))
        )

        errorIndication, errorStatus, errorIndex, varBinds = next(iterator)
        if errorIndication:
            logger.error(f"SNMP error from {ip}: {errorIndication}")
            return None
        elif errorStatus:
            return None

        for varBind in varBinds:
            try:
                return float(varBind[1])  # Convert to float if possible
            except (ValueError, TypeError):
                return None
    except Exception as e:
        logger.error(f"SNMP Error for {ip}: {e}")
        return None

# Login view
def user_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        branch = request.POST.get('branch')

        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            request.session['branch'] = branch
            return redirect('device_list')
        else:
            messages.error(request, 'Invalid credentials')
    return render(request, 'login.html')

# Logout view
def user_logout(request):
    logout(request)
    return redirect('login')

# Device list view with filtering and search
@login_required
def device_list(request):
    # Get search query
    query = request.GET.get('q', '')
    show_full_list = request.GET.get('show_full_list', '0') == '1'
    
    # Get branch from session
    branch = request.session.get('branch', 'Unknown')
    
    # Start with all devices
    devices = Device.objects.all()
    
    # Apply search filter if query exists
    if query:
        devices = devices.filter(
            Q(serial_number__icontains=query) |
            Q(branch__icontains=query) |
            Q(ip_address__icontains=query) |
            Q(name__icontains=query)
        )
    
    # Filter by branch unless showing full list
    if not show_full_list and branch != 'Unknown':
        devices = devices.filter(branch=branch)
    
    # Order devices by serial number
    devices = devices.order_by('serial_number')
    
    context = {
        'devices': devices,
        'query': query,
        'branch': branch,
        'show_full_list': show_full_list,
    }
    
    return render(request, 'device_list.html', context)

# Add new device
@login_required
def device_add(request):
    if request.method == 'POST':
        form = DeviceForm(request.POST)
        if form.is_valid():
            device = form.save(commit=False)
            device.status = check_device_status(device.ip_address)
            device.cpu_usage = fetch_snmp_data(device.ip_address, '1.3.6.1.4.1.2021.11.10.0')
            device.temperature = fetch_snmp_data(device.ip_address, '1.3.6.1.4.1.2021.13.16.0')
            device.latency = fetch_snmp_data(device.ip_address, '1.3.6.1.2.1.31.1.1.1.10.1')
            device.bandwidth = fetch_snmp_data(device.ip_address, '1.3.6.1.2.1.31.1.1.1.15.1')
            device.save()
            
            # Create initial stats record
            DeviceStats.objects.create(
                device=device,
                cpu_usage=device.cpu_usage,
                temperature=device.temperature,
                latency=device.latency,
                bandwidth=device.bandwidth
            )
            
            messages.success(request, 'Device added successfully!')
            return redirect('device_list')
    else:
        form = DeviceForm()
    return render(request, 'device_form.html', {'form': form, 'title': 'Add New Device'})

# Edit device
@login_required
def device_edit(request, pk):
    device = get_object_or_404(Device, pk=pk)
    if request.method == 'POST':
        form = DeviceForm(request.POST, instance=device)
        if form.is_valid():
            device = form.save(commit=False)
            device.status = check_device_status(device.ip_address)
            device.save()
            messages.success(request, 'Device updated successfully!')
            return redirect('device_list')
    else:
        form = DeviceForm(instance=device)
    return render(request, 'device_form.html', {'form': form, 'title': 'Edit Device'})

# Delete device
@login_required
def device_delete(request, pk):
    device = get_object_or_404(Device, pk=pk)
    if request.method == 'POST':
        device.delete()
        messages.success(request, 'Device deleted successfully!')
        return redirect('device_list')
    return render(request, 'device_confirm_delete.html', {'device': device})

# Import devices from CSV
@login_required
def import_csv(request):
    if request.method == 'POST':
        try:
            csv_file = request.FILES['file']
            if not csv_file.name.endswith('.csv'):
                messages.error(request, 'Please upload a CSV file.')
                return redirect('import_csv')

            file_data = csv_file.read().decode("utf-8").splitlines()
            csv_data = csv.reader(file_data)
            next(csv_data, None)  # Skip header

            for row in csv_data:
                if len(row) != 5:
                    logger.warning(f"Skipping invalid row: {row}")
                    continue

                device, created = Device.objects.update_or_create(
                    serial_number=row[0],
                    defaults={
                        'ip_address': row[1],
                        'name': row[2],
                        'model': row[3],
                        'branch': row[4],
                        'status': check_device_status(row[1])
                    }
                )
                
                # Create initial stats record if device was created
                if created:
                    DeviceStats.objects.create(
                        device=device,
                        cpu_usage=device.cpu_usage,
                        temperature=device.temperature,
                        latency=device.latency,
                        bandwidth=device.bandwidth
                    )

            messages.success(request, 'CSV imported successfully.')
            return redirect('device_list')
        except Exception as e:
            logger.error(f"Error importing CSV: {e}")
            messages.error(request, 'An error occurred while importing the CSV file.')
    return render(request, 'import_csv.html')

# Check device status using ping
def check_device_status(ip_address):
    try:
        response_time = ping(ip_address, timeout=2)
        return 'Up' if response_time is not None else 'Down'
    except Exception as e:
        logger.error(f"Error pinging device {ip_address}: {e}")
        return 'Unknown'

# Save notification preferences
@login_required
def save_notification_preferences(request):
    if request.method == 'POST':
        emails = request.POST.getlist('emails')
        notification_times = request.POST.getlist('notification_times', [])
        interval = int(request.POST.get('interval', 30))

        NotificationPreference.objects.update_or_create(
            user=request.user,
            defaults={
                'emails': emails, 
                'notification_times': notification_times, 
                'interval': interval
            }
        )
        messages.success(request, 'Notification preferences updated successfully!')
    return redirect('device_list')

#Alerts & Notification
@login_required
def alerts_notifications_view(request):
    return render(request, 'alerts_notifications.html')

# Create status message
def create_status_message(statuses):
    message = "Device Status Report:\n\n"
    for status in statuses:
        message += f"Device: {status['device_name']}, Status: {status['status']}\n"
    return message

# New: View for performance graph page
@login_required
def performance_graph_view(request):
    branch = request.session.get('branch', 'Unknown')
    devices = Device.objects.filter(branch=branch)
    
    # Get selected device if specified
    selected_device_id = request.GET.get('device_id')
    selected_device = None
    
    if selected_device_id:
        try:
            selected_device = Device.objects.get(pk=selected_device_id)
        except Device.DoesNotExist:
            pass
    
    context = {
        'devices': devices,
        'selected_device': selected_device,
        'branch': branch
    }
    
    return render(request, 'performance_graph.html', context)

# API view to get device stats
@login_required
def device_stats_api(request):
    branch = request.session.get('branch', 'Unknown')
    device_id = request.GET.get('device_id')
    
    if device_id:
        # If device_id is specified, get stats for that device
        try:
            device = Device.objects.get(pk=device_id)
            stats = {
                'cpu_usage': device.cpu_usage,
                'temperature': device.temperature,
                'latency': device.latency,
                'bandwidth': device.bandwidth,
            }
        except Device.DoesNotExist:
            stats = {}
    else:
        # Otherwise, get stats for all devices in the branch
        devices = Device.objects.filter(branch=branch)
        
        cpu_usage = 0
        temperature = 0
        latency = 0
        bandwidth = 0
        count = 0
        
        for device in devices:
            if device.cpu_usage is not None:
                cpu_usage += device.cpu_usage
                count += 1
            if device.temperature is not None:
                temperature += device.temperature
            if device.latency is not None:
                latency += device.latency
            if device.bandwidth is not None:
                bandwidth += device.bandwidth
        
        # Calculate averages if any devices were found
        if count > 0:
            stats = {
                'cpu_usage': round(cpu_usage / count, 2),
                'temperature': round(temperature / count, 2),
                'latency': round(latency / count, 2),
                'bandwidth': round(bandwidth / count, 2)
            }
        else:
            stats = {
                'cpu_usage': 0,
                'temperature': 0,
                'latency': 0,
                'bandwidth': 0
            }
    
    return JsonResponse(stats)

# API view to get device historical stats
@login_required
def device_historical_stats_api(request):
    device_id = request.GET.get('device_id')
    days = int(request.GET.get('days', 7))
    
    if not device_id:
        return JsonResponse({'error': 'Device ID is required'}, status=400)
    
    try:
        device = Device.objects.get(pk=device_id)
    except Device.DoesNotExist:
        return JsonResponse({'error': 'Device not found'}, status=404)
    
    # Get stats for the specified period
    start_date = timezone.now() - timedelta(days=days)
    stats = DeviceStats.objects.filter(
        device=device,
        timestamp__gte=start_date
    ).order_by('timestamp')
    
    # Format data for charts
    result = {
        'labels': [],
        'cpu_usage': [],
        'temperature': [],
        'latency': [],
        'bandwidth': []
    }
    
    for stat in stats:
        result['labels'].append(stat.timestamp.strftime('%Y-%m-%d %H:%M'))
        result['cpu_usage'].append(stat.cpu_usage if stat.cpu_usage is not None else 0)
        result['temperature'].append(stat.temperature if stat.temperature is not None else 0)
        result['latency'].append(stat.latency if stat.latency is not None else 0)
        result['bandwidth'].append(stat.bandwidth if stat.bandwidth is not None else 0)
    
    return JsonResponse(result)

# Export devices to CSV
@login_required
def export_csv(request):
    branch = request.session.get('branch', 'Unknown')
    devices = Device.objects.filter(branch=branch)
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="devices.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Serial Number', 'IP Address', 'Name', 'Model', 'Branch', 'Status'])
    
    for device in devices:
        writer.writerow([
            device.serial_number,
            device.ip_address,
            device.name,
            device.model,
            device.branch,
            device.status
        ])
    
    return response

# Download device stats as CSV
@login_required
def download_device_stats(request):
    device_id = request.GET.get('device_id')
    days = int(request.GET.get('days', 7))
    
    # Set up the HTTP response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="device_stats.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Device', 'Timestamp', 'CPU Usage (%)', 'Temperature (°C)', 'Latency (ms)', 'Bandwidth (Mbps)'])
    
    if device_id:
        # Download stats for specific device
        try:
            device = Device.objects.get(pk=device_id)
            start_date = timezone.now() - timedelta(days=days)
            stats = DeviceStats.objects.filter(
                device=device,
                timestamp__gte=start_date
            ).order_by('timestamp')
            
            for stat in stats:
                writer.writerow([
                    device.name,
                    stat.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                    stat.cpu_usage if stat.cpu_usage is not None else 'N/A',
                    stat.temperature if stat.temperature is not None else 'N/A',
                    stat.latency if stat.latency is not None else 'N/A',
                    stat.bandwidth if stat.bandwidth is not None else 'N/A'
                ])
        except Device.DoesNotExist:
            writer.writerow(['Device not found'])
    else:
        # If no device specified, return all stats from all devices
        branch = request.session.get('branch', 'Unknown')
        devices = Device.objects.filter(branch=branch)
        start_date = timezone.now() - timedelta(days=days)
        
        for device in devices:
            stats = DeviceStats.objects.filter(
                device=device,
                timestamp__gte=start_date
            ).order_by('timestamp')
            
            for stat in stats:
                writer.writerow([
                    device.name,
                    stat.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                    stat.cpu_usage if stat.cpu_usage is not None else 'N/A',
                    stat.temperature if stat.temperature is not None else 'N/A',
                    stat.latency if stat.latency is not None else 'N/A',
                    stat.bandwidth if stat.bandwidth is not None else 'N/A'
                ])
    
    return response

# Dashboard view
@login_required
def dashboard(request):
    branch = request.session.get('branch', 'Unknown')
    
    # Get device counts by status
    all_devices = Device.objects.filter(branch=branch)
    total_devices = all_devices.count()
    up_devices = all_devices.filter(status='Up').count()
    down_devices = all_devices.filter(status='Down').count()
    unknown_devices = all_devices.filter(status='Unknown').count()
    
    # Get recent alerts
    recent_alerts = DeviceStats.objects.filter(
        device__branch=branch,
        alert_triggered=True
    ).order_by('-timestamp')[:10]
    
    context = {
        'branch': branch,
        'total_devices': total_devices,
        'up_devices': up_devices,
        'down_devices': down_devices,
        'unknown_devices': unknown_devices,
        'recent_alerts': recent_alerts,
    }
    
    return render(request, 'dashboard.html', context)

# Update device status (for AJAX calls)
@csrf_exempt
@login_required
def update_device_status(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            device_id = data.get('device_id')
            new_status = data.get('status')
            
            if not device_id or not new_status:
                return JsonResponse({'error': 'Missing device_id or status'}, status=400)
            
            device = get_object_or_404(Device, pk=device_id)
            old_status = device.status
            device.status = new_status
            device.save()
            
            # Create a status change record if status changed
            if old_status != new_status:
                # You might want to create a model for status changes
                pass
            
            return JsonResponse({'success': True})
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            logger.error(f"Error updating device status: {e}")
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)

# Scheduled task to update device stats
def update_device_stats():
    """
    This function should be called by a scheduled task (e.g., Celery)
    to periodically update device statistics.
    """
    devices = Device.objects.all()
    
    for device in devices:
        # Check status
        old_status = device.status
        new_status = check_device_status(device.ip_address)
        
        # Update device metrics
        cpu_usage = fetch_snmp_data(device.ip_address, '1.3.6.1.4.1.2021.11.10.0')
        temperature = fetch_snmp_data(device.ip_address, '1.3.6.1.4.1.2021.13.16.0')
        latency = fetch_snmp_data(device.ip_address, '1.3.6.1.2.1.31.1.1.1.10.1')
        bandwidth = fetch_snmp_data(device.ip_address, '1.3.6.1.2.1.31.1.1.1.15.1')
        
        # Check for alerts
        alert_triggered = False
        alert_message = ""
        
        # Example alert conditions
        if new_status != old_status and new_status == 'Down':
            alert_triggered = True
            alert_message = f"Device {device.name} is down"
        
        if cpu_usage and cpu_usage > 90:
            alert_triggered = True
            alert_message += f"\nHigh CPU usage ({cpu_usage}%)"
        
        if temperature and temperature > 80:
            alert_triggered = True
            alert_message += f"\nHigh temperature ({temperature}°C)"
        
        # Update device
        device.status = new_status
        device.cpu_usage = cpu_usage
        device.temperature = temperature
        device.latency = latency
        device.bandwidth = bandwidth
        device.last_updated = timezone.now()
        device.save()
        
        # Create stats record
        stats = DeviceStats.objects.create(
            device=device,
            cpu_usage=cpu_usage,
            temperature=temperature,
            latency=latency,
            bandwidth=bandwidth,
            alert_triggered=alert_triggered,
            alert_message=alert_message.strip() if alert_triggered else ""
        )
        
        # Send notification if alert triggered
        if alert_triggered:
            try:
                # Get user notification preferences
                users = User.objects.filter(is_active=True)
                for user in users:
                    try:
                        pref = NotificationPreference.objects.get(user=user)
                        current_hour = timezone.now().hour
                        
                        # Check if notification should be sent now based on preferences
                        if str(current_hour) in pref.notification_times:
                            # Send email
                            for email in pref.emails:
                                send_mail(
                                    f"Alert for {device.name}",
                                    alert_message,
                                    settings.DEFAULT_FROM_EMAIL,
                                    [email],
                                    fail_silently=True
                                )
                    except NotificationPreference.DoesNotExist:
                        continue
            except Exception as e:
                logger.error(f"Error sending alert notification: {e}")

# API view to get alerts 
@login_required
def alerts_api(request):
    branch = request.session.get('branch', 'Unknown')
    days = int(request.GET.get('days', 7))
    
    start_date = timezone.now() - timedelta(days=days)
    alerts = DeviceStats.objects.filter(
        device__branch=branch,
        alert_triggered=True,
        timestamp__gte=start_date
    ).order_by('-timestamp')
    
    result = []
    for alert in alerts:
        result.append({
            'device_name': alert.device.name,
            'device_id': alert.device.id,
            'timestamp': alert.timestamp.strftime('%Y-%m-%d %H:%M'),
            'message': alert.alert_message
        })
    
    return JsonResponse({'alerts': result})

# Maintenance mode toggle
@login_required
def toggle_maintenance_mode(request, pk):
    device = get_object_or_404(Device, pk=pk)
    
    if request.method == 'POST':
        device.maintenance_mode = not device.maintenance_mode
        device.save()
        
        status = "enabled" if device.maintenance_mode else "disabled"
        messages.success(request, f"Maintenance mode {status} for {device.name}")
        
        return redirect('device_list')
    
    return render(request, 'toggle_maintenance.html', {'device': device})

# Renders the Zabbix-style stats dashboard HTML
@login_required
def stats_html_dashboard(request):
    return render(request, 'stats.html')
