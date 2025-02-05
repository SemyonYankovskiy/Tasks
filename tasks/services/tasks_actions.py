from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.transaction import atomic
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.shortcuts import render
from django.urls import reverse
from django.utils.dateformat import format

from tasks.forms import AddTaskForm, EditTaskForm
from tasks.models import Task, AttachedFile, Engineer, Tag
from tasks.services.export import TasksExcelExport
from tasks.services.service import remove_unused_attached_files
from tasks.services.tasks_prepare import get_tasks


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

    pattern = f"{text}: [{name} / {datetime.now().strftime('%d.%m.%Y %H:%M')}]\n"
    task.completion_text += pattern
    task.save()


@login_required
@atomic
def create_task(request):
    redirect_to = reverse("tasks")

    if request.method == "POST":

        post_data = create_tags(request.POST, "tags_create")  # Сохраняем теги и возвращаем

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

    return redirect("tasks")


@login_required
@atomic
def edit_task(request, task_id):
    task = get_object_or_404(Task, pk=task_id)

    # Стандартный редирект на список задач
    redirect_to = reverse("tasks")

    if request.method == "POST":

        post_data = create_tags(request.POST, "tags_edit")  # Сохраняем теги и возвращаем

        form = EditTaskForm(post_data, request.FILES, instance=task)

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
        comment = request.POST.get("comment", "")
        # Получаем URL с параметрами фильтров
        redirect_to = request.POST.get("from_url", redirect_to).strip()

        # Обновление задачи
        task.is_done = False

        task.save()
        add_event_log(user=request.user, task=task, text="↩️ Задача переоткрыта: " + comment)
        messages.add_message(request, messages.SUCCESS, f"Задача '{task.header}' возвращена в работу")

    return HttpResponseRedirect(redirect_to)


@login_required
def close_task(request, task_id):
    """
    Устанавливает в поле task.is_done = True и добавляет комментарий к полю task.completion_text
    При успешном изменении полей - редирект на страницу откуда была вызвана
    """
    redirect_to: str = reverse("tasks")

    if request.method == "POST":
        task = get_object_or_404(Task, pk=task_id)
        comment = request.POST.get("comment", "")

        # Получаем URL с параметрами фильтров
        redirect_to = request.POST.get("from_url", redirect_to).strip()

        # if "?referrer=" in redirect_to:
        #     # Извлекаем параметры из URL
        #     parsed_url = urlparse(redirect_to)
        #     query_params = parse_qs(parsed_url.query)
        #
        #     # Получаем параметр referrer
        #     encoded_referrer = query_params.get("referrer", [""])[0]
        #     decoded_referrer = unquote(encoded_referrer)
        #
        #     redirect_to = decoded_referrer

        # Обновление задачи
        task.is_done = True
        # task.completion_time = datetime.now()
        task.save()
        add_event_log(user=request.user, task=task, text="✅ Задача закрыта: " + comment)
        messages.add_message(request, messages.SUCCESS, f"Задача '{task.header}' закрыта")

    return HttpResponseRedirect(redirect_to)


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
    tasks = get_tasks(request, filter_params, page_number=1, per_page=100)  # Передаем фильтры

    tasks_data = []
    paginator = tasks["pagination_data"]["paginator"]

    # Получаем все задачи, сортируем их
    sorted_tasks = sorted(paginator.object_list,
                          key=lambda task: (task.completion_time or task.create_time, task.create_time))

    # Применяем пагинацию
    for page_num in range(paginator.num_pages):
        page_data = paginator.get_page(page_num)

        for task in sorted_tasks:
            engineers = ", ".join([str(engineer.second_name) for engineer in task.engineers.all()])
            formatted_date = format(task.completion_time, "d.m.Y")

            task_info = {
                "date": formatted_date,
                "header": task.header,
                "engineers": engineers,
                "is_done": task.is_done,
            }
            tasks_data.append(task_info)

    return render(request, "components/task/print.html", {"tasks": tasks_data})

