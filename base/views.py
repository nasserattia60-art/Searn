from django.shortcuts import render

# Create your views here.

def home(request):
    return render(request, 'base/home.html')

def handler404(request, exception):
    return render(request, 'base/404.html', status=404)

def handler403(request, exception):
    return render(request, 'base/403.html', status=403)

def handler500(request):
    return render(request, 'base/500.html', status=500)