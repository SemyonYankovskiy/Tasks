from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, F
from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from tasks.services.tree_nodes import GroupsTree, ObjectsTagsTree
from .filters import ObjectFilter
from .forms import CKEditorEditForm, CKEditorCreateForm
from .functions.objects import get_objects_list, add_tasks_count_to_objects
from .functions.service import paginate_queryset, get_random_icon
from .functions.tasks_prepare import get_filtered_tasks, get_m2m_fields_for_tasks, task_filter_params
from .models import Object, Task, Engineer


@login_required
def get_home(request):
    # Создаем фильтр с параметрами запроса
    user_filter = ObjectFilter(request.GET, queryset=get_objects_list(request))

    # Применяем фильтр к запросу
    filtered_objects = user_filter.qs

    # Получаем номер страницы из запроса
    page_number = request.GET.get("page")
    per_page = request.GET.get("per_page", 8)  # Значение по умолчанию
    pagination_data = paginate_queryset(filtered_objects, page_number, per_page)
    objects_qs = pagination_data["page_obj"]

    add_tasks_count_to_objects(queryset=objects_qs, user=request.user, field_name="tasks_count")

    tags = ObjectsTagsTree({"user": request.user}).get_nodes()
    groups = GroupsTree({"user": request.user}).get_nodes()

    exclude_params = ["page"]
    filter_data = {key: value for key, value in request.GET.items() if key not in exclude_params}

    # Формируем строку с параметрами фильтра
    filter_url = urlencode(filter_data, doseq=True)

    random_icon = get_random_icon(request)

    not_count_params = ["page", "per_page"]
    # Передаем отфильтрованные объекты в контекст
    context = {
        "objects_qs": objects_qs,
        "pagination_data": pagination_data,
        "filter_data": filter_url,
        "tags_json": tags,
        "random_icon": random_icon,
        "current_tags": request.GET.getlist("tags"),
        "groups_json": groups,
        "current_groups": request.GET.getlist("groups"),
        "current_page": request.path,
        "params_count": len(
            [param for key, param in request.GET.items() if param and key not in not_count_params]
        ),
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
    pagination_data = paginate_queryset(filtered_tasks_data.tasks, page_number, per_page=8)

    tasks = pagination_data["page_obj"]

    child_objects = get_objects_list(request).filter(parent=obj)

    random_icon = get_random_icon(request)

    filter_context = task_filter_params(request)
    ckeditor = CKEditorCreateForm(request.POST)

    context = {
        "object": obj,
        "object_id_list": [obj.id],
        "tasks": tasks,
        "counters": filtered_tasks_data.tasks_counters,
        "filter_params": filtered_tasks_data.filter_params,
        "random_icon": random_icon,
        "pagination_data": pagination_data,
        "child_objects": child_objects,
        **filter_context,
        "is_objects_page": request.path.startswith("/object/"),
        "ckeditor": ckeditor,
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
    per_page = request.GET.get(
        "per_page", 8
    )  # Получаем количество отображаемых элементов пагинации из селектора

    # Тут теперь хранятся и задачи и параметры пагинатора
    pagination_data = paginate_queryset(filtered_task.tasks, page_number, per_page)

    random_icon = get_random_icon(request)

    ckeditor = CKEditorCreateForm(request.POST)

    context = {
        "pagination_data": pagination_data,
        "random_icon": random_icon,
        "counters": filtered_task.tasks_counters,
        "filter_params": filtered_task.filter_params,
        **filter_context,
        "current_page": request.path,
        "ckeditor": ckeditor,

    }

    return render(request, "components/task/tasks_page.html", context=context)


@login_required
def get_task_view(request, task_id: int):
    """
    Рендер задачи в модальном окне
    """
    task = get_object_or_404(Task, pk=task_id)
    context = {
        "task": task,
        "expanded": True,  # параметр для аккордеона, без него будет раскрыт
        "form_type": "collapse",
    }
    return render(request, "components/task/task.html", context=context)


@login_required
def get_map_page(request):
    return render(request, "components/map/map.html")


@login_required
def get_calendar_page(request):
    tasks = get_filtered_tasks(request)
    filter_context = task_filter_params(request)

    return render(
        request,
        "components/calendar/calendar.html",
        {
            "tasks": tasks,
            **filter_context,
            "random_icon": get_random_icon(request),
            "current_page": request.path,
            "c": tasks.tasks_counters,
            "fp": tasks.filter_params,
        },
    )


@login_required
def get_task_edit_form(request, task_id: int):
    task = get_object_or_404(Task, pk=task_id)
    fields = get_m2m_fields_for_tasks(request.user)

    from_url = request.GET.get("from_url", reverse("tasks"))

    current_engineers_with_type = list(task.engineers.all().values_list("id", flat=True))
    current_departments_with_type = list(task.departments.all().values_list("id", flat=True))

    current_engineers = []
    for each in current_engineers_with_type:
        current_engineers.append(f"eng_{each}")

    for each in current_departments_with_type:
        current_engineers.append(f"dep_{each}")

    ckeditor_form = CKEditorEditForm(initial={"text_edit": task.text})

    context = {
        "task": task,
        **fields,
        "from_url": from_url,
        "current_engineers": current_engineers,
        "ckeditor_form": ckeditor_form,
        # "current_tags_edit": list(task.tags.all().values_list("id", flat=True)),
        "current_tags_edit": list(task.tags.all().values_list("tag_name", flat=True)),
        "current_objects_edit": list(task.objects_set.all().values_list("id", flat=True)),
    }
    return render(request, "components/task/edit_task_form.html", context)


@login_required
def get_stat_page(request):
    # Выбираем всех инженеров с данными по активным и завершённым задачам
    engineers = (Engineer.objects.all()
                 .prefetch_related("tasks")
                 .select_related("department")
                 .annotate(
                     active_task_count=Count('tasks', filter=Q(tasks__is_done=False)),  # Подсчёт активных задач
                     completed_task_count=Count('tasks', filter=Q(tasks__is_done=True))  # Подсчёт завершённых задач
                 ))

    # Собираем данные для каждого инженера
    engineer_stats = []
    for engineer in engineers:
        engineer_stats.append({
            'first_name': engineer.first_name,
            'second_name': engineer.second_name,
            'department': engineer.department.name if engineer.department else 'Нет департамента',
            'active_tasks_count': engineer.active_task_count,
            'completed_tasks_count': engineer.completed_task_count,
        })

    context = {
        'random_icon': get_random_icon(request),  # Ваша функция для получения случайного значка (если нужно)
        'engineer_stats': engineer_stats,
    }

    return render(request, 'stat_page.html', context)
