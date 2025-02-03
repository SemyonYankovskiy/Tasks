import re
from typing import List

from bs4 import BeautifulSoup

from ..models import Task


class TasksPrinter:

    def __init__(self):
        self.tasks = []

    def add_tasks(self, tasks: List[Task]):
        for task in tasks:
            # Получаем значения M2M полей
            engineers = ", ".join([str(engineer) for engineer in task.engineers.all()])
            departments = ", ".join([str(department) for department in task.departments.all()])
            tags = ", ".join([str(tag) for tag in task.tags.all()])

            # Используем BeautifulSoup для извлечения текста из HTML
            soup = BeautifulSoup(task.text, "html.parser")
            text = soup.get_text()

            # Регулярное выражение для удаления изображений, если нужно
            pattern = r'!.*?.*?'  # Находит все строки в формате ![...](...)
            cleaned_text = re.sub(pattern, "", text)

            # Убираем лишние пробелы
            clean_text = re.sub(r'\s+', ' ', cleaned_text).strip()

            # Формируем строку для вывода
            task_info = (
                f"ID: {task.id}\n"
                f"Создатель: {task.creator}\n"
                f"Дата создания: {task.create_time}\n"
                f"Важность: {task.priority}\n"
                f"Название задачи: {task.header}\n"
                f"Описание: {clean_text}\n"
                f"Задача завершена?: {task.is_done}\n"
                f"Дата завершения: {task.completion_time}\n"
                f"Текст завершения: {task.completion_text}\n"
                f"Инженеры: {engineers}\n"
                f"Отделы: {departments}\n"
                f"Теги: {tags}\n"
                "-" * 40  # Разделитель между задачами
            )
            self.tasks.append(task_info)

    def print_tasks(self):
        for task_info in self.tasks:
            print(task_info)

