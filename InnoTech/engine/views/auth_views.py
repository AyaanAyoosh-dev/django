from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from engine.models import UserProfile

def login_view(request):
    """Handles secure industrial login and automatic database role/factory routing."""
    error_message = None

    if request.method == "POST":
        username_input = request.POST.get("username")
        password_input = request.POST.get("password")
        
        # 1. Authenticate credentials via Django's auth system
        user = authenticate(request, username=username_input, password=password_input)
        
        if user is not None:
            login(request, user)
            
            try:
                # 2. Automatically pull factory and role from the UserProfile database
                profile = UserProfile.objects.get(user=user)
                request.session['factory'] = profile.factory_name
                request.session['role'] = profile.role
                
                # 3. Route based strictly on database permissions
                if profile.role == "worker":
                    return redirect('worker_dashboard')
                elif profile.role == "safety_officer":
                    return redirect('safety_dashboard')
                    
            except UserProfile.DoesNotExist:
                error_message = "Access Denied: No industrial profile assigned to this user."
        else:
            error_message = "Invalid username or password."

    return render(request, 'login.html', {'error': error_message})