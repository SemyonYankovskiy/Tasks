
from django.core.cache import cache
from django.db.models import Count, OuterRef, Subquery, Case, When, Value, CharField, QuerySet
from django.db.models.functions import Concat, Substr, Length

from tasks.models import Object, AttachedFile
from .service import paginate_queryset
from .tasks_prepare import permission_filter
from ..filters import ObjectFilter


def get_objects_list(request) -> QuerySet[Object]:
    """
    Создает запрос к базе данных для получения объектов и добавляет дополнительные поля
    через аннотации и подзапросы, такие как превью изображения, количество дочерних объектов и задач.
    """

    # Подзапрос для получения первого файла изображения (jpeg, jpg, png) для каждого объекта
    image_subquery = (
        AttachedFile.objects.filter(objects_set=OuterRef("pk"), file__iregex=r"\.(jpeg|jpg|png)$")
        .order_by("id")
        .values("file")[:1]
    )

    # Подзапрос для подсчета активных задач (не завершенных) для каждого объекта
    tasks_count_subquery = (
        permission_filter(request.user)
        .filter(objects_set=OuterRef("pk"), is_done=False)
        .values('objects_set')
        .annotate(tasks_count=Count("id"))
        .values("tasks_count")
    )

    # Основной запрос для получения списка объектов
    objects = (
        Object.objects.all()
        .prefetch_related("tags", "groups")
        .filter(groups__users=request.user)
        .annotate(
            img_preview=Subquery(image_subquery),  # Добавляем превью изображения как подзапрос
            child_count=Count("children", distinct=True),  # Подсчет уникальных дочерних объектов
            description_length=Length("description"),
            tasks_count=Subquery(tasks_count_subquery, output_field=CharField()),  # Добавляем счетчик задач
            short_description=Case(
                When(description_length__gt=53, then=Concat(Substr("description", 1, 50), Value("..."))),
                default="description",
                output_field=CharField(),
            ),
        )
        .only("id", "name", "priority", "slug", "zabbix_link", "notes_link", "ecstasy_link", "another_link")
        .distinct()
        .order_by("parent_id", "-id")
    )

    return objects


def get_objects(request, filter_params, page_number, per_page):
    """
    Возвращает список объектов. Если не применяются фильтры - возвращает объекты из кэша
    """
    cache_key = f'objects-page:{page_number}:{request.user}'
    cached_data = cache.get(cache_key) if not filter_params else None

    if cached_data:
        return cached_data

    # ======= Фильтрация ======= #
    filtered_objects = ObjectFilter(request.GET, queryset=get_objects_list(request)).qs

    # ======= Пагинация ======= #
    pagination_data = paginate_queryset(filtered_objects, page_number, per_page)

    result = {
        "objects_qs": pagination_data["page_obj"],
        "pagination_data": pagination_data,
    }

    # Кэшируем результат, если отсутствуют фильтры
    if not filter_params:
        cache.set(cache_key, result, timeout=60)

    return result






