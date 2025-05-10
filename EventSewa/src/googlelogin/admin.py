from django.contrib import admin
from .models import Organizer, Event, EventHistory, OrganizerRequest, Admin
from django.utils.html import format_html

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('name', 'date', 'location', 'capacity', 'price', 'organizer', 'event_code')
    list_filter = ('date', 'organizer')
    search_fields = ('name', 'location', 'event_code')
    readonly_fields = ('event_code', 'created_at', 'updated_at')
    fieldsets = (
        ('Event Information', {
            'fields': ('name', 'description', 'date', 'location', 'capacity', 'price')
        }),
        ('Organizer Information', {
            'fields': ('organizer',)
        }),
        ('System Information', {
            'fields': ('event_code', 'created_at', 'updated_at', 'expiration'),
            'classes': ('collapse',)
        }),
    )

    def show_image(self, obj):
        if obj.image:
            return format_html('<img src="data:image/jpeg;base64,{}" width="50" height="50"/>', obj.image.decode('utf-8'))
        return "No image"
    show_image.short_description = 'Event Image'

    def save_model(self, request, obj, form, change):
        if not obj.event_code:
            obj.event_code = Event.generate_event_code()
        super().save_model(request, obj, form, change)
