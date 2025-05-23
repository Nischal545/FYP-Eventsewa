# Generated by Django 5.0.6 on 2025-04-11 04:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('googlelogin', '0004_event_eventhistory'),
    ]

    operations = [
        migrations.CreateModel(
            name='OrganizerRequest',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('organization_name', models.CharField(max_length=100)),
                ('username', models.CharField(max_length=100, unique=True)),
                ('owner_names', models.TextField()),
                ('email', models.CharField(max_length=255, unique=True)),
                ('password', models.CharField(max_length=100)),
                ('address', models.TextField()),
                ('phone', models.CharField(max_length=15)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')], default='pending', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'organizer_requests',
                'managed': False,
            },
        ),
        migrations.AlterModelTable(
            name='admin',
            table='admins',
        ),
        migrations.AlterModelTable(
            name='event',
            table='event',
        ),
        migrations.AlterModelTable(
            name='eventhistory',
            table='event_history',
        ),
        migrations.AlterModelTable(
            name='organizer',
            table='organizers',
        ),
        migrations.AlterModelTable(
            name='userprofile',
            table='group1',
        ),
    ]
