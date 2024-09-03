from tasks.models import Engineer, Task


def get_filtered_tasks(request, obj=None):
    user = request.user
    show_my_tasks_only = request.GET.get("show_my_tasks_only") == "true"
    sort_order = request.GET.get("sort_order", "desc")  # По умолчанию сортировка по убыванию

    try:
        engineer = Engineer.objects.get(user=user)
    except Engineer.DoesNotExist:
        engineer = None

    if show_my_tasks_only:
        if engineer:
            tasks = Task.objects.filter(engineers=engineer)
        else:
            tasks = Task.objects.none()
    else:
        tasks = Task.objects.all()

    # Если передан объект, фильтруем задачи по этому объекту
    if obj:
        tasks = tasks.filter(objects_set=obj)

    # Применение prefetch_related для оптимизации запросов
    tasks = tasks.prefetch_related("files", "tags", "engineers")

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
