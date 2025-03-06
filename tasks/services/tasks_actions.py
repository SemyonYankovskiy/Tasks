from datetime import datetime

from bs4 import BeautifulSoup
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.transaction import atomic
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.shortcuts import render
from django.urls import reverse
from django.utils.dateformat import format

from tasks.forms import AddTaskForm, EditTaskForm
from tasks.models import Task, AttachedFile, Engineer, Tag, Comment
from tasks.services.export import TasksExcelExport
from tasks.services.service import remove_unused_attached_files
from tasks.services.tasks_prepare import get_tasks


def auto_resize_pic(html_string):

    if html_string:
        # Парсинг строки
        soup = BeautifulSoup(html_string, 'html.parser')

        # Находим тег <img>
        img_tag = soup.find('img')
        if img_tag:
            # Если есть атрибут style
            if 'style' in img_tag.attrs:
                # Разбиваем стили на части
                styles = img_tag['style'].split(';')
                # Обрабатываем каждый стиль
                new_styles = []
                for style in styles:
                    if style.strip().startswith('width'):
                        # Заменяем ширину на 100%
                        new_styles.append('width:100%')
                    # Игнорируем height (удаляем его)
                # Обновляем атрибут style
                img_tag['style'] = '; '.join(new_styles).strip('; ')

            # Получаем измененную строку
            return str(soup)
        else:
            return html_string
    else:
        return ""


@atomic
def create_tags(request, tags_list):
    """
    Проверяет, существуют ли теги в базе данных, и создаёт новые теги, если они отсутствуют.
    """

    # Получаем данные о тегах из формы (может содержать как новые теги, так и существующие ID)
    tags_data = request.getlist(tags_list)  # Здесь список тегов, включая новые
    new_tag_ids = []  # Для хранения ID тегов (как существующих, так и новых)
    print(tags_data)
    # Получаем все существующие теги для проверки
    existing_tags = {tag.tag_name for tag in Tag.objects.all()}  # Используем множество для быстрого поиска

    existing_lower_tags = {tag.lower() for tag in existing_tags}
    for tag in tags_data:
        tag_lower = tag.lower()
        # Если тег не является числом и не существует в базе, создаем его
        if tag_lower not in existing_lower_tags:
            # Создаем новый тег в базе данных
            new_tag = Tag.objects.create(tag_name=tag)
            # Добавляем ID нового тега в список
            new_tag_ids.append(str(new_tag.id))
        else:
            try:
                # Если тег уже существует, просто добавляем его ID в список
                existing_tag = Tag.objects.get(tag_name=tag)
                new_tag_ids.append(str(existing_tag.id))
                print(existing_tag.id)
            except Exception as e:
                print(f"Тег {tag} уже существует")

    # Копируем данные POST-запроса и заменяем список тегов на список их ID
    post_data = request.copy()
    post_data.setlist(tags_list, new_tag_ids)  # Заменяем теги их ID
    return post_data  # Возвращаем обновленные данные POST-запроса


def add_event_log(user, task, text):
    try:
        name = f"{user.engineer.first_name} {user.engineer.second_name}"
    except AttributeError:
        # Если у пользователя нет engineer, использовать имя пользователя
        name = user.username

    pattern = f"{text} [{name} / {datetime.now().strftime('%d.%m.%Y %H:%M')}]\n"
    task.completion_text += pattern
    task.save()


@login_required
@atomic
def create_task(request):
    redirect_to = reverse("tasks")

    if request.method == "POST":

        created_text = auto_resize_pic(request.POST.get("text"))  # Обрабатываем текст
        post_data = request.POST.copy()  # Создаём копию данных формы
        post_data["text"] = created_text  # Заменяем текст в копии
        print(created_text)
        post_data = create_tags(post_data, "tags_create")  # Сохраняем теги и возвращаем
        print(post_data)
        # Теперь создаем форму с обновлёнными данными (содержит ID всех тегов)
        form = AddTaskForm(post_data, request.FILES, instance=Task(creator=request.user))

        # Получаем URL с параметрами фильтров
        redirect_to = request.POST.get("from_url", redirect_to).strip()


        if form.is_valid():
            task = form.save()

            # Сохраняем прикреплённые файлы (если они есть)
            for file in request.FILES.getlist("files[]"):
                task.files.add(AttachedFile.objects.create(file=file))

            messages.add_message(
                request, messages.SUCCESS, f"Задача '{form.cleaned_data['header']}' успешно создана"
            )
            add_event_log(user=request.user, task=task, text="➕ Задача создана")
            return redirect(redirect_to)
        else:
            messages.add_message(request, messages.WARNING, form.errors)

    return redirect(redirect_to)


