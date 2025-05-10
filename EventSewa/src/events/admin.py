from django.contrib import admin
from .models import Event

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'event_code', 'organizer', 'date', 'location', 'capacity', 'price', 'is_active')
    list_filter = ('is_active', 'date')
    search_fields = ('name', 'event_code', 'location')
    readonly_fields = ('created_at', 'updated_at')
