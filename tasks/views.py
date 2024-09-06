from datetime import datetime
from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, F
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.urls import reverse

from .filters import ObjectFilter
from .models import Object, Task, Tag, ObjectGroup, Engineer
from .services.objects import get_objects_list, paginate_queryset, get_objects_tree
from .services.tasks import get_filtered_tasks


@login_required
def get_home(request):
    # Создаем фильтр с параметрами запроса
    user_filter = ObjectFilter(request.GET, queryset=get_objects_list(request))

    # Применяем фильтр к запросу
    filtered_objects = user_filter.qs

    # Получаем номер страницы из запроса
    page_number = request.GET.get("page")

    # Используем функцию пагинации
    pagination_data = paginate_queryset(filtered_objects, page_number, per_page=4)

    # Получаем теги, связанные с объектами
    tags = Tag.objects.filter(objects_set__isnull=False).distinct()

    tags = [{"id": tag.id, "label": tag.tag_name} for tag in tags]
    # Получаем группы, связанные с объектами
    groups = ObjectGroup.objects.filter(objects_set__isnull=False).distinct()

    groups = [{"id": group.id, "label": group.name} for group in groups]

    exclude_params = ["show_my_tasks_only", "sort_order", "page"]
    filter_data = {key: value for key, value in request.GET.items() if key not in exclude_params}

    # Формируем строку с параметрами фильтра
    filter_url = urlencode(filter_data, doseq=True)

    # Передаем отфильтрованные объекты в контекст
    context = {
        "pagination_data": pagination_data,
        "filter_data": filter_url,
        "tags_json": tags,
        "current_tags": request.GET.getlist("tags"),
        "groups_json": groups,
        "current_groups": request.GET.getlist("groups"),
        "params_count": len([param for param in request.GET.values() if param])
    }

    return render(request, "components/home/home.html", context=context)


@login_required
def get_object_page(request, object_slug):
    user = request.user
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

    child_objects = get_objects_list(request).filter(parent=obj)

    context = {
        "object": obj,
        "tasks": filtered_tasks_data,
        "task_count": obj.done_tasks_count + obj.undone_tasks_count,
        "child_objects": child_objects,
    }

    return render(request, "components/object/object-page.html", context=context)


def task_filter_params(request):
    # Получаем теги, связанные с задачами
    tags_qs = Tag.objects.filter(tasks__isnull=False).values("id", "tag_name")
    tags = [{"id": tag["id"], "label": tag["tag_name"]} for tag in tags_qs]  # label обязателен

    # Получаем инженеров, связанных с задачами
    engineers_qs = list(Engineer.objects.all().values("id", "first_name", "second_name"))
    engineers = [{"id": eng["id"], "label": f"{eng['first_name']} {eng['second_name']}"} for eng in engineers_qs]

    objects_tree = get_objects_tree()

    filter_data = {key: value for key, value in request.GET.items() if key != "page"}

    # Формируем строку с параметрами фильтра
    filter_url = urlencode(filter_data, doseq=True)
    return {
        "tags_json": tags,
        "current_tags": request.GET.getlist("tags"),
        "engineers_json": engineers,
        "current_engineers": request.GET.getlist("engineers"),
        "current_objects": request.GET.getlist("objects_set"),
        "objects_json": objects_tree,
        "filter_data": filter_url,
        "params_count": len([param for param in request.GET.values() if param])
    }


@login_required
def tasks_page(request):
    filtered_task = get_filtered_tasks(request)

    filter_context = task_filter_params(request)

    return render(
        request,
        "components/task/tasks_page.html",
        {
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
    #tasks = Task.objects.all().values("id", "header", "completion_time", "priority", "is_done")


    tasks = get_filtered_tasks(request)
    filter_context = task_filter_params(request)

    return render(request, "components/calendar/calendar.html", {"tasks": tasks, **filter_context,})


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
