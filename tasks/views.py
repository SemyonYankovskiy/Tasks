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

        groups_arr = []
        item_groups_all = item.groups.all()
        for group in item_groups_all:

            groups_arr.append(group)
        print(groups_arr)
        data.append({"id": item.pk,
                    "groups": groups_arr,
                    "title": item.name,
                    "desc": desc,
                    "priority": item.priority,
                    "img_preview": img_preview.file.url if img_preview else None, })


    context = {"objects": data}

    return render(request, "home.html", context=context)



def get_object_page(request, object_id):
    object = get_object_or_404(Object, pk=object_id)

    # Подсчёт задач
    tasks = object.tasks.all()
    task_count = sum(1 for task in tasks if task)
    done_count = sum(1 for task in tasks if task.is_done is True)
    not_done_count = sum(1 for task in tasks if task.is_done is False)

    # Получаем дочерние объекты
    child_objects = Object.objects.filter(parent=object)

    # Исключаем первый объект из списка дочерних объектов
    if child_objects.exists():
        child_objects_excluding_first = child_objects[1:]
    else:
        child_objects_excluding_first = child_objects

    # Подготовка данных дочерних объектов
    child_data = []
    for child in child_objects:
        attached_files = child.files.all()
        img_preview = attached_files.filter(file__regex=r'\.(jpeg|jpg|png)$').first()

        desc = child.description[:50] + "..." if len(child.description) > 50 else child.description

        child_data.append({
            "id": child.pk,
            "title": child.name,
            "desc": desc,
            "priority": child.priority,
            "img_preview": img_preview.file.url if img_preview else None,
        })


    context = {
        "object": object,
        "task_count": task_count,
        "done_count": done_count,
        "not_done_count": not_done_count,
        "child_objects": child_objects_excluding_first,  # Добавляем исключённые объекты в контекст
        "child_data": child_data,
    }


    return render(request, "object-page.html", context=context)


