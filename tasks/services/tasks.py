from urllib.parse import urlencode

from django.db.models import Q

from tasks.filters import TaskFilter
from tasks.models import Engineer, Task, Tag
from tasks.services.objects import get_objects_tree


def get_filtered_tasks(request, obj=None):
    show_my_tasks_only = request.GET.get("show_my_tasks_only") == "true"
    sort_order = request.GET.get("sort_order", "desc")  # По умолчанию сортировка по убыванию
    if request.path.startswith("/calendar/"):
        show_active_task = request.GET.get("show_active_task", "true") == "true"
        show_done_task = request.GET.get("show_done_task", "true") == "true"
    else:
        show_active_task = request.GET.get("show_active_task", "true") == "true"
        show_done_task = request.GET.get("show_done_task", "false") == "true"

    try:
        engineer = Engineer.objects.get(user=request.user)
    except Engineer.DoesNotExist:
        engineer = None



    basic_qs = Task.objects.all().filter(Q(objects_set__groups__users=request.user) | Q(engineers__user=request.user)).distinct()

    tasks = TaskFilter(request.GET, queryset=basic_qs).qs



    if show_my_tasks_only:
        if engineer:
            tasks = tasks.filter(engineers=engineer)
        else:
            tasks = tasks.none()


    # Если передан объект, фильтруем задачи по этому объекту
    if obj:
        tasks = tasks.filter(objects_set=obj)



    # Применение prefetch_related для оптимизации запросов
    tasks = tasks.prefetch_related("files", "tags", "engineers", "objects_set")

    # Сортировка по дате завершения: asc для возрастания, desc для убывания
    if sort_order == "asc":
        tasks = tasks.order_by("completion_time")
    else:
        tasks = tasks.order_by("-completion_time")

    done_tasks_count = tasks.filter(is_done=True).count()
    not_done_count = tasks.filter(is_done=False).count()


    if show_active_task and not show_done_task:
        tasks = tasks.filter(is_done=False)
    elif show_done_task and not show_active_task:
        tasks = tasks.filter(is_done=True)
    elif show_active_task and show_done_task:
        tasks = tasks  # Показываем и активные, и завершённые задачи
    else:
        tasks = tasks.none()  # Если оба фильтра выключены, ничего не показываем

    context = {
        "tasks": tasks,
        "show_active_task": show_active_task,
        "show_done_task": show_done_task,
        "done_count": done_tasks_count,
        "not_done_count": not_done_count,
        "show_my_tasks_only": show_my_tasks_only,
        "sort_order": sort_order,
    }
    return context


def task_filter_params(request):
    # Получаем теги, связанные с задачами
    tags_qs = Tag.objects.filter(tasks__isnull=False).values("id", "tag_name")
    tags = [{"id": tag["id"], "label": tag["tag_name"]} for tag in tags_qs]  # label обязателен

    # Получаем инженеров, связанных с задачами
    engineers_qs = list(Engineer.objects.all().values("id", "first_name", "second_name"))
    engineers = [{"id": eng["id"], "label": f"{eng['first_name']} {eng['second_name']}"} for eng in engineers_qs]

    objects_tree = get_objects_tree()
    not_count_params = ["show_my_tasks_only", "sort_order", "page", "show_active_task", "show_done_task"]
    exclude_params = ["page"]

    filter_data = {key: value for key, value in request.GET.items() if key not in exclude_params}

    # Формируем строку с параметрами фильтра
    filter_url = urlencode(filter_data, doseq=True) + "#tasks"
    return {
        "tags_json": tags,
        "current_tags": request.GET.getlist("tags"),
        "engineers_json": engineers,
        "current_engineers": request.GET.getlist("engineers"),
        "current_objects": request.GET.getlist("objects_set"),
        "objects_json": objects_tree,
        "filter_data": filter_url,
        "params_count": len([param for key, param in request.GET.items() if param and key not in not_count_params])
    }
