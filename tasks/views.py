from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from tasks.services.objects import get_objects, get_single_object, get_child_objects
from tasks.services.tasks_prepare import get_tasks
from tasks.services.tree_nodes import GroupsTree
from .filters import ObjectFilter, get_current_filter_params, get_fields_for_filter, TaskFilter, filter_url, \
    applied_filters_count
from .forms import CKEditorEditForm, CKEditorCreateForm, CKEditorEditObjForm, CKEditorCreateObjForm, CKEditorAnswerForm
from .models import Object, Task
from .services.statistics import get_stat
from .services.tree_nodes.tree_nodes import AllTagsTree


@login_required
def get_home(request):
    page_number = request.GET.get("page", 1)
    per_page = request.GET.get("per_page", 8)
    filter_params = urlencode({key: value for key, value in request.GET.items() if key not in ["page"]})

    objects = get_objects(request, filter_params, page_number, per_page)

    filter_fields_items = get_fields_for_filter(request.user, "objects")

    current_filter_params = get_current_filter_params(request, "objects")

    obj_filter = ObjectFilter(request.GET)

    ckeditor__obj_form = CKEditorCreateObjForm()

    context = {**objects,
               **current_filter_params,
               **filter_fields_items,
               "ckeditor__obj_form": ckeditor__obj_form,
               "filter_data": filter_url(request),  # для сохранения фильтров при пагинации
               "params_count": applied_filters_count(request),
               }
    return render(request, "components/home/home.html", context=context)


@login_required
def get_object_page(request, object_slug):
    page_number = request.GET.get("page", 1)
    per_page = request.GET.get("per_page", 8)

    filter_params = urlencode({key: value for key, value in request.GET.items() if key not in ["page"]})

    obj = get_single_object(request.user, object_slug)  # Получаем объект
    child_objects = get_child_objects(user=request.user, parent=obj["object"])

    tasks = get_tasks(request, filter_params, page_number, per_page, obj=obj["object"])

    fields = get_fields_for_filter(user=request.user, page="tasks")
    ckeditor = CKEditorCreateForm(request.POST)

    context = {
        **obj,
        **tasks,
        **fields,
        "child_objects": child_objects,
        "ckeditor": ckeditor,
        "filter_data": filter_url(request, obj=obj["object"]),  # Передаем объект в filter_url
    }

    return render(request, "components/object/object-page.html", context=context)


@login_required
def get_tasks_page(request):
    page_number = request.GET.get("page", 1)
    per_page = request.GET.get("per_page", 8)
    obj_id = request.GET.get("object_id")  # Получаем объект из запроса, если есть
    obj = None

    if obj_id:
        obj = get_object_or_404(Object, id=obj_id)  # Получаем объект по ID

    filter_params = urlencode({key: value for key, value in request.GET.items() if key not in ["page"]})

    tasks = get_tasks(request, filter_params, page_number, per_page, obj=obj)

    fields = get_fields_for_filter(user=request.user, page="tasks")
    current_filter_params = get_current_filter_params(request=request, page="tasks")

    task_filter = TaskFilter(request.GET)
    ckeditor = CKEditorCreateForm(request.POST)

    context = {
        **tasks,
        **fields,
        **current_filter_params,
        "filter_data": filter_url(request, obj=obj),  # Передаем объект в filter_url
        "params_count": task_filter.applied_filters_count_taks,
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
    filter_params = urlencode({key: value for key, value in request.GET.items() if key not in ["page"]})

    tasks = get_tasks(request, filter_params, page_number, per_page)
    fields = get_fields_for_filter(user=request.user, page="tasks")
    current_filter_params = get_current_filter_params(request=request, page="tasks")
    task_filter = TaskFilter(request.GET)

    context = {
        **tasks,
        **fields,
        "current_filter_params": current_filter_params,  # для TreeSelect
        "params_count": task_filter.applied_filters_count_taks,
    }

    return render(request, "components/calendar/calendar.html", context=context)


@login_required
def get_task_edit_form(request, task_id: int):
    task = get_object_or_404(Task, pk=task_id)
    fields = get_fields_for_filter(request.user, "tasks")
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
    elif action_type == 'delete':
        action_url = reverse('delete_task', args=[task_id])
        form_action = 'delete'
    else:
        action_url = reverse('reopen_task', args=[task_id])
        form_action = 'reopen'

    context = {
        'task_id': task_id,
        'form_action': form_action,
        'action_url': action_url,
        'from_url': request.GET.get('from_url', ''),
    }

    return render(request, 'components/task/action_task_form.html', context)


@login_required
def get_task_comment_form(request, task_id):
    ckeditor_answer = CKEditorAnswerForm(request.POST)
    context = {
        'task_id': task_id,
        'action_url': reverse('reopen_task', args=[task_id]),
        'from_url': request.GET.get('from_url', ''),
        "ckeditor_answer": ckeditor_answer,
    }

    return render(request, 'components/task/comment_task_form.html', context)


@login_required
def get_stat_page(request):
    stat = get_stat()
    context = {**stat}
    return render(request, 'stat_page.html', context)
