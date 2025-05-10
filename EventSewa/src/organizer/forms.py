from django import forms
from googlelogin.models import Event

class EventForm(forms.ModelForm):
    performer_name = forms.CharField(
        max_length=255, 
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter performer or artist name'
        })
    )
    start_time = forms.TimeField(
        widget=forms.TimeInput(attrs={
            'type': 'time',
            'class': 'form-control',
            'placeholder': 'Start time'
        }), 
        required=True
    )
    end_time = forms.TimeField(
        widget=forms.TimeInput(attrs={
            'type': 'time',
            'class': 'form-control',
            'placeholder': 'End time'
        }), 
        required=True
    )
    description = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 4, 
            'class': 'form-control',
            'placeholder': 'Provide a detailed description of your event, including what attendees can expect'
        }), 
        required=True
    )
    
    class Meta:
        model = Event
        fields = ['name', 'date', 'location', 'capacity', 'price']
        widgets = {
            'date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'price': forms.NumberInput(attrs={
                'step': '0.01', 
                'class': 'form-control',
                'placeholder': 'Enter ticket price in NPR'
            }),
            'capacity': forms.NumberInput(attrs={
                'min': '1', 
                'class': 'form-control',
                'placeholder': 'Enter maximum number of attendees'
            }),
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter a descriptive title for your event'
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter the full venue address'
            }),
        }
        labels = {
            'name': 'Event Title',
            'date': 'Event Date',
            'location': 'Venue Location',
            'capacity': 'Audience Capacity',
            'price': 'Ticket Price (NPR)',
        }
        help_texts = {
            'name': 'Enter the title of your event',
            'date': 'Select the date of your event',
            'location': 'Enter the venue location',
            'capacity': 'Maximum number of attendees',
            'price': 'Price per ticket in NPR',
        }