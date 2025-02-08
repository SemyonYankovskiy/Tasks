from django.core.cache import cache

from tasks.models import Task


def get_stat():
    cache_key = f"stat"
    cached_data = cache.get(cache_key)
    if cached_data:
        return cached_data

    # Выбираем все задачи, которые не удалены
    tasks = Task.objects.filter(deleted=False)

    # Агрегируем данные по задачам для инженеров и отделов
    engineer_stats = {}
    department_stats = {}

    for task in tasks:
        # Считаем задачу для каждого инженера, связанного с задачей
        for engineer in task.engineers.all():
            if engineer.id not in engineer_stats:
                engineer_stats[engineer.id] = {
                    'first_name': engineer.first_name,
                    'second_name': engineer.second_name,
                    'department': engineer.department.name if engineer.department else 'Нет департамента',
                    'active_tasks_count': 0,
                    'completed_tasks_count': 0,
                }
            if task.is_done:
                engineer_stats[engineer.id]['completed_tasks_count'] += 1
            else:
                engineer_stats[engineer.id]['active_tasks_count'] += 1

        # Считаем задачу для каждого отдела, связанного с задачей
        for department in task.departments.all():
            if department.id not in department_stats:
                department_stats[department.id] = {
                    'name': department.name,
                    'active_tasks_count': 0,
                    'completed_tasks_count': 0,
                }
            if task.is_done:
                department_stats[department.id]['completed_tasks_count'] += 1
            else:
                department_stats[department.id]['active_tasks_count'] += 1

    # Преобразуем словари в списки для удобства вывода
    engineer_stats_list = list(engineer_stats.values())
    department_stats_list = list(department_stats.values())

    result = {
        'engineer_stats': engineer_stats_list,
        'department_stats': department_stats_list,
    }

    cache.set(cache_key, result, timeout=600)

    return result