from django.contrib import admin
from django.urls import path
from engine.views.auth_views import login_view
from engine.views.worker_views import worker_dashboard_view
from engine.views.safety_views import safety_dashboard_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', login_view, name='login'),
    path('worker/dashboard/', worker_dashboard_view, name='worker_dashboard'),
    path('safety/dashboard/', safety_dashboard_view, name='safety_dashboard'),
]