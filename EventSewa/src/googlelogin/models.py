from django.db import models
from django.core.validators import RegexValidator
from decimal import Decimal
import random
import string
from django.db import connection
from datetime import datetime

class Admin(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    email = models.CharField(max_length=255)
    username = models.CharField(max_length=50)
    password = models.CharField(max_length=100)
    type = models.CharField(max_length=50, default='event_checker')

    class Meta:
        db_table = 'admins'
        managed = False

    def __str__(self):
        return self.username

class UserProfile(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=100)
    username = models.CharField(max_length=50)
    email = models.EmailField(max_length=255, unique=True)
    phone_number = models.CharField(
        max_length=15,
        unique=True,
        validators=[RegexValidator(
            regex=r'^\+?1?\d{10,15}$',
            message="Phone Number must be entered in the format: '+999999999'. Up to 15 digits allowed."
        )]
    )
    password = models.CharField(max_length=128)
    gender = models.CharField(max_length=10, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    image = models.TextField(blank=True, null=True)
    dob = models.DateField(blank=True, null=True)
    signup_date = models.DateTimeField(auto_now_add=True)
    points = models.IntegerField(default=0)
    verification_status = models.BooleanField(default=False)

    class Meta:
        db_table = 'group1'
        managed = False
        ordering = ['username']

    def __str__(self):
        return self.username

class Organizer(models.Model):
    id = models.AutoField(primary_key=True)
    user_id = models.BigIntegerField()
    organization_name = models.CharField(max_length=100)
    username = models.CharField(max_length=100, unique=True)
    owner_names = models.TextField()
    email = models.CharField(max_length=255, unique=True)
    password = models.CharField(max_length=100)
    address = models.TextField()
    verification_status = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'organizers'
        managed = False

    def __str__(self):
        return self.organization_name

class Event(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    date = models.DateField()
    location = models.CharField(max_length=255)
    capacity = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    organizer = models.ForeignKey(Organizer, on_delete=models.CASCADE)
    event_code = models.CharField(max_length=10, unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expiration = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'events'
        managed = False

    def save(self, *args, **kwargs):
        if not self.event_code:
            self.event_code = self.generate_event_code()
        
        # Combine date with start_time and end_time to create expiration
        if hasattr(self, 'start_time') and hasattr(self, 'end_time'):
            self.expiration = datetime.combine(self.date, self.end_time)
        
        super().save(*args, **kwargs)

    def generate_event_code(self):
        while True:
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            if not Event.objects.filter(event_code=code).exists():
                return code

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.event_code:
            self.event_code = self.generate_event_code()
        
        # First save the event to get an ID
        super().save(*args, **kwargs)
        
        # Create the event-specific table in events schema
        table_name = f"{self.name.lower().replace(' ', '_')}_{self.event_code}"
        with connection.cursor() as cursor:
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS events.{table_name} (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    ticket_quantity INTEGER NOT NULL,
                    booking_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users.auth_user(id)
                )
            """)

    @property
    def total_revenue(self):
        return float(self.price * self.capacity)

    @property
    def platform_fee(self):
        return float(self.total_revenue * 0.1)

class EventHistory(models.Model):
    OCCURRENCE_CHOICES = [
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('failed', 'Failed')
    ]
    PAYMENT_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('unpaid', 'Unpaid')
    ]
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    admin = models.ForeignKey(Admin, on_delete=models.CASCADE)
    occurrence_status = models.CharField(max_length=20, choices=OCCURRENCE_CHOICES, default='pending')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_CHOICES, default='pending')
    marketing_fee = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    total_revenue = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    verification_date = models.DateTimeField(null=True, blank=True)
    failure_reason = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'event_history'
        managed = False

    def __str__(self):
        return f"{self.event.name} - {self.occurrence_status}"

class OrganizerRequest(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='organizer_requests', db_column='user_id')
    organization_name = models.CharField(max_length=100)
    username = models.CharField(max_length=100, unique=True)
    owner_names = models.TextField()
    email = models.CharField(max_length=255, unique=True)
    password = models.CharField(max_length=100)
    address = models.TextField()
    phone = models.CharField(max_length=15)
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ], default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'users"."organizer_requests'
        managed = False

    def __str__(self):
        return self.organization_name