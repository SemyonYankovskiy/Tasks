from django.db.models.query import Q

from tasks.models import Tag, ObjectGroup, Object, Engineer
from tasks.services.tree_nodes.base import Node, Tree


class ObjectsTagsTree(Tree):
    """
    Возвращает дерево тегов. Кого? Объектов.
    """

    def _get_queryset(self):
        qs = Tag.objects.filter(objects_set__isnull=False)

        user = self._context.get("user", None)
        if user is None:
            return qs.none()

        if not user.is_superuser:
            qs = qs.filter(objects_set__groups__users=user)

        return qs.distinct()

    def get_nodes(self) -> list[Node]:
        # Получаем теги, к которым есть доступ
        qs = self._get_queryset()
        result: list[Node] = [{"id": tag.id, "label": tag.tag_name} for tag in qs]
        return result


class TasksTagsTree(Tree):

    def _get_queryset(self):
        qs = Tag.objects.filter(tasks__isnull=False)  # Все теги только задач

        user = self._context.get("user", None)
        if user is None:
            # Если пользователь не авторизован
            return qs.none()

        engineer: Engineer | None = user.get_engineer_or_none()
        if engineer and engineer.head_of_department:
            qs = qs.filter(
                Q(tasks__departments=engineer.department)
                | Q(tasks__engineers__department=engineer.department)
            )
        elif engineer:
            qs = qs.filter(Q(tasks__engineers=engineer) | Q(tasks__departments=engineer.department_id))

        elif not user.is_superuser:
            qs = qs.none()

        return qs.distinct()

    def get_nodes(self) -> list[Node]:
        qs = self._get_queryset()
        result: list[Node] = [{"id": tag.id, "label": tag.tag_name} for tag in qs]
        return result


class GroupsTree(Tree):

    def _get_queryset(self):
        qs = ObjectGroup.objects.filter(objects_set__isnull=False)

        user = self._context.get("user", None)
        if user is None:
            return qs.none()

        if not user.is_superuser:
            qs = qs.filter(users=user)

        return qs.distinct()

    def get_nodes(self) -> list[Node]:
        qs = self._get_queryset()
        result: list[Node] = [{"id": group.id, "label": group.name} for group in qs]
        return result


class ObjectsTree(Tree):

    def _get_queryset(self):
        user = self._context.get("user", 0)
        qs = Object.objects.all().values("id", "name", "parent")

        if not user.is_superuser:
            # Запрос к базе данных для получения всех объектов с полями id, name и parent
            qs = qs.filter(groups__users=user)

        return qs

    def get_nodes(self) -> list[Node]:
        """
        Вытягивает дерево объектов. Каждый объект может иметь родительский объект (parent),
        и функция строит дерево родительских и дочерних объектов.
        """
        objects_qs = list(self._get_queryset())

        # Преобразуем список объектов в словарь, где ключом является id объекта
        objects: dict = {obj["id"]: obj for obj in objects_qs}

        # Строим отношения "родитель-дети" для каждого объекта
        for obj in objects_qs:
            obj_id = obj["id"]
            parent = objects[obj_id]["parent"]

            if parent is not None and objects.get(parent):  # Если у объекта есть родитель
                # Добавляем дочерний объект к родителю в словарь
                objects[parent].setdefault("children", [])  # Если еще нет списка детей, создаем его
                if obj_id not in objects[parent]["children"]:
                    objects[parent]["children"].append(obj_id)  # Добавляем id дочернего объекта

        # Вспомогательная функция для преобразования объекта и его детей в нужный формат
        def transform(object_id: int) -> Node:
            item = objects[object_id]
            node: Node = {
                "id": item["id"],  # Добавляем идентификатор объекта
                "label": item["name"],  # Добавляем имя объекта
            }
            if item.get("children"):  # Если у объекта есть дети
                # Рекурсивно преобразуем детей
                node["children"] = [transform(child) for child in item["children"]]
            return node

        # Применяем преобразование к корневым элементам (у которых нет родителя)
        result: list[Node] = [transform(obj_id) for obj_id in objects if objects[obj_id]["parent"] is None]
        return result


class EngineersTree(Tree):

    @staticmethod
    def _get_queryset():
        return Engineer.objects.all().values(
            "id", "first_name", "second_name", "department", "department__name"
        )

    def get_nodes(self) -> list[Node]:
        # Запрос к базе данных для получения всех объектов с полями id, first_name, second_name и department

        engineers_qs = list(self._get_queryset())

        # Словарь для департаментов
        departments: dict[int, Node] = {}

        # Список для инженеров без департаментов
        no_department_engineers: list[Node] = []

        # Проходим по каждому инженеру из выборки
        for engineer in engineers_qs:
            engineer_id: int = engineer["id"]
            engineer_label: str = engineer["first_name"] + " " + engineer["second_name"]
            department_id: int | None = engineer["department"]
            department_label: str = engineer["department__name"]

            # Если у инженера нет департамента, добавляем его в список без департаментов
            if department_id is None:
                no_department_engineers.append({"id": f"eng_{engineer_id}", "label": engineer_label})
            else:
                # Если департамент существует, проверяем, есть ли он уже в словаре департаментов
                if department_id not in departments:
                    departments[department_id] = {
                        "id": f"dep_{department_id}",
                        "label": department_label,
                        "children": [],
                    }
                # Добавляем инженера как "ребенка" в департамент
                departments[department_id]["children"].append(
                    {"id": f"eng_{engineer_id}", "label": engineer_label, "children": []}
                )

        # Преобразуем департаменты в список и добавляем в начало списка
        engineers_tree = list(departments.values())

        # Добавляем инженеров без департамента в конец списка
        engineers_tree.extend(no_department_engineers)
        return engineers_tree
