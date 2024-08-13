# from django.http import HttpResponse
# from django.shortcuts import render, get_object_or_404
# from .models import Object
# from django.urls import reverse
#
#
# def get_home(request):
#     objects_ = Object.objects.all()
#     data = []
#     for item in objects_:
#         attached_files = item.files.all()
#         img_preview = attached_files.filter(file__regex=r'\.(jpeg|jpg|png)$').first()
#
#         if len(item.description)>50:
#             desc = item.description[:50]+ "..."
#         else: desc = item.description
#
#         groups_arr = []
#         item_groups_all = item.groups.all()
#         for group in item_groups_all:
#             groups_arr.append(group)
#
#         data.append({"id": item.pk,
#                     "groups": groups_arr,
#                     "title": item.name,
#                     "desc": desc,
#                     "priority": item.priority,
#                     "img_preview": img_preview.file.url if img_preview else None, })
#
#
#     context = {"objects": data}
#
#     return render(request, "home.html", context=context)
#
#
#
# def get_object_page(request, object_id):
#     object = get_object_or_404(Object, pk=object_id)
#
#     # Подсчёт задач
#     tasks = object.tasks.all()
#     task_count = sum(1 for task in tasks if task)
#     done_count = sum(1 for task in tasks if task.is_done is True)
#     not_done_count = sum(1 for task in tasks if task.is_done is False)
#
#     # Получаем дочерние объекты
#     child_objects = Object.objects.filter(parent=object)
#
#     # Исключаем первый объект из списка дочерних объектов
#     if child_objects.exists():
#         child_objects_excluding_first = child_objects[1:]
#     else:
#         child_objects_excluding_first = child_objects
#
#     # Подготовка данных дочерних объектов
#     child_data = []
#     for child in child_objects:
#         attached_files = child.files.all()
#         img_preview = attached_files.filter(file__regex=r'\.(jpeg|jpg|png)$').first()
#
#         desc = child.description[:50] + "..." if len(child.description) > 50 else child.description
#
#         groups_arr = []
#         item_groups_all = child.groups.all()
#         for group in item_groups_all:
#             groups_arr.append(group)
#
#         child_data.append({
#             "id": child.pk,
#             "groups": groups_arr,
#             "title": child.name,
#             "desc": desc,
#             "priority": child.priority,
#             "img_preview": img_preview.file.url if img_preview else None,
#         })
#
#
#     context = {
#         "object": object,
#         "task_count": task_count,
#         "done_count": done_count,
#         "not_done_count": not_done_count,
#         "child_objects": child_objects_excluding_first,  # Добавляем исключённые объекты в контекст
#         "child_data": child_data,
#     }
#
#
#     return render(request, "object-page.html", context=context)


from django.db.models import Count, Q, F, OuterRef, Subquery, When, Case, Value, CharField
from django.db.models.functions import Substr, Concat, Length
from django.http import Http404
from django.shortcuts import render
from .models import Object, Task, AttachedFile


def get_objects_list(request):
    # Создаем подзапрос для получения первого файла изображения (jpeg, jpg, png)
    image_subquery = (
        AttachedFile.objects.filter(objects_set=OuterRef("pk"), file__iregex=r"\.(jpeg|jpg|png)$")
            .order_by("id")  # Сортируем по идентификатору
            .values("file")[:1]  # Получаем только поле 'file' и ограничиваем результат одним элементом
    )

    # Подзапрос для получения количества детей у объекта
    child_count_subquery = (
        Object.objects.filter(parent=OuterRef("pk"))  # Фильтруем объекты, у которых родитель - текущий объект
            .values("id")  # Получаем идентификаторы детей
    )


    # Основной запрос для получения списка объектов
    return (
        Object.objects.all()  # Получаем все объекты
            .prefetch_related("tags", "groups")  # Предварительно загружаем связанные теги и группы для оптимизации запросов
                                                # метод для указания на поля ManyToMany

            #.select_related()                  # метод для указания на поля ForeignKey
            .annotate(
                img_preview=Subquery(image_subquery),  # Добавляем аннотацию с изображением
                child_count=Count("children"),  # Подсчитываем количество детей (объектов, у которых этот объект является родителем)
                description_length=Length("description"),  # Получаем длину полного описания
                short_description=Case(
                    When(description_length__gt=53, then=Concat(Substr("description", 1, 50), Value("..."))),
                    # Если длина описания больше 53, добавляем '...'
                    default="description",  # В противном случае используем полное описание
                    output_field=CharField(),  # Указываем, что тип поля - строка
                ),

            )
            .only("id", "name", "priority")  # Ограничиваем выборку только необходимыми полями
                                            # метод для указания на собственные поля модели

            .filter(groups__users=request.user)  # Фильтруем объекты по пользователям в группах
            .distinct()  # Убираем дублирование объектов
            .order_by("parent_id", "-id")
    )


def get_home(request):
    context = {"objects": get_objects_list(request)}

    return render(request, "home.html", context=context)


def get_object_page(request, object_id):
    obj = (
        Object.objects.filter(pk=object_id)  # Фильтруем объекты по ID
            .prefetch_related("files", "tags", "groups")  # Загружаем связанные файлы, теги и группы # метод для указания на поля ManyToMany
            .annotate(
                parent_name=F("parent__name"),
                done_tasks_count=Count("id", filter=Q(tasks__is_done=True)),  # Подсчитываем выполненные задачи
                undone_tasks_count=Count("id", filter=Q(tasks__is_done=False)),  # Подсчитываем невыполненные задачи
            )
            .filter(groups__users=request.user)  # Фильтруем объекты, к которым имеет доступ текущий пользователь через группы
            .first()  # Получаем первый (и единственный) объект или None, если не найден
    )

    # Если объект не найден, выбрасываем исключение 404 (страница не найдена)
    if obj is None:
        raise Http404()

    # Получаем связанные задачи для данного объекта.
    # Используем prefetch_related для оптимизации выборки связанных данных (файлы, теги, инженеры).
    tasks = Task.objects.filter(objects_set=obj).prefetch_related("files", "tags", "engineers")


    # Получаем дочерние объекты, связанные с текущим объектом (если есть).
    # Предполагается, что функция get_objects_list возвращает QuerySet объектов.
    child_objects = get_objects_list(request).filter(parent=obj)

    # Формируем контекст для передачи в шаблон.
    context = {
        "object": obj,  # Основной объект
        "tasks": tasks,  # Задачи, связанные с объектом
        "parent_name": obj.parent_name,
        "task_count": obj.done_tasks_count + obj.undone_tasks_count,  # Общее количество задач
        "done_count": obj.done_tasks_count,  # Количество выполненных задач
        "not_done_count": obj.undone_tasks_count,  # Количество невыполненных задач
        "child_objects": child_objects,  # Дочерние объекты
    }

    # Рендерим шаблон "object-page.html" с переданным контекстом.
    return render(request, "object-page.html", context=context)