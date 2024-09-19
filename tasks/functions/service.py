import json
import os
import random

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator


from djangoProject import settings
from tasks.models import Task


@login_required
def get_random_icon(request):
    # Папка с иконками
    icon_directory = os.path.join(settings.BASE_DIR, 'static/img/lazy')

    # Получаем список файлов в папке
    icon_pull = os.listdir(icon_directory)

    # Если файлы есть, выбираем случайную иконку
    icon = random.choice(icon_pull) if icon_pull else None

    # Формируем путь для шаблона
    icon_path = f'img/lazy/{icon}' if icon else None

    return icon_path


def remove_unused_task_attached_files(file_uploader_data: str, task: Task, *, delete_orphan_files: bool = False):
    """Удаляет прикрепленные к задачам файлы, которые не используются"""

    try:
        # Получаем список ОСТАВШИХСЯ прикрепленных файлов из json строчки.
        # Строка имеет формат:
        # '[{"file":"/media/uploads/2024/9/11/file1.png"},{"file":"/media/uploads/2024/9/11/file2.png"}]'
        not_deleted_files: list | None = json.loads(file_uploader_data)
    except json.JSONDecodeError:
        # Если не удалось распарсить json строку, то указываем None,
        # чтобы не удалить случайно все файлы.
        not_deleted_files = None

    if not_deleted_files is not None:
        # Если удалось распарсить json строку, то проверяем какие файлы есть в этом списке.

        # Создаем список URL адресов файлов, которые должны ОСТАТЬСЯ у этой задачи.
        files_urls = [f["file"] for f in not_deleted_files]
        for db_file in task.files.all():  # Смотрим уже имеющиеся файлы у задачи.
            # Если файла нет в списке оставшихся, то его нужно открепить от этой задачи.
            if db_file.file.url not in files_urls:
                task.files.remove(db_file)  # Удаляем связь задачи и файла.

                # Если нужно удалять файлы, то удаляем их.
                if delete_orphan_files:
                    db_file.file.delete()
                    db_file.delete()


def paginate_queryset(queryset, page_number, per_page):
    """
    Создаёт объект пагинации, внутри которого в переменной page_obj данные для пагинации.
    Описывает параметры пагинатора для корректного отображения кнопок управления

    """
    # Создаем объект пагинации
    paginator = Paginator(queryset, per_page)
    page_obj = paginator.get_page(page_number)

    # Определяем общее количество страниц и текущую страницу
    total_pages = paginator.num_pages
    current_page = page_obj.number

    # Флаги для отображения многоточий и ссылок на крайние страницы
    end_show_ellipsis = current_page < total_pages - 3
    end_show_last_page_link = current_page <= total_pages - 3
    start_show_ellipsis = current_page > 4
    start_show_first_page_link = current_page >= 4

    # Возвращаем объект страницы и параметры для отображения пагинации
    return {
        "page_obj": page_obj,
        "end_show_ellipsis": end_show_ellipsis,
        "end_show_last_page_link": end_show_last_page_link,
        "start_show_ellipsis": start_show_ellipsis,
        "start_show_first_page_link": start_show_first_page_link,
        "last_page_number": total_pages,
        "per_page": per_page
    }