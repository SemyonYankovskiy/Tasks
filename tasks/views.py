import json
import os
import random
from datetime import datetime
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q, F, OuterRef, Subquery, Case, When, Value, CharField
from django.db.models.functions import Concat, Substr, Length
from django.db.transaction import atomic
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from djangoProject import settings
from .filters import ObjectFilter, TaskFilter
from .forms import AddTaskForm, EditTaskForm
from .models import Object, Task, Tag, ObjectGroup, AttachedFile, Engineer


def get_objects_list(request):
    # Создаем подзапрос для получения первого файла изображения (jpeg, jpg, png)
    image_subquery = (
        AttachedFile.objects.filter(objects_set=OuterRef("pk"), file__iregex=r"\.(jpeg|jpg|png)$")
        .order_by("id")  # Сортируем по идентификатору
        .values("file")[:1]  # Получаем только поле 'file' и ограничиваем результат одним элементом
    )

    # Основной запрос для получения списка объектов
    objects = (
        Object.objects.all()  # Получаем все объекты
        .prefetch_related(
            "tags", "groups",
        )  # Предварительно загружаем связанные теги и группы для оптимизации запросов
        .filter(groups__users=request.user)
        .annotate(
            img_preview=Subquery(image_subquery),  # Добавляем аннотацию с изображением
            child_count=Count('children', distinct=True),  # Подсчёт уникальных детей
            description_length=Length('description'),  # Длина описания
            tasks_count=Count('tasks', distinct=True),  # Подсчёт уникальных задач
            short_description=Case(
                When(description_length__gt=53, then=Concat(Substr("description", 1, 50), Value("..."))),
                default="description",  # В противном случае используем полное описание
                output_field=CharField(),  # Указываем, что тип поля - строка
            ),
        )
        .only("id", "name", "priority", "slug")  # Ограничиваем выборку только необходимыми полями
        .distinct()  # Убираем дублирование объектов
        .order_by("parent_id", "-id")
    )
    return objects


@login_required
def get_home(request):
    # Создаем фильтр с параметрами запроса
    user_filter = ObjectFilter(request.GET, queryset=get_objects_list(request))

    # Применяем фильтр к запросу
    filtered_objects = user_filter.qs

    # Получаем номер страницы из запроса
    page_number = request.GET.get("page")

    # Используем функцию пагинации
    pagination_data = paginate_queryset(filtered_objects, page_number, per_page=8)

    # Получаем теги, связанные с объектами
    tags = Tag.objects.filter(objects_set__isnull=False).filter(objects_set__groups__users=request.user).distinct()

    tags = [{"id": tag.id, "label": tag.tag_name} for tag in tags]
    # Получаем группы, связанные с объектами
    groups = ObjectGroup.objects.filter(objects_set__isnull=False).filter(users=request.user).distinct()

    groups = [{"id": group.id, "label": group.name} for group in groups]

    exclude_params = ["page"]
    filter_data = {key: value for key, value in request.GET.items() if key not in exclude_params}

    # Формируем строку с параметрами фильтра
    filter_url = urlencode(filter_data, doseq=True)

    random_icon = get_random_icon(request)

    # Передаем отфильтрованные объекты в контекст
    context = {
        "pagination_data": pagination_data,
        "filter_data": filter_url,
        "tags_json": tags,
        "random_icon": random_icon,
        "current_tags": request.GET.getlist("tags"),
        "groups_json": groups,
        "current_groups": request.GET.getlist("groups"),
        "params_count": len([param for key, param in request.GET.items() if param and key != "page"])
    }

    return render(request, "components/home/home.html", context=context)


def paginate_queryset(queryset, page_number, per_page=4):
    paginator = Paginator(queryset, per_page)
    page_obj = paginator.get_page(page_number)

    total_pages = paginator.num_pages
    current_page = page_obj.number

    end_show_ellipsis = current_page < total_pages - 3
    end_show_last_page_link = current_page <= total_pages - 3
    start_show_ellipsis = current_page > 4
    start_show_first_page_link = current_page >= 4

    return {
        "page_obj": page_obj,
        "end_show_ellipsis": end_show_ellipsis,
        "end_show_last_page_link": end_show_last_page_link,
        "start_show_ellipsis": start_show_ellipsis,
        "start_show_first_page_link": start_show_first_page_link,
        "last_page_number": total_pages,
    }



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


