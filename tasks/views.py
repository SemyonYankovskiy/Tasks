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

        if len(item.description)>50:
            desc = item.description[:50]+ "..."
        else: desc = item.description

        data.append({"id": item.pk,
                    "title": item.name,
                    "desc": desc,
                    "priority": item.priority,
                    "img_preview": img_preview.file.url if img_preview else None, })


    context = {"objects": data}

    return render(request, "home.html", context=context)


# def get_object_page(request, object_id):
#     object = get_object_or_404(Object, pk=object_id)
#     context = {"object": object}
#     return render(request, "object-page.html", context=context)
def get_object_page(request, object_id):
    object = get_object_or_404(Object, pk=object_id)

    # Подсчёт задач
    tasks = object.tasks.all()
    task_count = sum(1 for task in tasks if task)
    done_count = sum(1 for task in tasks if task.is_done is True)
    not_done_count = sum(1 for task in tasks if task.is_done is False)

    context = {
        "object": object,
        "task_count": task_count,
        "done_count": done_count,
        "not_done_count": not_done_count,
    }

    return render(request, "object-page.html", context=context)
