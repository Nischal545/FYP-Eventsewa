from django.db import models
from django.utils import timezone
from googlelogin.models import Organizer
import random
import string

class Event(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    organizer = models.ForeignKey(Organizer, on_delete=models.CASCADE, db_column='organizer_id', related_name='events')
    description = models.TextField()
    date = models.DateTimeField()
    location = models.CharField(max_length=255)
    capacity = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)
    event_code = models.CharField(max_length=6, unique=True, null=True, blank=True)
    image = models.BinaryField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'events'
        managed = True

    @property
    def total_revenue(self):
        return float(self.price * self.capacity)

    @property
    def platform_fee(self):
        return float(self.total_revenue * 0.1)

    @classmethod
    def generate_event_code(cls):
        while True:
            letters = ''.join(random.choices(string.ascii_uppercase, k=2))
            digits = ''.join(random.choices(string.digits, k=4))
            code = letters + digits
            if not cls.objects.filter(event_code=code).exists():
                return code