@login_required
def get_object_page(request, object_slug):
    # Получаем основной объект
    obj = (
        Object.objects.filter(slug=object_slug)
        .prefetch_related("files", "tags", "groups")
        .annotate(
            parent_name=F("parent__name"),
            parent_slug=F("parent__slug"),
            done_tasks_count=Count("id", filter=Q(tasks__is_done=True)),
            undone_tasks_count=Count("id", filter=Q(tasks__is_done=False)),
        )
        .filter(groups__users=request.user)
        .first()
    )

    # Если объект не найден, выбрасываем исключение 404 (страница не найдена)
    if obj is None:
        raise Http404()

    # Получаем связанные задачи с учетом фильтров
    filtered_tasks_data = get_filtered_tasks(request, obj=obj)

    # Получаем номер страницы из запроса
    page_number = request.GET.get("page")
    # Используем функцию пагинации
    pagination_data = paginate_queryset(filtered_tasks_data["tasks"], page_number, per_page=4)
    filtered_tasks_data["tasks"] = pagination_data["page_obj"]

    child_objects = get_objects_list(request).filter(parent=obj)

    random_icon = get_random_icon(request)

    context = {
        "object": obj,
        "tasks": filtered_tasks_data,
        "random_icon": random_icon,
        "pagination_data": pagination_data,
        "task_count": obj.done_tasks_count + obj.undone_tasks_count,
        "child_objects": child_objects,
        "filter_data": "#tasks",
    }

    return render(request, "components/object/object-page.html", context=context)


def get_m2m_fields_for_tasks():
    # Получаем теги, связанные с задачами
    tags_qs = Tag.objects.filter(tasks__isnull=False).values("id", "tag_name").distinct()
    tags = [{"id": tag["id"], "label": tag["tag_name"]} for tag in tags_qs]  # label обязателен

    # Получаем инженеров, связанных с задачами
    engineers_qs = list(Engineer.objects.all().values("id", "first_name", "second_name"))
    engineers = [{"id": eng["id"], "label": f"{eng['first_name']} {eng['second_name']}"} for eng in engineers_qs]

    objects_tree = get_objects_tree()

    return {
        "tags_json": tags,
        "engineers_json": engineers,
        "objects_json": objects_tree,
    }


def get_objects_tree() -> list:
    objects_qs = list(Object.objects.all().values("id", "name", "parent"))
    objects = {
        obj["id"]: obj for obj in objects_qs
    }

    for obj in objects_qs:
        obj_id = obj["id"]
        parent = objects[obj_id]["parent"]

        if parent is not None:
            objects[parent].setdefault("children", [])
            if obj_id not in objects[parent]["children"]:
                objects[parent]["children"].append(obj_id)

    def transform(obj_id: int):
        item = objects[obj_id]
        transformed_item = {
            'id': item['id'],
            'label': item['name']
        }
        if item.get('children'):
            transformed_item['children'] = [transform(child) for child in item["children"]]
        return transformed_item

    # Применяем преобразование к корневым элементам
    return [transform(obj_id) for obj_id in objects if objects[obj_id]["parent"] is None]


def task_filter_params(request):
    not_count_params = ["show_my_tasks_only", "sort_order", "page", "show_active_task", "show_done_task"]

    exclude_params = ["page"]
    filter_data = {key: value for key, value in request.GET.items() if key not in exclude_params}

    # Формируем строку с параметрами фильтра
    filter_url = urlencode(filter_data, doseq=True) + "#tasks"

    return {
        **get_m2m_fields_for_tasks(),
        "current_tags": request.GET.getlist("tags"),
        "current_engineers": request.GET.getlist("engineers"),
        "current_objects": request.GET.getlist("objects_set"),
        "filter_data": filter_url,
        "params_count": len([param for key, param in request.GET.items() if param and key not in not_count_params])
    }


def get_filtered_tasks(request, obj=None):
    show_my_tasks_only = request.GET.get("show_my_tasks_only") == "true"
    sort_order = request.GET.get("sort_order", "desc")  # По умолчанию сортировка по убыванию
    if request.path.startswith("/calendar/"):
        show_active_task = request.GET.get("show_active_task", "true") == "true"
        show_done_task = request.GET.get("show_done_task", "true") == "true"
    else:
        show_active_task = request.GET.get("show_active_task", "true") == "true"
        show_done_task = request.GET.get("show_done_task", "false") == "true"

    try:
        engineer = Engineer.objects.get(user=request.user)
    except Engineer.DoesNotExist:
        engineer = None

    if request.user.is_superuser:
        basic_qs = Task.objects.all().distinct()
    else:
        basic_qs = Task.objects.all().filter(
            Q(objects_set__groups__users=request.user) | Q(engineers__user=request.user)).distinct()

    tasks = TaskFilter(request.GET, queryset=basic_qs).qs

    if show_my_tasks_only:
        if engineer:
            tasks = tasks.filter(engineers=engineer)
        else:
            tasks = tasks.none()

    # Если передан объект, фильтруем задачи по этому объекту
    if obj:
        tasks = tasks.filter(objects_set=obj)

    # Применение prefetch_related для оптимизации запросов
    tasks = tasks.prefetch_related("files", "tags", "engineers", "objects_set")

    # Сортировка по дате завершения: asc для возрастания, desc для убывания
    if sort_order == "asc":
        tasks = tasks.order_by("completion_time")
    else:
        tasks = tasks.order_by("-completion_time")

    done_tasks_count = tasks.filter(is_done=True).count()
    not_done_count = tasks.filter(is_done=False).count()

    if show_active_task and not show_done_task:
        tasks = tasks.filter(is_done=False)
    elif show_done_task and not show_active_task:
        tasks = tasks.filter(is_done=True)
    elif show_active_task and show_done_task:
        tasks = tasks  # Показываем и активные, и завершённые задачи
    else:
        tasks = tasks.none()  # Если оба фильтра выключены, ничего не показываем

    context = {
        "tasks": tasks,
        "show_active_task": show_active_task,
        "show_done_task": show_done_task,
        "done_count": done_tasks_count,
        "not_done_count": not_done_count,
        "show_my_tasks_only": show_my_tasks_only,
        "sort_order": sort_order,
    }
    return context


