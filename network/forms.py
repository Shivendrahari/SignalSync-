# network/forms.py

from django import forms
from .models import Device

class DeviceForm(forms.ModelForm):
    """
    Form for adding and editing devices.
    Includes validation and read-only handling for certain fields.
    """
    class Meta:
        model = Device
        fields = ['serial_number', 'ip_address', 'name', 'model', 'branch', 'snmp_community', 'snmp_version']
        widgets = {
            'snmp_version': forms.Select(choices=[('1', 'SNMP v1'), ('2c', 'SNMP v2c'), ('3', 'SNMP v3')]),
        }

    def __init__(self, *args, **kwargs):
        super(DeviceForm, self).__init__(*args, **kwargs)

        # Make serial number read-only for existing devices
        if self.instance and self.instance.pk:
            self.fields['serial_number'].widget.attrs['readonly'] = True

    def clean_ip_address(self):
        """
        Validate that the IP address is correctly formatted.
        """
        ip_address = self.cleaned_data.get('ip_address')
        import ipaddress
        try:
            ipaddress.ip_address(ip_address)
        except ValueError:
            raise forms.ValidationError("Invalid IP address format. Please enter a valid IPv4 or IPv6 address.")
        return ip_address
