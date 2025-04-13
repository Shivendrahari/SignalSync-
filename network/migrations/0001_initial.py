# Generated by Django 5.1 on 2024-08-27 09:37

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Device',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('serial_number', models.CharField(max_length=10)),
                ('ip', models.GenericIPAddressField()),
                ('name', models.CharField(max_length=100)),
                ('model', models.CharField(max_length=100)),
                ('status', models.CharField(choices=[('Up', 'Up'), ('Down', 'Down')], max_length=10)),
                ('branch', models.CharField(max_length=100)),
            ],
        ),
    ]
