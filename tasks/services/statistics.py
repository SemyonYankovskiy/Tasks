from django.core.cache import cache
from django.db.models import Count, Q

from tasks.models import Engineer


def get_stat():
    cache_key = f"stat"
    cached_data = cache.get(cache_key)
    if cached_data:
        return cached_data

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

    result = {'engineer_stats': engineer_stats,}

    cache.set(cache_key, result, timeout=600)

    return result
