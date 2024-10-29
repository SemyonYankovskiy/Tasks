from django.db.models import Count, OuterRef, Subquery, Case, When, Value, CharField, QuerySet
from django.db.models.functions import Concat, Substr, Length

from tasks.models import Object, AttachedFile
from user.models import User
from .tasks_prepare import permission_filter


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





def add_tasks_count_to_objects(queryset: QuerySet[Object], user: User, field_name: str) -> QuerySet[Object]:
    for obj in queryset:
        count: int = permission_filter(user).filter(objects_set=obj, is_done=False).count()
        setattr(obj, field_name, count)

    return queryset






