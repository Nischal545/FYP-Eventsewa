from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('googlelogin', '0007_auto_20250411_1154'),
    ]

    operations = [
        # Create events schema
        migrations.RunSQL(
            "CREATE SCHEMA IF NOT EXISTS events;",
            "DROP SCHEMA IF EXISTS events CASCADE;"
        ),
        
        # Create events table in the public schema first (for Django ORM compatibility)
        migrations.CreateModel(
            name='Event',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
                ('description', models.TextField()),
                ('date', models.DateTimeField()),
                ('location', models.CharField(max_length=255)),
                ('capacity', models.IntegerField()),
                ('price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('is_active', models.BooleanField(default=True)),
                ('event_code', models.CharField(blank=True, max_length=6, null=True, unique=True)),
                ('image', models.BinaryField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('organizer', models.ForeignKey(db_column='organizer_id', on_delete=django.db.models.deletion.CASCADE, related_name='events', to='googlelogin.organizer')),
            ],
            options={
                'db_table': 'events',
                'managed': True,
            },
        ),
    ]