@login_required
@atomic
def edit_task(request, task_id):
    task = get_object_or_404(Task, pk=task_id)

    # Стандартный редирект на список задач
    redirect_to = reverse("tasks")

    if request.method == "POST":
        edited_text = auto_resize_pic(request.POST.get("text_edit"))  # Обрабатываем текст
        post_data = request.POST.copy()  # Создаём копию данных формы
        post_data["text_edit"] = edited_text  # Заменяем текст в копии

        post_data = create_tags(post_data, "tags_edit")  # Обновляем теги

        form = EditTaskForm(post_data, request.FILES, instance=task)  # Используем обновлённые данные

        # Получаем URL с параметрами фильтров
        redirect_to = request.POST.get("from_url", redirect_to).strip()

        if form.is_valid():
            updated_task = form.save()

            # Удаляем неиспользуемые прикрепленные файлы
            remove_unused_attached_files(request.POST.get("fileuploader-list-files"), updated_task)

            # Обработка прикрепленных файлов
            for file in request.FILES.getlist("files[]"):
                updated_task.files.add(AttachedFile.objects.create(file=file))
            updated_task.save()

            add_event_log(user=request.user, task=updated_task, text="✏️ Задача отредактирована")

            messages.add_message(
                request, messages.SUCCESS, f"Задача '{form.cleaned_data['header']}' отредактирована"
            )
        else:
            messages.add_message(request, messages.WARNING, form.errors)

    # Редирект на исходную страницу с фильтрами
    return redirect(redirect_to)


@login_required
@atomic
def take_task(request, task_id):
    task = get_object_or_404(Task, pk=task_id)
    # Стандартный редирект на список задач
    redirect_to = reverse("tasks")

    if request.method == "POST":
        # Получаем URL с параметрами фильтров
        redirect_to = request.POST.get("from_url", redirect_to).strip()

        try:
            Engineer.objects.get(user=request.user)
            print(request.user.engineer)
            task.engineers.add(request.user.engineer)
            task.save()
            add_event_log(user=request.user, task=task, text="🙋‍♂️Пользователь взял задачу")
            messages.add_message(request, messages.SUCCESS, f"Задача '{task.header}' добавлена в Мои задачи")
        except Engineer.DoesNotExist:
            print(f"у {request.user} нет инженера")
            messages.add_message(request, messages.WARNING, f"у {request.user} нет инженера")
            return redirect(redirect_to)

    # Редирект на исходную страницу
    return redirect(redirect_to)


@login_required
def delete_task(request, task_id):
    redirect_to: str = reverse("tasks")

    if request.method == "POST":

        # Получаем URL с параметрами фильтров
        redirect_to = request.POST.get("from_url", redirect_to).strip()

        task = get_object_or_404(Task, pk=task_id)

        if request.user.is_staff or request.user == task.creator:

            # Обновление задачи
            task.deleted = True

            task.save()

            add_event_log(user=request.user, task=task, text="🗑️ Задача удалена")

            messages.add_message(request, messages.SUCCESS, f"Задача '{task.header}' удалена")
        else:
            messages.add_message(request, messages.ERROR, f"Недостаточно прав для удаления задачи")

    return HttpResponseRedirect(redirect_to)


