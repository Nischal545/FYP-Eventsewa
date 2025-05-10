from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('events', '0001_initial'),
    ]

    operations = [
        # Copy data from old event table to new events table
        migrations.RunSQL(
            """
            INSERT INTO events (
                id, name, organizer_id, description, date, location, capacity, 
                price, is_active, event_code, image, created_at, updated_at
            )
            SELECT 
                id, name, organizer_id, description, date, location, capacity, 
                price, is_active, event_code, image, created_at, updated_at
            FROM event
            ON CONFLICT (id) DO NOTHING;
            """,
            # Rollback SQL - do nothing as we want to keep the data
            "SELECT 1;"
        ),
    ]
