import datetime
from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, F
from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from .filters import ObjectFilter
from .functions.objects import get_objects_list
from .functions.service import paginate_queryset, get_random_icon
from .functions.tasks_prepare import get_filtered_tasks, get_m2m_fields_for_tasks, task_filter_params
from .models import Object, Task, Tag, ObjectGroup


@login_required
def get_home(request):
    # Создаем фильтр с параметрами запроса
    user_filter = ObjectFilter(request.GET, queryset=get_objects_list(request))

    # Применяем фильтр к запросу
    filtered_objects = user_filter.qs

    # Получаем номер страницы из запроса
    page_number = request.GET.get("page")
    per_page = request.GET.get('per_page', 8)  # Значение по умолчанию
    pagination_data = paginate_queryset(filtered_objects, page_number, per_page)

    # Получаем теги, связанные с объектами
    tags = Tag.objects.filter(objects_set__isnull=False).filter(objects_set__groups__users=request.user).distinct()

    tags = [{"id": tag.id, "label": tag.tag_name} for tag in tags]
    # Получаем группы, связанные с объектами
    groups = ObjectGroup.objects.filter(objects_set__isnull=False).filter(users=request.user).distinct()

    groups = [{"id": group.id, "label": group.name} for group in groups]

    exclude_params = ["page"]
    filter_data = {key: value for key, value in request.GET.items() if key not in exclude_params}

    # Формируем строку с параметрами фильтра
    filter_url = urlencode(filter_data, doseq=True)

    random_icon = get_random_icon(request)

    not_count_params = ["page", "per_page"]
    # Передаем отфильтрованные объекты в контекст
    context = {
        "pagination_data": pagination_data,
        "filter_data": filter_url,
        "tags_json": tags,
        "random_icon": random_icon,
        "current_tags": request.GET.getlist("tags"),
        "groups_json": groups,
        "current_groups": request.GET.getlist("groups"),
        'current_page': request.path,
        "params_count": len([param for key, param in request.GET.items() if param and key not in not_count_params])

    }

    return render(request, "components/home/home.html", context=context)


@login_required
def get_object_page(request, object_slug):
    # Получаем основной объект
    obj = (
        Object.objects.filter(slug=object_slug)
            .prefetch_related("files", "tags", "groups")
            .annotate(
            parent_name=F("parent__name"),
            parent_slug=F("parent__slug"),
            done_tasks_count=Count("id", filter=Q(tasks__is_done=True)),
            undone_tasks_count=Count("id", filter=Q(tasks__is_done=False)),
        )
            .filter(groups__users=request.user)
            .first()
    )

    # Если объект не найден, выбрасываем исключение 404 (страница не найдена)
    if obj is None:
        raise Http404()

    # Получаем связанные задачи с учетом фильтров
    filtered_tasks_data = get_filtered_tasks(request, obj=obj)

    # Получаем номер страницы из запроса
    page_number = request.GET.get("page")
    # Используем функцию пагинации
    pagination_data = paginate_queryset(filtered_tasks_data["tasks"], page_number, per_page=8)

    filtered_tasks_data["tasks"] = pagination_data["page_obj"]

    child_objects = get_objects_list(request).filter(parent=obj)

    random_icon = get_random_icon(request)

    filter_context = task_filter_params(request)

    context = {
        "default_date": datetime.date.today().strftime("%Y-%m-%d"),
        "default_time": "17:30",
        "object": obj,
        "object_id_list": [obj.id],
        "tasks": filtered_tasks_data,
        "random_icon": random_icon,
        "pagination_data": pagination_data,
        "task_count": obj.done_tasks_count + obj.undone_tasks_count,
        "child_objects": child_objects,
        **filter_context,
        'is_objects_page': request.path.startswith('/object/'),
    }

    return render(request, "components/object/object-page.html", context=context)


@login_required
def get_tasks_page(request):
    """
    Рендер страницы с задачами
    """
    filtered_task = get_filtered_tasks(request)  # Получаем qs объект

    filter_context = task_filter_params(request)  # Получаем текущие параметры фильтра из url

    # Пагинация
    page_number = request.GET.get("page")  # Получаем номер страницы из запроса
    per_page = request.GET.get('per_page', 8)  # Получаем количество отображаемых элементов пагинации из селектора
    pagination_data = paginate_queryset(filtered_task["tasks"], page_number,
                                        per_page)  # Тут теперь хранятся и задачи и параметры пагинатора

    random_icon = get_random_icon(request)

    context = {
        "default_date": datetime.date.today().strftime("%Y-%m-%d"),
        "default_time": "17:30",
        "pagination_data": pagination_data,
        "random_icon": random_icon,
        "tasks": filtered_task,
        **filter_context,
        'current_page': request.path,
    }

    return render(request, "components/task/tasks_page.html", context=context, )


@login_required
def get_task_view(request, task_id: int):
    """
    Рендер задачи в модальном окне
    """
    # Получаем параметр from_url или используем URL по умолчанию
    from_url = request.GET.get('from_url', reverse('tasks'))

    task = get_object_or_404(Task, pk=task_id)
    context = {
        "task": task,
        "expanded": True,  # параметр для аккордеона, без него будет раскрыт
        "form_type": "collapse",
        'from_url': from_url,  # Передаем URL с фильтрами в контекст
    }
    return render(request, "components/task/task.html", context=context)


@login_required
def get_map_page(request):
    return render(request, "components/map/map.html")


@login_required
def get_calendar_page(request):
    random_icon = get_random_icon(request)
    tasks = get_filtered_tasks(request)
    filter_context = task_filter_params(request)

    return render(
        request,
        "components/calendar/calendar.html",
        {"default_date": datetime.date.today().strftime("%Y-%m-%d"),
         "default_time": "17:30", "tasks": tasks, **filter_context, "random_icon": random_icon,
         'current_page': request.path, }
    )


@login_required
def get_task_edit_form(request, task_id: int):
    task = get_object_or_404(Task, pk=task_id)
    fields = get_m2m_fields_for_tasks()

    from_url = request.GET.get('from_url', reverse('tasks'))

    current_engineers_with_type = list(task.engineers.all().values_list("id", flat=True))
    current_departaments_with_type = list(task.departments.all().values_list("id", flat=True))

    current_engineers = []
    for each in current_engineers_with_type:
        current_engineers.append(f"eng_{each}")

    for each in current_departaments_with_type:
        current_engineers.append(f"dep_{each}")

    context = {
        "task": task,
        **fields,
        "from_url": from_url,
        "current_engineers": current_engineers,
        "current_tags_edit": list(task.tags.all().values_list("id", flat=True)),
        "current_objects_edit": list(task.objects_set.all().values_list("id", flat=True)),
    }
    return render(request, 'components/task/edit_task_form.html', context)
