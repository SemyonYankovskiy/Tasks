from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from tasks.services.objects import get_objects, get_single_object, get_child_objects
from tasks.services.tasks_prepare import get_tasks
from tasks.services.tree_nodes import GroupsTree
from .filters import ObjectFilter, get_current_filter_params, get_fields_for_filter, TaskFilter
from .forms import CKEditorEditForm, CKEditorCreateForm, CKEditorEditObjForm
from .models import Object, Task, Engineer
from .services.tree_nodes.tree_nodes import AllTagsTree


@login_required
def get_home(request):
    page_number = request.GET.get("page", 1)
    per_page = request.GET.get("per_page", 8)
    filter_params = urlencode({key: value for key, value in request.GET.items() if key not in ["page", "per_page"]})

    objects = get_objects(request, filter_params, page_number, per_page)

    filter_fields_items = get_fields_for_filter(request.user, "objects")

    current_filter_params = get_current_filter_params(request, "objects")

    obj_filter = ObjectFilter(request.GET)

    context = {**objects,
               **current_filter_params,
               **filter_fields_items,
               "filter_data": obj_filter.filter_url,  # для сохранения фильтров при пагинации
               "params_count": obj_filter.applied_filters_count,
               }
    return render(request, "components/home/home.html", context=context)





@login_required
def get_object_page(request, object_slug):
    page_number = request.GET.get("page", 1)
    per_page = request.GET.get("per_page", 8)
    filter_params = urlencode({key: value for key, value in request.GET.items() if key not in ["page", "per_page", ]})

    obj = get_single_object(request.user, object_slug)
    child_objects = get_child_objects(user=request.user, parent=obj["object"])

    tasks = get_tasks(request, filter_params, page_number, per_page, obj=obj["object"])
    # filtered_task = get_filtered_tasks(request, obj=obj["object"])
    # pagination_data = paginate_queryset(filtered_task.tasks, page_number, per_page)

    ckeditor = CKEditorCreateForm(request.POST)
    context = {
        **obj,
        **tasks,
        # "tasks": pagination_data["page_obj"],
        # "pagination_data": pagination_data,
        # "task_count": filtered_task.tasks_counters,
        # "filter_params": filtered_task.filter_params,
        "child_objects": child_objects,
        "ckeditor": ckeditor,
    }

    return render(request, "components/object/object-page.html", context=context)


@login_required
def get_tasks_page(request):
    page_number = request.GET.get("page", 1)
    per_page = request.GET.get("per_page", 8)
    filter_params = urlencode({key: value for key, value in request.GET.items() if key not in ["page", "per_page", ]})

    tasks = get_tasks(request, filter_params, page_number, per_page)

    fields = get_fields_for_filter(user=request.user, page="tasks")
    current_filter_params = get_current_filter_params(request=request, page="tasks")

    task_filter = TaskFilter(request.GET)
    ckeditor = CKEditorCreateForm(request.POST)

    context = {
        **tasks,
        **fields,
        "current_filter_params": current_filter_params,  # для TreeSelect
        "filter_data": task_filter.filter_url,  # для сохранения фильтров при пагинации
        "params_count": task_filter.applied_filters_count,
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
def get_calendar_page(request):
    page_number = request.GET.get("page", 1)
    per_page = request.GET.get("per_page", 1000)
    filter_params = urlencode({key: value for key, value in request.GET.items() if key not in ["page", "per_page", ]})

    tasks = get_tasks(request, filter_params, page_number, per_page)
    fields = get_fields_for_filter(user=request.user, page="tasks")
    current_filter_params = get_current_filter_params(request=request, page="tasks")
    task_filter = TaskFilter(request.GET)

    context = {
        **tasks,
        **fields,
        "current_filter_params": current_filter_params,  # для TreeSelect
        "params_count": task_filter.applied_filters_count,
    }

    return render(request, "components/calendar/calendar.html", context=context)


@login_required
def get_task_edit_form(request, task_id: int):
    task = get_object_or_404(Task, pk=task_id)
    fields = get_fields_for_filter(request.user, "tasks")
    print(fields)
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

        'engineer_stats': engineer_stats,
    }

    return render(request, 'stat_page.html', context)
