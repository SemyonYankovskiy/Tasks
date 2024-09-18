from urllib.parse import urlencode

from django.db.models import Q

from tasks.filters import TaskFilter
from tasks.functions.objects import get_objects_tree, get_engineers_tree
from tasks.models import Task, Tag, Engineer


def get_filtered_tasks(request, obj=None):
    """
    Возвращает часть задач, которые отфильтрованы или включены/выключены в шаблоне
    """
    # Определяем, показывать ли только мои задачи и порядок сортировки
    show_my_tasks_only = request.GET.get("show_my_tasks_only") == "true"
    sort_order = request.GET.get("sort_order", "desc")  # По умолчанию сортировка по убыванию

    show_active_task = request.GET.get("show_active_task", "true") == "true"
    show_done_task = request.GET.get("show_done_task", "false") == "true"

    # Получаем информацию об инженере, связанном с текущим пользователем
    try:
        engineer = Engineer.objects.get(user=request.user)
    except Engineer.DoesNotExist:
        engineer = None

    # Если пользователь администратор, получаем все задачи, иначе фильтруем по пользователю
    if request.user.is_superuser:
        # Администратор видит все задачи
        basic_qs = Task.objects.all().distinct()
    else:
        # Получаем объект Engineer, связанный с текущим пользователем
        try:
            engineer = Engineer.objects.get(user=request.user)
        except Engineer.DoesNotExist:
            engineer = None

        if engineer and engineer.departament:
            # Пользователь видит задачи, в которых он сам указан как инженер,
            # а также задачи, связанные с его департаментом
            basic_qs = Task.objects.filter(
                Q(engineers=engineer) | Q(departments=engineer.departament)
            ).distinct()
        else:
            # Если у пользователя нет департамента, он видит только свои задачи
            basic_qs = Task.objects.filter(
                Q(engineers=engineer)
            ).distinct()

    # Применяем фильтр задач на основе запроса
    tasks = TaskFilter(request.GET, queryset=basic_qs).qs

    # Если фильтр "только мои задачи" активен, фильтруем по текущему инженеру
    if show_my_tasks_only:
        if engineer:
            tasks = tasks.filter(engineers=engineer)
        else:
            tasks = tasks.none()

    # Фильтруем задачи по переданному объекту, если он есть
    if obj:
        tasks = tasks.filter(objects_set=obj)

    # Оптимизируем запросы с использованием prefetch_related
    tasks = tasks.prefetch_related("files", "tags", "engineers", "objects_set")

    # Применяем сортировку по дате завершения
    if sort_order == "asc":
        tasks = tasks.order_by("completion_time")
    else:
        tasks = tasks.order_by("-completion_time")

    # Считаем количество завершённых и незавершённых задач
    done_tasks_count = tasks.filter(is_done=True).count()
    not_done_count = tasks.filter(is_done=False).count()

    # Фильтруем задачи в зависимости от того, какие категории нужно показывать
    if show_active_task and not show_done_task:
        tasks = tasks.filter(is_done=False)
    elif show_done_task and not show_active_task:
        tasks = tasks.filter(is_done=True)
    elif show_active_task and show_done_task:
        tasks = tasks  # Показываем и активные, и завершённые задачи
    else:
        tasks = tasks.none()  # Если оба фильтра отключены, не показываем задачи

    # Возвращаем контекст с отфильтрованными задачами и параметрами отображения
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


def get_m2m_fields_for_tasks():
    """
    Возвращает поля m2m задач, для отображения в фильтре задач
    """
    # Получаем теги, связанные с задачами, и формируем список для отображения
    tags_qs = Tag.objects.filter(tasks__isnull=False).values("id", "tag_name").distinct()
    tags = [{"id": tag["id"], "label": tag["tag_name"]} for tag in tags_qs]  # Поле label обязательно

    # # Получаем инженеров, связанных с задачами, и формируем список для отображения
    # engineers_qs = list(Engineer.objects.all().values("id", "first_name", "second_name"))
    # engineers = [{"id": eng["id"], "label": f"{eng['first_name']} {eng['second_name']}"} for eng in engineers_qs]

    # Получаем дерево объектов
    objects_tree = get_objects_tree()
    engineers_tree = get_engineers_tree()

    # Возвращаем данные для использования в фильтрах
    return {
        "tags_json": tags,
        "engineers_json": engineers_tree,
        "objects_json": objects_tree,
    }


def task_filter_params(request):
    """
    Возвращает текущие параметры фильтра, количество примененных фильтров,
    поля m2mб строку с параметрами фильтра для сохранения состояния фильтра
    """

    # Параметры, которые не нужно учитывать при подсчёте количества активных фильтров
    not_count_params = ["show_my_tasks_only", "sort_order", "page", "show_active_task", "show_done_task", "per_page"]

    # Параметры, которые исключаются из URL
    exclude_params = ["page", "per_page"]
    filter_data = {key: value for key, value in request.GET.items() if key not in exclude_params}

    # Формируем строку с параметрами фильтра для последующего использования в шаблонах
    filter_url = urlencode(filter_data, doseq=True) + "#tasks"

    # current_engineers_with_type = request.GET.getlist("engineers")
    # current_engineers = []
    # for each in current_engineers_with_type:
    #     type_id = each.split("_")
    #     type = type_id[0]
    #     id = int(type_id[1])
    #     current_engineers.append(id)
    #
    # print(current_engineers_with_type)
    # print(current_engineers)
    #
    # Возвращаем фильтры и количество активных параметров
    return {
        **get_m2m_fields_for_tasks(),
        "current_tags": request.GET.getlist("tags"),
        "current_engineers": request.GET.getlist("engineers"),
        "current_objects": request.GET.getlist("objects_set"),
        "filter_data": filter_url,
        "params_count": len([param for key, param in request.GET.items() if param and key not in not_count_params])
    }
