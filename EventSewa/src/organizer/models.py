from django.db import models
from django.utils import timezone
from googlelogin.models import UserProfile

class OrganizerNotification(models.Model):
    organizer = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'organizer_notification'

    def __str__(self):
        return f"{self.title} ({self.organizer.email})"
