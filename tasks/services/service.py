import datetime
import json

from django.core.paginator import Paginator


def remove_unused_attached_files(file_uploader_data: str, qs_object, *, delete_orphan_files: bool = False):
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
        for db_file in qs_object.files.all():  # Смотрим уже имеющиеся файлы у задачи.
            # Если файла нет в списке оставшихся, то его нужно открепить от этой задачи.
            if db_file.file.url not in files_urls:
                qs_object.files.remove(db_file)  # Удаляем связь задачи и файла.

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
        "paginator": paginator,
        "page_obj": page_obj,
        "end_show_ellipsis": end_show_ellipsis,
        "end_show_last_page_link": end_show_last_page_link,
        "start_show_ellipsis": start_show_ellipsis,
        "start_show_first_page_link": start_show_first_page_link,
        "last_page_number": total_pages,
        "per_page": per_page,
    }


def pagination_homepage():

    pass


def default_date():
    # Получаем текущее время
    now = datetime.datetime.now()

    # Определяем время 17:00 для сравнения
    cutoff_time = now.replace(hour=17, minute=0, second=0, microsecond=0)

    # Проверяем, текущее время больше 17:00 или нет
    if now > cutoff_time:
        # Если текущее время больше 17:00, устанавливаем следующий день
        date_today = now + datetime.timedelta(days=1)
    else:
        # Иначе устанавливаем сегодняшний день
        date_today = now

    # Оставляем только дату (без времени)
    return date_today.date().strftime("%Y-%m-%d")


def transliterate(text: str) -> str:
    """Транслитерация русского текста в латиницу."""
    cyrillic_to_latin = {
        'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd',
        'е': 'e', 'ё': 'yo', 'ж': 'zh', 'з': 'z', 'и': 'i',
        'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n',
        'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't',
        'у': 'u', 'ф': 'f', 'х': 'kh', 'ц': 'ts', 'ч': 'ch',
        'ш': 'sh', 'щ': 'shch', 'ъ': '', 'ы': 'y', 'ь': '',
        'э': 'e', 'ю': 'yu', 'я': 'ya',
        'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D',
        'Е': 'E', 'Ё': 'Yo', 'Ж': 'Zh', 'З': 'Z', 'И': 'I',
        'Й': 'Y', 'К': 'K', 'Л': 'L', 'М': 'M', 'Н': 'N',
        'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T',
        'У': 'U', 'Ф': 'F', 'Х': 'Kh', 'Ц': 'Ts', 'Ч': 'Ch',
        'Ш': 'Sh', 'Щ': 'Shch', 'Ъ': '', 'Ы': 'Y', 'Ь': '',
        'Э': 'E', 'Ю': 'Yu', 'Я': 'Ya'
    }
    return ''.join(cyrillic_to_latin.get(char, char) for char in text)