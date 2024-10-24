from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, F
from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from tasks.services.tree_nodes import GroupsTree, ObjectsTagsTree
from .filters import ObjectFilter
from .forms import CKEditorEditForm, CKEditorCreateForm, CKEditorEditObjForm
from .functions.objects import get_objects_list, add_tasks_count_to_objects
from .functions.service import paginate_queryset, get_random_icon
from .functions.tasks_prepare import get_filtered_tasks, get_m2m_fields_for_tasks, task_filter_params
from .models import Object, Task, Engineer
from django.core.cache import cache

from .services.tree_nodes.tree_nodes import AllTagsTree


@login_required
def get_home(request):
    page_number = request.GET.get("page", 1)  # Упрощение получения номера страницы
    # Используем фильтры для создания уникального кэш-ключа
    filter_params = urlencode({key: value for key, value in request.GET.items() if key not in ["page", "per_page"]})
    cache_key = f'objects-page:{page_number}:{request.user.username}:{filter_params}'

    # Получаем данные из кэша
    cached_data = cache.get(cache_key)

    # =========== Кеширование =========== #
    if cached_data is None:
        # =========== Фильтр =========== #
        tags = ObjectsTagsTree({"user": request.user}).get_nodes()
        groups = GroupsTree({"user": request.user}).get_nodes()

        user_filter = ObjectFilter(request.GET, queryset=get_objects_list(request))
        filtered_objects = user_filter.qs  # Применяем фильтр к запросу

        # Счётчик применённых фильтров
        not_count_params = ["page", "per_page"]
        params_count = len([param for key, param in request.GET.items() if param and key not in not_count_params])

        # =========== Пагинация =========== #
        per_page = request.GET.get("per_page", 8)
        pagination_data = paginate_queryset(filtered_objects, page_number, per_page)
        objects_qs = pagination_data["page_obj"]

        add_tasks_count_to_objects(queryset=objects_qs, user=request.user, field_name="tasks_count")

        # Сохраняем данные в кэш
        cached_data = {
            "objects_qs": objects_qs,
            "pagination_data": pagination_data,
            "tags": tags,
            "groups": groups,
            "current_path": request.path,
            "params_count": params_count,
        }
        cache.set(cache_key, cached_data, timeout=60)
    else:
        # Используем закэшированные данные
        objects_qs = cached_data["objects_qs"]
        pagination_data = cached_data["pagination_data"]
        tags = cached_data["tags"]
        groups = cached_data["groups"]
        params_count = cached_data["params_count"]

    # Формируем строку с параметрами фильтра для пагинатора
    exclude_params = ["page"]
    filter_data = {key: value for key, value in request.GET.items() if key not in exclude_params}
    filter_url = urlencode(filter_data, doseq=True)

    context = {
        "objects_qs": objects_qs,
        "pagination_data": pagination_data,
        "filter_data": filter_url,
        "tags_json": tags,
        "random_icon": get_random_icon(request),
        "current_tags": request.GET.getlist("tags"),
        "groups_json": groups,
        "current_groups": request.GET.getlist("groups"),
        "current_page": request.path,
        "params_count": params_count,
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

    if obj:
        # Получаем все связанные файлы
        attached_files = obj.files.all()

        # Разделяем файлы на изображения и не-изображения
        images = [file for file in attached_files if file.is_image]  # Используем поле is_image
        non_images = [file for file in attached_files if not file.is_image]  # Используем поле is_image
    else:
        images = []
        non_images = []

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
        "obj_images": images,
        "obj_files": non_images,
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
def get_obj_edit_form(request, slug: int):

    obj = get_object_or_404(Object, slug=slug)
    groups = GroupsTree({"user": request.user}).get_nodes()
    tags = AllTagsTree({"user": request.user}).get_nodes()


    ckeditor__obj_form = CKEditorEditObjForm(initial={"description": obj.description})

    context = {
        "object": obj,
        "ckeditor__obj_form": ckeditor__obj_form,

        "edit_tags_json": tags,
        "edit_current_tags": list(obj.tags.all().values_list("tag_name", flat=True)),

        "edit_groups_json": groups,
        "edit_current_groups": list(obj.groups.all().values_list("id", flat=True)),
    }
    return render(request, "components/object/edit_obj_form.html", context)


@login_required
def get_task_action_form(request, task_id, action_type):
    task = get_object_or_404(Task, pk=task_id)

    # Determine the form action (close or reopen)
    if action_type == 'close':
        action_url = reverse('close_task', args=[task_id])
        form_action = 'close'
    else:
        action_url = reverse('reopen_task', args=[task_id])
        form_action = 'reopen'

    context = {
        'task_id': task_id,
        'form_action': form_action,
        'action_url': action_url,
        'from_url': request.GET.get('from_url', ''),
    }

    return render(request, 'components/task/confirm_task_form.html', context)


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
