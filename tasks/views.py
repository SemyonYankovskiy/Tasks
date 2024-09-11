from datetime import datetime
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, F
from django.db.transaction import atomic
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse

from .filters import ObjectFilter
from .forms import AddTaskForm, EditTaskForm
from .models import Object, Task, Tag, ObjectGroup, AttachedFile
from .services.objects import get_objects_list, paginate_queryset
from .services.tasks import get_filtered_tasks, task_filter_params, get_m2m_fields_for_tasks


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


from django.shortcuts import render
from django.conf import settings
import os
import random


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
        {"task": task, "expanded": True, "form_type": "collapse"},
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

        update_text = f"\n\nЗакрыто: [{name} / {datetime.now().strftime('%d.%m.%Y %H:%M')}]\n{comment}"

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
@atomic
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
            updated_task = form.save(commit=False)
            updated_task.is_done = form.cleaned_data.get('is_done', False)
            updated_task.save()
            form.save_m2m()

            # Обработка файлов
            files = request.FILES.getlist('files')
            for file in files:
                attached_file = AttachedFile(file=file)
                attached_file.save()
                updated_task.files.add(attached_file)

            messages.add_message(request, messages.SUCCESS, f"Задача '{form.cleaned_data['header']}' отредактирована")
            return redirect("tasks")
        else:
            messages.add_message(request, messages.WARNING, form.errors)
            return redirect("tasks")
    else:
        form = EditTaskForm(instance=task)

        # Передаем текущее состояние полей задачи
        context = {
            'form': form,
            'task': task,
        }
        return render(request, 'components/task/edit_task_button.html', context)
