import datetime
from dataclasses import dataclass
from zoneinfo import ZoneInfo

from django.core.cache import cache
from django.db.models import Q, Count, Case, When, QuerySet

from tasks.filters import TaskFilter, TaskFilterByDone
from tasks.models import Task, Engineer
from tasks.services.cache_version import CacheVersion
from tasks.services.service import paginate_queryset
from user.models import User


def permission_filter(user: User) -> QuerySet[Task]:
    engineer: Engineer | None = user.get_engineer_or_none()

    # Если пользователь администратор, он видит все задачи
    if user.is_superuser:
        queryset = Task.objects.all()
        queryset |= Task.objects.filter(creator=user)
        return queryset.distinct()

    # Если пользователь head_of_department
    elif engineer and engineer.head_of_department:
        # Получаем всех пользователей, связанных с инженерами департамента
        department_users = User.objects.filter(engineer__department=engineer.department)

        # Пользователь head_of_department видит задачи, связанные с его департаментом, подчиненными и задачи,
        # которые подчиненные создали для других департаментов
        queryset = Task.objects.filter(
            Q(departments=engineer.department)  # Задачи департамента
            | Q(engineers__department=engineer.department)  # Задачи всех в департаменте
            | Q(creator__in=department_users)  # Задачи, созданные подчиненными
        )
        queryset |= Task.objects.filter(creator=user)
        return queryset.distinct()

    # Если пользователь не администратор и не head_of_department
    elif engineer:
        if engineer.department:
            # Пользователь видит только свои задачи и задачи департамента
            queryset = Task.objects.filter(Q(engineers=engineer) | Q(departments=engineer.department))
            queryset |= Task.objects.filter(creator=user)
            return queryset.distinct()
        else:
            # Если у пользователя нет департамента, он видит только свои задачи
            queryset = Task.objects.filter(engineers=engineer)
            queryset |= Task.objects.filter(creator=user)
            return queryset.distinct()

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
    my_tasks_count: int
    available_tasks_count: int


@dataclass
class FilterParams:
    show_my_tasks_only: bool
    sort_order: str
    show_active_task: bool
    show_done_task: bool


@dataclass
class FilteredTasksResult:
    tasks: QuerySet[Task]
    # tasks_id_list: list
    tasks_counters: TasksCounter
    filter_params: FilterParams
    tasks_filter_by_done: TaskFilterByDone


def get_tasks_count(queryset: QuerySet[Task], engineer: Engineer, available_queryset: QuerySet[Task]) -> TasksCounter:
    # Счётчик всех задач
    all_tasks_status = queryset.aggregate(
        done_tasks_count=Count(Case(When(is_done=True, then=1))),
        not_done_count=Count(Case(When(is_done=False, then=1))),
    )

    # Счётчик задач, созданных текущим пользователем
    my_tasks_status = queryset.filter(engineers=engineer).aggregate(
        my_done_tasks_count=Count(Case(When(is_done=True, then=1))),
        my_not_done_count=Count(Case(When(is_done=False, then=1))),
    )

    # Подсчет задач со сроком выполнения сегодня для всех задач и только моих
    tasks_due_today_count = queryset.filter(
        completion_time__date=datetime.datetime.now().date(), is_done=False
    ).count()

    # Счётчик доступных задач (включает задачи департамента, подчинённых и прочие)
    available_tasks_count = available_queryset.count()

    return TasksCounter(
        done_count=all_tasks_status["done_tasks_count"],
        not_done_count=all_tasks_status["not_done_count"],
        tasks_due_today_count=tasks_due_today_count,
        my_tasks_count=my_tasks_status["my_done_tasks_count"] + my_tasks_status["my_not_done_count"],
        available_tasks_count=available_tasks_count
    )


def get_filtered_tasks(request, obj=None):
    """
    Возвращает часть задач, которые отфильтрованы или включены/выключены в шаблоне
    """
    tasks_qs = permission_filter(user=request.user)
    tasks_qs_old = tasks_qs
    tasks_qs = tasks_qs.prefetch_related("files", "tags", "engineers", "objects_set", "departments", "creator")

    tasks_filter = TaskFilter(request.GET, queryset=tasks_qs, request=request)

    tasks_qs = tasks_filter.qs

    if obj:
        tasks_qs = tasks_qs.filter(objects_set=obj)

    tasks_counters = get_tasks_count(queryset=tasks_qs, available_queryset=tasks_qs_old, engineer=request.user.get_engineer_or_none())

    tasks_filter_by_done = TaskFilterByDone(request.GET, queryset=tasks_qs, request=request)

    tasks_qs = tasks_filter_by_done.qs

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


def get_tasks(request, filter_params, page_number, per_page, obj=None):
    """
    Возвращает список объектов. Если не применяются фильтры - возвращает объекты из кэша
    """
    if obj:
        cache_key = f'{obj.slug}_tasks_page:{page_number}:{request.user}'
    else:
        cache_key = f'tasks_page:{page_number}:{request.user}'

    version_cache_key = "tasks_page_version_cache"
    cache_version = CacheVersion(version_cache_key)
    cache_version_value = cache_version.get_cache_version()

    cached_data = cache.get(cache_key, version=cache_version_value) if not filter_params else None

    if cached_data:
        return cached_data

    filtered_task = get_filtered_tasks(request, obj=obj)
    pagination_data = paginate_queryset(filtered_task.tasks, page_number, per_page)

    # Задаём московский часовой пояс
    moscow_tz = ZoneInfo("Europe/Moscow")
    for task in pagination_data["page_obj"]:
        if task.completion_time:
            completion_time_moscow = task.completion_time.astimezone(moscow_tz)
            now_moscow = datetime.datetime.now(moscow_tz)

            # Вычисляем оставшееся время
            time_left = completion_time_moscow - now_moscow

            # Переводим время в часы и преобразуем к int
            hours_left = int(time_left.total_seconds() // 3600) if time_left.total_seconds() > 0 else 0
            task.time_left = hours_left
            task.time_now = now_moscow

        else:
            task.time_left = 0  # Если дедлайн не задан

    result = {
        "tasks": pagination_data["page_obj"],
        "pagination_data": pagination_data,
        "task_count": filtered_task.tasks_counters,
        "filter_params": filtered_task.filter_params,
    }

    # Кэшируем результат, если отсутствуют фильтры
    if not filter_params:
        cache.set(cache_key, result, timeout=600, version=cache_version_value)

    return result