@login_required
def reopen_task(request, task_id):
    """
    Устанавливает в поле task.is_done = False и добавляет комментарий к полю task.completion_text
    При успешном изменении полей - редирект на страницу откуда была вызвана
    """
    redirect_to: str = reverse("tasks")

    if request.method == "POST":
        task = get_object_or_404(Task, pk=task_id)

        # Получаем URL с параметрами фильтров
        redirect_to = request.POST.get("from_url", redirect_to).strip()

        # Обновление задачи
        task.is_done = False

        task.save()
        add_event_log(user=request.user, task=task, text="↩️ Задача переоткрыта")
        messages.add_message(request, messages.SUCCESS, f"Задача '{task.header}' возвращена в работу")

    return HttpResponseRedirect(redirect_to)


@login_required
def comment_task(request, task_id):
    redirect_to: str = reverse("tasks")

    if request.method == "POST":

        task = get_object_or_404(Task, pk=task_id)
        is_done = "is_done" in request.POST
        answer = request.POST.get("answer", "").strip()  # Убираем лишние пробелы

        # Получаем URL с параметрами фильтров (если нужно)
        redirect_to = request.POST.get("from_url", redirect_to).strip()


        if answer:
            print(answer)
            text = auto_resize_pic(answer)
            print(text)
            comment = Comment.objects.create(
                task=task,
                author=request.user,
                text=text,
            )
            comment.save()

        if is_done:
            # Обновление задачи
            task.is_done = True
            task.save()

            # Логируем событие о закрытии задачи
            add_event_log(user=request.user, task=task, text="✅ Задача закрыта")
            messages.add_message(request, messages.SUCCESS, f"Задача '{task.header}' закрыта")
        else:
            # Логируем событие о новом комментарии
            add_event_log(user=request.user, task=task, text="⤴️ Ответ на задачу")
            messages.add_message(request, messages.SUCCESS, f"Добавлен ответ к задаче '{task.header}'")

    return HttpResponseRedirect(redirect_to)


# @login_required
# def close_task(request, task_id):
#
#     redirect_to: str = reverse("tasks")
#
#     if request.method == "POST":
#         task = get_object_or_404(Task, pk=task_id)
#         comment = request.POST.get("comment", "")
#
#         # Получаем URL с параметрами фильтров
#         redirect_to = request.POST.get("from_url", redirect_to).strip()
#
#         # Обновление задачи
#         task.is_done = True
#         # task.completion_time = datetime.now()
#         task.save()
#         add_event_log(user=request.user, task=task, text="✅ Задача закрыта")
#         messages.add_message(request, messages.SUCCESS, f"Задача '{task.header}' закрыта")
#
#     return HttpResponseRedirect(redirect_to)


@login_required
def export_to_excel(request):
    tasks = get_tasks(request, "filter_params", page_number=1, per_page=100)

    export = TasksExcelExport("Tasks")

    paginator = tasks["pagination_data"]["paginator"]

    for page_num in range(paginator.num_pages):
        page_data = paginator.get_page(page_num)
        print(page_data.object_list)
        export.add_tasks(page_data.object_list)

    return export.make_response(filename=f"tasks_for_{request.user}_{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


@login_required
def print_tasks(request):
    filter_params = request.GET.urlencode()  # Сохраняем все фильтры из запроса

    # Указываем большое значение per_page, чтобы получить все задачи
    tasks = get_tasks(request, filter_params, page_number=1, per_page=100000)

    # Получаем список всех задач
    all_tasks = tasks["pagination_data"]["paginator"].object_list

    # Сортируем задачи
    sorted_tasks = sorted(all_tasks, key=lambda task: (task.completion_time or task.create_time, task.create_time))

    tasks_data = []
    for task in sorted_tasks:
        engineers = [str(engineer.second_name) for engineer in task.engineers.all()]
        departments = [str(department) for department in task.departments.all()]
        responsible_list = departments + engineers
        responsible = ", ".join(responsible_list) if responsible_list else ""

        formatted_date = format(task.completion_time, "d.m.Y") if task.completion_time else "—"

        task_info = {
            "date": formatted_date,
            "header": task.header,
            "engineers": responsible,
            "is_done": task.is_done,
            "priority": task.priority,
        }
        tasks_data.append(task_info)

    return render(request, "components/task/print.html", {"tasks": tasks_data})
