from django.http import HttpResponse
from django.shortcuts import render


def index(request):
    data = {"user_name": "Янковский С."}
    return render(request, "home.html", context=data)


def get_object_page(request):
    data = {"user_name": "user_name111"}
    return render(request, "object-page.html", context=data)