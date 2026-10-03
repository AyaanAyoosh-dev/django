from django.urls import path, include
from . import views
from samathwacore.views import index, contact, knowmore, ourvision, terms, contactus, signup 
from django.contrib.auth import views as auth_views
from .forms import LoginForm

app_name = 'samathwacore'

urlpatterns = [
    path('', views.index, name='index'),
    path('items/', include('item.urls')),
    path('contact/', contact, name='contact'),
    path('knowmore/', knowmore, name='knowmore'),
    path('ourvision/', ourvision, name='ourvision'),
    path('terms/', terms, name='terms'),
    path('contactus/', contactus, name='contactus'),
    path('signup/', signup, name='signup'),
    path('login/', auth_views.LoginView.as_view(template_name='core/login.html', authentication_form=LoginForm), name='login'),
]


