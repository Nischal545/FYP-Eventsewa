from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

    dependencies = [
        ('googlelogin', '0007_auto_20250411_1154'),
    ]

    operations = [
        migrations.RunSQL(
            """
            DROP TABLE IF EXISTS organizers;
            CREATE TABLE organizers (
                id SERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES group1(id) ON DELETE CASCADE,
                organization_name VARCHAR(100) NOT NULL,
                username VARCHAR(100) UNIQUE NOT NULL,
                owner_names TEXT NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                password VARCHAR(100) NOT NULL,
                address TEXT NOT NULL,
                verification_status BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """,
            """
            DROP TABLE IF EXISTS organizers;
            """
        ),
    ] 