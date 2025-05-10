# users/models.py
from django.db import models
from django.core.validators import RegexValidator

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
            message="Phone Number must be entered in the format: '+999999999'."
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
        db_table = 'users"."group1'
        managed = False

    def __str__(self):
        return self.username