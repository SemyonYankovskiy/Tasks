import random

from django.conf import settings


def get_random_icon(request):
    # Папка с иконками
    icon_directory = settings.BASE_DIR/ "static/self/img/lazy"

    # Получаем список файлов в папке
    icon_pull = list(icon_directory.rglob("*.png"))

    # Если файлы есть, выбираем случайную иконку
    icon = random.choice(icon_pull) if icon_pull else None

    # Формируем путь для шаблона
    icon_path = f"self/img/lazy/{icon}" if icon else None

    return {"header_icon": icon_path}


def get_current_page(request):
    return {"current_page": request.path, "objects_page": request.path.startswith("/object/")}
