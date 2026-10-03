from django.shortcuts import render,redirect
from django.http import HttpResponse
from item.models import Category, Item # type: ignore

from .forms import SignupForm

def index(request):
    items = Item.objects.filter(Service_Avaialble=True)
    categories = Category.objects.all()
    return render(request, 'core/index.html', {
        'categories': categories,
        'items': items,
    })

# Define a contact view that renders the contact.html template
def contact(request):
   return render(request, 'core/contact.html')
def knowmore(request):
   return render(request, 'core/knowmore.html')
def ourvision(request):
   return render(request, 'core/ourvision.html')
def terms(request):
   return render(request, 'core/terms.html')
   
def contactus(request):
   return render(request, 'core/contactus.html')

def signup(request):
   if request.method == 'POST':
      form = SignupForm(request.POST)

      if form.is_valid():  
         form.save()

         return redirect('/login/')
   else:

      form = SignupForm()

   return render(request, 'core/signup.html', {
                      
      'form': form

   })