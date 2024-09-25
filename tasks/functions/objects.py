from django.db.models import Count, OuterRef, Subquery, Case, When, Value, CharField, QuerySet
from django.db.models.functions import Concat, Substr, Length

from tasks.models import Object, AttachedFile
from user.models import User
from .tasks_prepare import permission_filter


def get_objects_list(request) -> QuerySet[Object]:
    """
    Создает запрос к базе данных для получения объектов и добавляет дополнительные поля
    через аннотации и подзапросы, такие, как превью изображения, количество дочерних объектов и задач.
    """

    # Подзапрос для получения первого файла изображения (jpeg, jpg, png) для каждого объекта
    image_subquery = (
        AttachedFile.objects.filter(objects_set=OuterRef("pk"), file__iregex=r"\.(jpeg|jpg|png)$")
        .order_by("id")  # Сортировка по идентификатору файла (чтобы выбрать первый по порядку)
        .values("file")[:1]  # Получение только первого файла (поле 'file')
    )

    # Основной запрос для получения списка объектов
    objects = (
        Object.objects.all()  # Получаем все объекты из базы данных
        .prefetch_related("tags", "groups")  # Предзагрузка связанных тегов и групп для оптимизации запросов
        .filter(groups__users=request.user)  # Фильтрация объектов по пользователю, который связан с группой
        .annotate(
            img_preview=Subquery(image_subquery),  # Добавляем превью изображения как подзапрос
            child_count=Count('children', distinct=True),  # Подсчет уникальных дочерних объектов
            description_length=Length('description'),  # Подсчет длины описания объекта
            # tasks_count=Count('tasks', filter=Q(tasks__is_done=False), distinct=True),  # Подсчет активных задач
            short_description=Case(
                # Если длина описания больше 53 символов, обрезаем до 50 символов и добавляем "..."
                When(description_length__gt=53, then=Concat(Substr("description", 1, 50), Value("..."))),
                default="description",  # Если описание короче 53 символов, выводим его полностью
                output_field=CharField(),  # Поле с текстовым выводом
            ),
        )
        .only("id", "name", "priority", "slug")  # Ограничиваем выборку только нужными полями для оптимизации
        .distinct()  # Убираем дублирующиеся объекты (если были)
        .order_by("parent_id", "-id")  # Сортировка по полю `parent_id`, затем по убыванию `id`
    )
    return objects  # Возвращаем список объектов с аннотациями


def add_tasks_count_to_objects(queryset: QuerySet[Object], user: User, field_name: str) -> QuerySet[Object]:

    for obj in queryset:
        count: int = permission_filter(user).filter(objects_set=obj, is_done=False).count()
        setattr(obj, field_name, count)

    return queryset
