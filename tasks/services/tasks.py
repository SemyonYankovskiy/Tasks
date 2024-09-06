from tasks.filters import TaskFilter
from tasks.models import Engineer, Task


def get_filtered_tasks(request, obj=None):
    show_my_tasks_only = request.GET.get("show_my_tasks_only") == "true"
    sort_order = request.GET.get("sort_order", "desc")  # По умолчанию сортировка по убыванию

    try:
        engineer = Engineer.objects.get(user=request.user)
    except Engineer.DoesNotExist:
        engineer = None

    tasks = TaskFilter(request.GET, queryset=Task.objects.all()).qs

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

    context = {
        "tasks": tasks,
        "done_count": done_tasks_count,
        "not_done_count": not_done_count,
        "show_my_tasks_only": show_my_tasks_only,
        "sort_order": sort_order,
    }
    return context
