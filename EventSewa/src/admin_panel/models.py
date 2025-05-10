from django.db import models

class Admin(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    email = models.CharField(max_length=255)
    username = models.CharField(max_length=50)
    password = models.CharField(max_length=100)
    type = models.CharField(max_length=50, default='event_checker')

    class Meta:
        db_table = 'users"."admins'
        managed = False

    def __str__(self):
        return self.username


class OrganizerRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ]
    
    email = models.EmailField()
    organization_name = models.CharField(max_length=255)
    description = models.TextField()
    website = models.URLField(null=True, blank=True)
    phone = models.CharField(max_length=20)
    address = models.CharField(max_length=255)
    password = models.CharField(max_length=128)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    rejection_reason = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'organizer_request'
        managed = False

    def __str__(self):
        return f"{self.organization_name} ({self.status})"