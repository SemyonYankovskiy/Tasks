from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, F, OuterRef, Subquery, When, Case, Value, CharField
from django.db.models.functions import Substr, Concat, Length
from django.http import Http404
from django.shortcuts import render, get_object_or_404, redirect
from .models import Object, Task, AttachedFile, Engineer
from .filters import ObjectFilter
from django.core.paginator import Paginator


@login_required
def get_home(request):
    # Создаем фильтр с параметрами запроса
    user_filter = ObjectFilter(request.GET, queryset=get_objects_list(request))

    # Применяем фильтр к запросу
    filtered_objects = user_filter.qs

    # Получаем номер страницы из запроса
    page_number = request.GET.get('page')

    # Используем функцию пагинации
    pagination_data = paginate_queryset(filtered_objects, page_number)

    # Передаем отфильтрованные объекты в контекст
    context = {
        "pagination_data": pagination_data,
        "filter": user_filter,  # Передаем фильтр в контекст для отображения в шаблоне
    }

    return render(request, "components/home/home.html", context=context)


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


def paginate_queryset(queryset, page_number, per_page=4):
    paginator = Paginator(queryset, per_page)
    page_obj = paginator.get_page(page_number)

    total_pages = paginator.num_pages
    current_page = page_obj.number

    end_show_ellipsis = current_page < total_pages - 3
    end_show_last_page_link = current_page <= total_pages - 3
    start_show_ellipsis = current_page > 4
    start_show_first_page_link = current_page >= 4

    print(current_page)
    print(start_show_ellipsis)
    print(start_show_first_page_link)

    return {
        "page_obj": page_obj,
        "end_show_ellipsis": end_show_ellipsis,
        "end_show_last_page_link": end_show_last_page_link,
        "start_show_ellipsis": start_show_ellipsis,
        "start_show_first_page_link": start_show_first_page_link,
        "last_page_number": total_pages
    }


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
    filtered_tasks_data = get_filtered_tasks(request,
                                             # obj=obj
                                             )

    child_objects = get_objects_list(request).filter(parent=obj)

    context = {
        "object": obj,
        "tasks": filtered_tasks_data,
        "task_count": obj.done_tasks_count + obj.undone_tasks_count,
        "child_objects": child_objects,

    }

    return render(request, "components/object/object-page.html", context=context)


def get_filtered_tasks(request, obj=None):
    user = request.user
    show_my_tasks_only = request.GET.get('show_my_tasks_only') == 'true'
    sort_order = request.GET.get('sort_order', 'desc')  # По умолчанию сортировка по убыванию
    try:
        engineer = Engineer.objects.get(user=user)
    except Engineer.DoesNotExist:
        engineer = None

    if show_my_tasks_only:
        if engineer:
            tasks = Task.objects.filter(engineers=engineer)
        else:
            tasks = Task.objects.none()
    else:
        tasks = Task.objects.all()

    # Применение prefetch_related для оптимизации запросов
    tasks = tasks.prefetch_related("files", "tags", "engineers")

    # Разделение задач на выполненные и невыполненные
    done_tasks = tasks.filter(is_done=True)
    undone_tasks = tasks.filter(is_done=False)

    # Сортировка выполненных задач
    if sort_order == 'asc':
        done_tasks = done_tasks.order_by('completion_time')
        undone_tasks = undone_tasks.order_by('completion_time')
    else:
        done_tasks = done_tasks.order_by('-completion_time')
        undone_tasks = undone_tasks.order_by('-completion_time')

    done_tasks_count = done_tasks.count()
    not_done_count = undone_tasks.count()

    # # Если передан объект, фильтруем задачи по этому объекту
    # if obj:
    #     done_tasks = done_tasks.filter(objects_set=obj)
    #     undone_tasks = undone_tasks.filter(objects_set=obj)

    # Получаем номер страницы из запроса
    page_number = request.GET.get('page')

    # Пагинация выполненных задач
    done_pagination_data = paginate_queryset(done_tasks, page_number, per_page=2)

    # Пагинация невыполненных задач
    undone_pagination_data = paginate_queryset(undone_tasks, page_number, per_page=2)

    context = {
        "done_tasks": done_pagination_data,
        "undone_tasks": undone_pagination_data,
        "done_count": done_tasks_count,
        "not_done_count": not_done_count,
        "show_my_tasks_only": show_my_tasks_only,
        "sort_order": sort_order,
    }

    return context


@login_required
def tasks_page(request):
    context = get_filtered_tasks(request)
    return render(request, 'components/task/tasks_page.html', context=context)


@login_required
def map_page(request):
    return render(request, 'components/map/map.html')


def close_task(request, task_id):
    if request.method == 'POST':
        task = get_object_or_404(Task, pk=task_id)
        comment = request.POST.get('comment', '')

        # Обновление задачи
        task.is_done = True
        task.completion_time = datetime.now()

        try:
            name = f"{request.user.engineer.first_name} {request.user.engineer.second_name}"
        except AttributeError:
            # Если у пользователя нет engineer, использовать имя пользователя
            name = request.user.username

        update_text = f'\n\nЗакрыто: [{name}] {comment}' if comment else f'\n\nЗакрыто: [{name}]'

        task.text += update_text
        task.save()

        return redirect('tasks')

    return redirect('tasks')
