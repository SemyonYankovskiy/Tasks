from django.db.models import Count, OuterRef, Subquery, Case, When, Value, CharField
from django.db.models.functions import Concat, Substr, Length

from tasks.models import Object, AttachedFile


def get_objects_list(request):
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
            tasks_count=Count('tasks', distinct=True),  # Подсчет уникальных задач, связанных с объектом
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


def get_objects_tree() -> list:
    """
    Вытягивает дерево объектов. Каждый объект может иметь родительский объект (parent),
    и функция строит дерево родительских и дочерних объектов.
    """

    # Запрос к базе данных для получения всех объектов с полями id, name и parent
    objects_qs = list(Object.objects.all().values("id", "name", "parent"))

    # Преобразуем список объектов в словарь, где ключом является id объекта
    objects = {
        obj["id"]: obj for obj in objects_qs
    }

    # Строим отношения "родитель-дети" для каждого объекта
    for obj in objects_qs:
        obj_id = obj["id"]
        parent = objects[obj_id]["parent"]

        if parent is not None:  # Если у объекта есть родитель
            # Добавляем дочерний объект к родителю в словарь
            objects[parent].setdefault("children", [])  # Если еще нет списка детей, создаем его
            if obj_id not in objects[parent]["children"]:
                objects[parent]["children"].append(obj_id)  # Добавляем id дочернего объекта

    # Вспомогательная функция для преобразования объекта и его детей в нужный формат
    def transform(obj_id: int):
        item = objects[obj_id]
        transformed_item = {
            'id': item['id'],  # Добавляем идентификатор объекта
            'label': item['name']  # Добавляем имя объекта
        }
        if item.get('children'):  # Если у объекта есть дети
            # Рекурсивно преобразуем детей
            transformed_item['children'] = [transform(child) for child in item["children"]]
        return transformed_item

    # Применяем преобразование к корневым элементам (у которых нет родителя)
    return [transform(obj_id) for obj_id in objects if objects[obj_id]["parent"] is None]
