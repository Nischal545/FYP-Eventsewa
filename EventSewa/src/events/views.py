from django.shortcuts import render
from django.contrib import messages

def events_list(request):
    return render(request, 'events/list.html') 