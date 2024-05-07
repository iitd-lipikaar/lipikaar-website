from django.shortcuts import render
from django.http import HttpResponse
from django.views.generic import TemplateView
from django.views.decorators.cache import never_cache


# Serve single-page React app
# index = never_cache(TemplateView.as_view(template_name="index.html"))

def index(request):
    # return HttpResponse("<h1>Hello</h1>")

    return render(request, "index.html")