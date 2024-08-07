from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404
from .models import Object
from django.urls import reverse


def get_home(request):
    objects_ = Object.objects.all()
    data = []
    for item in objects_:
        attached_files = item.files.all()
        img_preview = attached_files.filter(file__regex=r'\.(jpeg|jpg|png)$').first()

        data.append({"id": item.pk,
                    "title": item.name,
                    "desc": item.description,
                    "img_preview": img_preview.file.url, })


    context = {"objects": data}

    return render(request, "home.html", context=context)


def get_object_page(request, object_id):
    object = get_object_or_404(Object, pk=object_id)
    context = {"object": object}
    return render(request, "object-page.html", context=context)