@login_required
def tasks_page(request):
    filtered_task = get_filtered_tasks(request)

    filter_context = task_filter_params(request)

    # Получаем номер страницы из запроса
    page_number = request.GET.get("page")
    # Используем функцию пагинации
    pagination_data = paginate_queryset(filtered_task["tasks"], page_number, per_page=4)

    random_icon = get_random_icon(request)

    return render(
        request,
        "components/task/tasks_page.html",
        {
            "pagination_data": pagination_data,
            "random_icon": random_icon,
            "tasks": filtered_task,
            **filter_context,

        },
    )


@login_required
def get_task_view(request, task_id: int):
    task = get_object_or_404(Task, pk=task_id)
    return render(
        request,
        "components/task/task.html",
        {
            "task": task,
            "expanded": True,       # параметр для аккордеона, без него будет раскрыт
        },
    )


@login_required
def map_page(request):
    return render(request, "components/map/map.html")


@login_required
def calendar(request):
    random_icon = get_random_icon(request)
    tasks = get_filtered_tasks(request)
    filter_context = task_filter_params(request)

    return render(request, "components/calendar/calendar.html",
                  {"tasks": tasks, **filter_context, "random_icon": random_icon})


@login_required
def close_task(request, task_id):
    redirect_to: str = reverse("tasks")

    if request.method == "POST":
        task = get_object_or_404(Task, pk=task_id)
        comment = request.POST.get("comment", "")
        # Куда перенаправлять после успешного закрытия задачи
        redirect_to = request.POST.get("from_url", redirect_to).strip()

        # Обновление задачи
        task.is_done = True
        # task.completion_time = datetime.now()

        try:
            name = f"{request.user.engineer.first_name} {request.user.engineer.second_name}"
        except AttributeError:
            # Если у пользователя нет engineer, использовать имя пользователя
            name = request.user.username

        update_text = (f"\n______________________________________________________________\n"
                       f"Закрыто: [{name} / {datetime.now().strftime('%d.%m.%Y %H:%M')}]\n{comment}")

        task.text += update_text
        task.save()

    return HttpResponseRedirect(redirect_to)


@login_required
@atomic
def create_task(request):
    if request.method == 'POST':
        form = AddTaskForm(request.POST, request.FILES)

        if form.is_valid():
            task = form.save()  # Сохраняем задачу, но не коммитим
            # Проходимся по файлам и сохраняем их
            for file in request.FILES.getlist("files[]"):
                task.files.add(AttachedFile.objects.create(file=file))
            task.save()

            messages.add_message(request, messages.SUCCESS, f"Задача '{form.cleaned_data['header']}' успешно создана")
            return redirect("tasks")
        else:
            messages.add_message(request, messages.WARNING, form.errors)

    return redirect("tasks")


@login_required
def get_task_edit_form(request, task_id: int):
    task = get_object_or_404(Task, pk=task_id)
    fields = get_m2m_fields_for_tasks()

    context = {
        "task": task,
        **fields,
        "current_engineers": list(task.engineers.all().values_list("id", flat=True)),
        "current_tags_edit": list(task.tags.all().values_list("id", flat=True)),
        "current_objects_edit": list(task.objects_set.all().values_list("id", flat=True)),
    }
    return render(request, 'components/task/edit_task_form.html', context)


@login_required
@atomic
def edit_task(request, task_id):
    task = get_object_or_404(Task, pk=task_id)

    if request.method == 'POST':
        form = EditTaskForm(request.POST, request.FILES, instance=task)
        if form.is_valid():
            updated_task = form.save()

            remove_unused_task_attached_files(request.POST.get("fileuploader-list-files"), updated_task)

            # Обработка файлов
            for file in request.FILES.getlist('files[]'):
                updated_task.files.add(AttachedFile.objects.create(file=file))
            updated_task.save()

            messages.add_message(request, messages.SUCCESS, f"Задача '{form.cleaned_data['header']}' отредактирована")
        else:
            messages.add_message(request, messages.WARNING, form.errors)

    return redirect("tasks")


def remove_unused_task_attached_files(file_uploader_data: str, task: Task, *, delete_orphan_files: bool = False):
    """Удаляет прикрепленные к задачам файлы, которые не используются

    СИЛЬНО НЕ ЕБУ КАК РАБОТАЕТ"""

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






