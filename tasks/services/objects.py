from django.core.paginator import Paginator
from django.db.models import OuterRef, Subquery, Count, Case, When, Value, CharField
from django.db.models.functions import Length, Concat, Substr

from tasks.models import AttachedFile, Object


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
            "tags", "groups"
        )  # Предварительно загружаем связанные теги и группы для оптимизации запросов
        .filter(groups__users=request.user)
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

    return {
        "page_obj": page_obj,
        "end_show_ellipsis": end_show_ellipsis,
        "end_show_last_page_link": end_show_last_page_link,
        "start_show_ellipsis": start_show_ellipsis,
        "start_show_first_page_link": start_show_first_page_link,
        "last_page_number": total_pages,
    }


def get_objects_tree() -> list:
    # [ {
    #   id: 'a',
    #   label: 'a',
    #   children: [ {
    #     id: 'aa',
    #     label: 'aa',
    #   }, {
    #     id: 'ab',
    #     label: 'ab',
    #   } ],
    # }, {
    #   id: 'b',
    #   label: 'b',
    # }, {
    #   id: 'c',
    #   label: 'c',
    # } ]

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


