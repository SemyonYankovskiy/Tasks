import datetime
from urllib.parse import urlencode

from django.db.models import Q, Count, Case, When

from tasks.filters import TaskFilter
from tasks.functions.objects import get_objects_tree, get_engineers_tree
from tasks.models import Task, Tag, Engineer


def get_department_tasks(department):
    """
    Функция для получения всех задач, связанных с инженерами из определённого департамента.
    """
    # Находим всех инженеров департамента
    department_engineers = Engineer.objects.filter(departament=department)

    # Собираем все задачи, связанные с этими инженерами
    department_tasks = Task.objects.filter(engineers__in=department_engineers).distinct()

    return department_tasks


def permission_filter(request, engineer):
    # Если пользователь администратор, он видит все задачи
    if request.user.is_superuser:
        basic_qs = Task.objects.all().distinct()

    # Если пользователь is_staff
    elif request.user.is_staff:
        if engineer and engineer.departament:
            # Находим все задачи департамента и задачи самого пользователя
            department_tasks = get_department_tasks(engineer.departament)

            # Пользователь is_staff видит задачи, связанные с инженерами его департамента, включая подчиненных
            basic_qs = Task.objects.filter(
                Q(departments=engineer.departament) |  # Задачи департамента
                Q(engineers=engineer)  # Задачи самого пользователя-инженера
            ).distinct()

            # Объединение на уровне Python
            # Так как union не поддерживает prefetch_related(), объединим запросы на уровне Python
            basic_qs = basic_qs | department_tasks.distinct()

        else:
            # Если нет департамента, видит только свои задачи
            basic_qs = Task.objects.filter(
                Q(engineers=engineer)
            ).distinct()

    # Если пользователь не администратор и не is_staff
    else:
        if engineer and engineer.departament:
            # Пользователь видит только свои задачи и задачи департамента
            basic_qs = Task.objects.filter(
                Q(engineers=engineer) | Q(departments=engineer.departament)
            ).distinct()
        else:
            # Если у пользователя нет департамента, он видит только свои задачи
            basic_qs = Task.objects.filter(
                Q(engineers=engineer)
            ).distinct()

    return basic_qs




def get_filtered_tasks(request, obj=None):
    """
    Возвращает часть задач, которые отфильтрованы или включены/выключены в шаблоне
    """
    # Определяем, показывать ли только мои задачи и порядок сортировки
    show_my_tasks_only = request.GET.get("show_my_tasks_only") == "true"
    sort_order = request.GET.get("sort_order", "desc")  # По умолчанию сортировка по убыванию

    show_active_task = request.GET.get("show_active_task", "true") == "true"
    show_done_task = request.GET.get("show_done_task", "false") == "true"

    # Получаем объект Engineer, связанный с текущим пользователем
    try:
        engineer = Engineer.objects.select_related("departament").get(user=request.user)
    except Engineer.DoesNotExist:
        engineer = None

    basic_qs = permission_filter(request=request, engineer=engineer)

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
    tasks = tasks.prefetch_related("files", "tags", "engineers", "objects_set", "departments")

    # Применяем сортировку по дате завершения
    if sort_order == "asc":
        tasks = tasks.order_by("completion_time")
    else:
        tasks = tasks.order_by("-completion_time")

    # Используем aggregate для подсчёта завершённых и незавершённых задач за один запрос
    tasks_status = tasks.aggregate(
        done_tasks_count=Count(Case(When(is_done=True, then=1))),
        not_done_count=Count(Case(When(is_done=False, then=1)))
    )

    # Извлекаем значения из результата
    done_tasks_count = tasks_status['done_tasks_count']
    not_done_count = tasks_status['not_done_count']

    # Фильтруем задачи в зависимости от того, какие категории нужно показывать
    if show_active_task and not show_done_task:
        tasks = tasks.filter(is_done=False)
    elif show_done_task and not show_active_task:
        tasks = tasks.filter(is_done=True)
    elif show_active_task and show_done_task:
        tasks = tasks  # Показываем и активные, и завершённые задачи
    else:
        tasks = tasks.none()  # Если оба фильтра отключены, не показываем задачи

    # Находим количество задач, которые нужно выполнить сегодня
    today = datetime.date.today()
    tasks_due_today_count = tasks.filter(completion_time__date=today).count()

    # Возвращаем контекст с отфильтрованными задачами и параметрами отображения
    context = {
        "tasks": tasks,
        "show_active_task": show_active_task,
        "show_done_task": show_done_task,
        "done_count": done_tasks_count,
        "not_done_count": not_done_count,
        "show_my_tasks_only": show_my_tasks_only,
        "sort_order": sort_order,
        "tasks_due_today_count": tasks_due_today_count,
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
    поля m2m, строку с параметрами фильтра для сохранения состояния фильтра
    """

    # Параметры, которые не нужно учитывать при подсчёте количества активных фильтров
    not_count_params = ["show_my_tasks_only", "sort_order", "page", "show_active_task", "show_done_task", "per_page"]

    # Параметры, которые исключаются из URL
    exclude_params = ["page", "per_page"]
    filter_data = {key: value for key, value in request.GET.items() if key not in exclude_params}

    # Формируем строку с параметрами фильтра для последующего использования в шаблонах
    filter_url = urlencode(filter_data, doseq=True) + "#tasks"

    # Логика подсчёта активных фильтров
    applied_params = [
        param for key, param in request.GET.items()
        if param and key not in not_count_params
    ]

    # Проверяем наличие completion_time_after и completion_time_before и учитываем их как один фильтр
    completion_time_after = request.GET.get("completion_time_after")
    completion_time_before = request.GET.get("completion_time_before")

    if completion_time_after and completion_time_before:
        # Если оба параметра существуют, исключаем их из подсчёта по отдельности
        applied_params = [
            param for key, param in request.GET.items()
            if key not in ["completion_time_after", "completion_time_before"]
               and param and key not in not_count_params
        ]
        applied_params.append("completion_time_range")  # Добавляем как один фильтр

    # Количество примененных фильтров
    params_count = len(applied_params)

    return {
        **get_m2m_fields_for_tasks(),
        "current_tags": request.GET.getlist("tags"),
        "current_engineers": request.GET.getlist("engineers"),
        "current_objects": request.GET.getlist("objects_set"),
        "filter_data": filter_url,
        "params_count": params_count
    }
