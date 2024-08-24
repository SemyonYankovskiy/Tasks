from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, F, OuterRef, Subquery, When, Case, Value, CharField
from django.db.models.functions import Substr, Concat, Length
from django.http import Http404
from django.shortcuts import render
from .models import Object, Task, AttachedFile, Engineer
from .filters import ObjectFilter
import os

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
            .prefetch_related("tags",
                              "groups")  # Предварительно загружаем связанные теги и группы для оптимизации запросов
            .annotate(
            img_preview=Subquery(image_subquery),  # Добавляем аннотацию с изображением
            child_count=Count("children"),  # Подсчитываем количество детей
            description_length=Length("description"),  # Получаем длину полного описания
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
    filter = ObjectFilter(request.GET, queryset=get_objects_list(request))

    # Применяем фильтр к запросу
    filtered_objects = filter.qs

    # Передаем отфильтрованные объекты в контекст
    context = {
        "objects": filtered_objects,
        "filter": filter,  # Передаем фильтр в контекст для отображения в шаблоне
    }

    return render(request, "home.html", context=context)


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

    # Получаем связанные задачи для данного объекта
    tasks = Task.objects.filter(objects_set=obj).prefetch_related("files", "tags", "engineers")


    child_objects = get_objects_list(request).filter(parent=obj)

    context = {
        "object": obj,
        "tasks": tasks,
        "task_count": obj.done_tasks_count + obj.undone_tasks_count,
        "done_count": obj.done_tasks_count,
        "not_done_count": obj.undone_tasks_count,
        "child_objects": child_objects,
    }

    return render(request, "object-page.html", context=context)


@login_required
def tasks_page(request):
    user = request.user

    show_my_tasks_only = request.GET.get('show_my_tasks_only') == 'true'
    sort_order = request.GET.get('sort_order', 'desc')  # По умолчанию сортировка по убыванию

    try:
        engineer = Engineer.objects.get(user=user)
    except Engineer.DoesNotExist:
        engineer = None

    if show_my_tasks_only:
        if engineer:
            tasks = Task.objects.filter(engineers=engineer).prefetch_related("files", "tags", "engineers")
        else:
            tasks = Task.objects.none()
    else:
        tasks = Task.objects.all().prefetch_related("files", "tags", "engineers")

    # Сортировка по дате создания: asc для возрастания, desc для убывания
    if sort_order == 'asc':
        tasks = tasks.order_by('completion_time')
    else:
        tasks = tasks.order_by('-completion_time')

    done_tasks_count = tasks.filter(is_done=True).count()
    undone_tasks_count = tasks.filter(is_done=False).count()

    context = {
        "tasks": tasks,
        "task_count": tasks.count(),
        "done_count": done_tasks_count,
        "not_done_count": undone_tasks_count,
        "show_my_tasks_only": show_my_tasks_only,
        "sort_order": sort_order,
    }

    return render(request, 'components/tasks_page.html', context=context)


@login_required
def map_page(request):
    return render(request, 'components/map.html')