import datetime
from dataclasses import dataclass
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from django.db.models import Q, Count, Case, When, QuerySet

from tasks.filters import TaskFilter, TaskFilterByDone
from tasks.functions.service import default_date
from tasks.models import Task, Engineer
from tasks.services.tree_nodes import TasksTagsTree, ObjectsTree, EngineersTree
from user.models import User


def permission_filter(user: User) -> QuerySet[Task]:
    engineer: Engineer | None = user.get_engineer_or_none()
    # Если пользователь администратор, он видит все задачи
    if user.is_superuser:
        queryset = Task.objects.all()

    # Если пользователь head_of_department
    elif engineer and engineer.head_of_department:
        # Пользователь head_of_department видит задачи, связанные с инженерами его департамента, включая подчиненных
        queryset = Task.objects.filter(
            Q(departments=engineer.department)  # Задачи департамента
            | Q(engineers__department=engineer.department)  # Задачи всех в департаменте
        )

    # Если пользователь не администратор и не head_of_department
    elif engineer:
        if engineer.department:
            # Пользователь видит только свои задачи и задачи департамента
            queryset = Task.objects.filter(Q(engineers=engineer) | Q(departments=engineer.department))
        else:
            # Если у пользователя нет департамента, он видит только свои задачи
            queryset = Task.objects.filter(engineers=engineer)

    # Если нет инженера
    else:
        queryset = Task.objects.none()

    queryset |= Task.objects.filter(creator=user)

    return queryset.distinct()


@dataclass
class TasksCounter:
    done_count: int
    not_done_count: int
    tasks_due_today_count: int


@dataclass
class FilterParams:
    show_my_tasks_only: bool
    sort_order: str
    show_active_task: bool
    show_done_task: bool


@dataclass
class FilteredTasksResult:
    tasks: QuerySet[Task]
    tasks_counters: TasksCounter
    filter_params: FilterParams
    tasks_filter_by_done: TaskFilterByDone


def get_tasks_count(queryset: QuerySet[Task]) -> TasksCounter:
    # Используем aggregate для подсчёта завершённых и незавершённых задач за один запрос
    tasks_status = queryset.aggregate(
        done_tasks_count=Count(Case(When(is_done=True, then=1))),
        not_done_count=Count(Case(When(is_done=False, then=1))),
    )

    tasks_due_today_count = queryset.filter(
        completion_time__date=datetime.datetime.now(), is_done=False
    ).count()

    return TasksCounter(
        done_count=tasks_status["done_tasks_count"],
        not_done_count=tasks_status["not_done_count"],
        tasks_due_today_count=tasks_due_today_count,
    )


def get_filtered_tasks(request, obj=None):
    """
    Возвращает часть задач, которые отфильтрованы или включены/выключены в шаблоне
    """
    tasks_qs = permission_filter(user=request.user)

    tasks_qs = tasks_qs.prefetch_related("files", "tags", "engineers", "objects_set", "departments", "creator")

    tasks_filter = TaskFilter(request.GET, queryset=tasks_qs, request=request)

    tasks_qs = tasks_filter.qs

    if obj:
        tasks_qs = tasks_qs.filter(objects_set=obj)

    tasks_counters = get_tasks_count(tasks_qs)

    tasks_filter_by_done = TaskFilterByDone(request.GET, queryset=tasks_qs, request=request)

    tasks_qs = tasks_filter_by_done.qs

    # Задаём московский часовой пояс
    moscow_tz = ZoneInfo("Europe/Moscow")

    for task in tasks_qs:
        if task.completion_time:
            completion_time_moscow = task.completion_time.astimezone(moscow_tz)
            now_moscow = datetime.datetime.now(moscow_tz)

            # Вычисляем оставшееся время
            time_left = completion_time_moscow - now_moscow

            # Переводим время в часы и преобразуем к int
            hours_left = int(time_left.total_seconds() // 3600) if time_left.total_seconds() > 0 else 0
            task.time_left = hours_left

        else:
            task.time_left = 0  # Если дедлайн не задан

    # Возвращаем контекст с отфильтрованными задачами и параметрами отображения
    return FilteredTasksResult(
        tasks=tasks_qs,
        tasks_counters=tasks_counters,
        filter_params=FilterParams(
            show_my_tasks_only=tasks_filter.data.get("show_my_tasks_only"),
            sort_order=tasks_filter.data.get("sort_order"),
            show_active_task=tasks_filter_by_done.data.get("show_active_task"),
            show_done_task=tasks_filter_by_done.data.get("show_done_task"),
        ),
        tasks_filter_by_done=tasks_filter_by_done,
    )


def get_m2m_fields_for_tasks(user):
    """
    Возвращает поля m2m задач, для отображения в фильтре задач
    """
    context = {"user": user}

    tasks_tags_tree = TasksTagsTree(context).get_nodes()
    objects_tree = ObjectsTree(context).get_nodes()
    engineers_tree = EngineersTree(context).get_nodes()

    # Возвращаем данные для использования в фильтрах
    return {
        "tags_json": tasks_tags_tree,
        "engineers_json": engineers_tree,
        "objects_json": objects_tree,
    }


def task_filter_params(request):
    """
    Возвращает текущие параметры фильтра, количество примененных фильтров,
    поля m2m, строку с параметрами фильтра для сохранения состояния фильтра
    """

    # Параметры, которые не нужно учитывать при подсчёте количества активных фильтров
    not_count_params = [
        "show_my_tasks_only",
        "sort_order",
        "page",
        "show_active_task",
        "show_done_task",
        "per_page",
    ]

    # Параметры, которые исключаются из URL
    exclude_params = ["page", "per_page"]
    filter_data = {key: value for key, value in request.GET.items() if key not in exclude_params}

    # Формируем строку с параметрами фильтра для последующего использования в шаблонах
    filter_url = urlencode(filter_data, doseq=True) + "#tasks"

    # Логика подсчёта активных фильтров
    applied_params = [param for key, param in request.GET.items() if param and key not in not_count_params]

    # Количество примененных фильтров
    params_count = len(applied_params)

    # Проверяем наличие completion_time_after и completion_time_before и учитываем их как один фильтр
    if request.GET.get("completion_time_after") and request.GET.get("completion_time_before"):
        params_count -= 1

    return {
        **get_m2m_fields_for_tasks(request.user),
        "current_tags": request.GET.getlist("tags"),
        "current_engineers": request.GET.getlist("engineers"),
        "current_objects": request.GET.getlist("objects_set"),
        "filter_data": filter_url,
        "params_count": params_count,
        "default_date": default_date(),
        "default_time": "17:30",
    }
