import re

from django.test import TestCase

from tasks.models import Object, ObjectGroup, UserObjectGroup, Engineer, Tag
from tasks.services.tree_nodes import ObjectsTree, EngineersTree, GroupsTree, ObjectsTagsTree
from user.models import User


def find_all_ids_in_tree(nodes) -> list[int]:
    """
    Возвращает список ID объектов в дереве.
    Через регулярку достаем все ID объектов и создаем отсортированный список.
    """
    return sorted(map(int, re.findall(r"'id': (\d+),", str(nodes))))


class TestObjectsTree(TestCase):
    fixtures = ["tasks/tests/fixtures/v1.json"]

    def test_empty_user(self):
        """Пользователь без групп не видит перечень объектов."""
        user = User.objects.get(username="empty_user")
        context = {"user": user}
        nodes = ObjectsTree(context).get_nodes()

        self.assertListEqual([], nodes, f"Пользователь без групп доступов видит объекты в ObjectsTree!")

    def test_superuser(self):
        """Суперпользователь видит все объекты."""
        user = User.objects.get(username="admin")
        context = {"user": user}
        nodes = ObjectsTree(context).get_nodes()

        # Через регулярку достаем все ID объектов и создаем отсортированный список.
        match_ids = find_all_ids_in_tree(nodes)
        valid_ids = sorted(Object.objects.all().values_list("id", flat=True))

        # Проверяем, что все объекты есть в ответе.
        self.assertListEqual(
            valid_ids,
            match_ids,
            f"Суперпользователь НЕ видит все объекты в ObjectsTree!",
        )

    def test_noc_user_without_engineer(self):
        """Пользователь с доступом 'noc' видит только объекты с доступом 'noc'."""
        user = User.objects.get(username="noc")
        context = {"user": user}
        nodes = ObjectsTree(context).get_nodes()

        # Через регулярку достаем все ID объектов и создаем отсортированный список.
        match_ids = find_all_ids_in_tree(nodes)

        valid_ids = sorted(Object.objects.filter(groups__users=user).distinct().values_list("id", flat=True))

        # Проверяем, что все объекты есть в ответе.
        self.assertNotEqual(
            valid_ids > match_ids,
            "Пользователь 'noc' НЕ видит некоторые объекты в ObjectsTree",
        )
        self.assertNotEqual(
            valid_ids < match_ids,
            "Пользователь 'noc' видит ЛИШНИЕ объекты в ObjectsTree",
        )

        self.assertListEqual(
            valid_ids,
            match_ids,
            "Пользователь 'noc' видит не те объекты в ObjectsTree",
        )

    def test_user_with_engineer(self):
        """Пользователь с доступом 'engineer' видит только объекты с доступом 'engineer'."""
        user = User.objects.get(username="noah_griffith")
        context = {"user": user}
        nodes = ObjectsTree(context).get_nodes()

        # Через регулярку достаем все ID объектов и создаем отсортированный список.
        match_ids = find_all_ids_in_tree(nodes)

        valid_ids = sorted(Object.objects.filter(groups__users=user).distinct().values_list("id", flat=True))

        # Проверяем, что все объекты есть в ответе.
        self.assertNotEqual(
            valid_ids > match_ids,
            "Пользователь 'noah_griffith' НЕ видит некоторые объекты в ObjectsTree",
        )
        self.assertNotEqual(
            valid_ids < match_ids,
            "Пользователь 'noah_griffith' видит ЛИШНИЕ объекты в ObjectsTree",
        )

        self.assertListEqual(
            valid_ids,
            match_ids,
            "Пользователь 'noah_griffith' видит не те объекты в ObjectsTree",
        )

    def test_no_context(self):
        """Проверяем, что при пустом контексте будет ошибка."""
        with self.assertRaises(TypeError):
            ObjectsTree({}).get_nodes()

    def test_no_user(self):
        """Проверяем, что при отсутствии пользователя в контексте будет ошибка"""
        context = {"user": None}
        with self.assertRaises(TypeError):
            ObjectsTree(context).get_nodes()

    def test_no_objects(self):
        """Проверяем, что при отсутствии объектов в базе данных, возвращается пустой список."""
        Object.objects.all().delete()
        context = {"user": User.objects.get(username="noah_griffith")}
        nodes = ObjectsTree(context).get_nodes()
        self.assertListEqual(
            [], nodes, "При отсутствии объектов в базе данных возвращается не пустой список."
        )

    def test_no_groups(self):
        """Проверяем, что при отсутствии групп в базе данных, возвращается пустой список."""
        ObjectGroup.objects.all().delete()
        context = {"user": User.objects.get(username="noah_griffith")}
        nodes = ObjectsTree(context).get_nodes()
        self.assertListEqual([], nodes, "При отсутствии групп в базе данных возвращается не пустой список.")

    def test_no_permissions(self):
        """Проверяем, что при отсутствии прав в базе данных, возвращается пустой список."""
        UserObjectGroup.objects.all().delete()
        context = {"user": User.objects.get(username="noah_griffith")}
        nodes = ObjectsTree(context).get_nodes()
        self.assertListEqual([], nodes, "При отсутствии прав в базе данных возвращается не пустой список.")


class TestGroupsTree(TestCase):
    fixtures = ["tasks/tests/fixtures/v1.json"]

    def test_empty_user(self):
        """Пользователь без групп не видит перечень групп объектов."""
        user = User.objects.get(username="empty_user")
        context = {"user": user}
        nodes = GroupsTree(context).get_nodes()

        self.assertListEqual(
            [], nodes, f"Пользователь без групп доступов видит группы объектов в GroupsTree!"
        )

    def test_superuser(self):
        """Суперпользователь видит все объекты."""
        user = User.objects.get(username="admin")
        context = {"user": user}
        nodes = GroupsTree(context).get_nodes()

        # Через регулярку достаем все ID объектов и создаем отсортированный список.
        match_ids = find_all_ids_in_tree(nodes)
        valid_ids = sorted(ObjectGroup.objects.all().values_list("id", flat=True))

        # Проверяем, что все объекты есть в ответе.
        self.assertListEqual(
            valid_ids,
            match_ids,
            f"Суперпользователь НЕ видит все группы объектов в GroupsTree!",
        )

    def test_noc_user_without_engineer(self):
        """Пользователь с доступом 'noc' видит только объекты с доступом 'noc'."""
        user = User.objects.get(username="noc")
        context = {"user": user}
        nodes = GroupsTree(context).get_nodes()

        # Через регулярку достаем все ID объектов и создаем отсортированный список.
        match_ids = find_all_ids_in_tree(nodes)

        valid_ids = sorted(ObjectGroup.objects.filter(users=user).distinct().values_list("id", flat=True))

        # Проверяем, что все объекты есть в ответе.
        self.assertNotEqual(
            valid_ids > match_ids,
            "Пользователь 'noc' НЕ видит некоторые группы объектов в GroupsTree",
        )
        self.assertNotEqual(
            valid_ids < match_ids,
            "Пользователь 'noc' видит ЛИШНИЕ группы объектов в GroupsTree",
        )

        self.assertListEqual(
            valid_ids,
            match_ids,
            "Пользователь 'noc' видит не те группы объектов в GroupsTree",
        )

    def test_user_with_engineer(self):
        """Пользователь с доступом 'engineer' видит только объекты с доступом 'engineer'."""
        user = User.objects.get(username="noah_griffith")
        context = {"user": user}
        nodes = GroupsTree(context).get_nodes()

        # Через регулярку достаем все ID объектов и создаем отсортированный список.
        match_ids = find_all_ids_in_tree(nodes)

        valid_ids = sorted(ObjectGroup.objects.filter(users=user).distinct().values_list("id", flat=True))

        # Проверяем, что все объекты есть в ответе.
        self.assertNotEqual(
            valid_ids > match_ids,
            "Пользователь 'noah_griffith' НЕ видит некоторые группы объектов в GroupsTree",
        )
        self.assertNotEqual(
            valid_ids < match_ids,
            "Пользователь 'noah_griffith' видит ЛИШНИЕ группы объектов в GroupsTree",
        )

        self.assertListEqual(
            valid_ids,
            match_ids,
            "Пользователь 'noah_griffith' видит не те группы объектов в GroupsTree",
        )

    def test_no_context(self):
        """Проверяем, что при пустом контексте будет ошибка."""
        with self.assertRaises(TypeError):
            GroupsTree({}).get_nodes()

    def test_no_user(self):
        """Проверяем, что при отсутствии пользователя в контексте будет ошибка"""
        context = {"user": None}
        with self.assertRaises(TypeError):
            GroupsTree(context).get_nodes()

    def test_no_objects(self):
        """Проверяем, что при отсутствии объектов в базе данных, возвращается пустой список."""
        Object.objects.all().delete()
        context = {"user": User.objects.get(username="noah_griffith")}
        nodes = GroupsTree(context).get_nodes()
        self.assertListEqual(
            [], nodes, "При отсутствии объектов в базе данных возвращается не пустой список."
        )

    def test_no_groups(self):
        """Проверяем, что при отсутствии групп в базе данных, возвращается пустой список."""
        ObjectGroup.objects.all().delete()
        context = {"user": User.objects.get(username="noah_griffith")}
        nodes = GroupsTree(context).get_nodes()
        self.assertListEqual([], nodes, "При отсутствии групп в базе данных возвращается не пустой список.")

    def test_no_permissions(self):
        """Проверяем, что при отсутствии прав в базе данных, возвращается пустой список."""
        UserObjectGroup.objects.all().delete()
        context = {"user": User.objects.get(username="noah_griffith")}
        nodes = GroupsTree(context).get_nodes()
        self.assertListEqual([], nodes, "При отсутствии прав в базе данных возвращается не пустой список.")


class TestObjectsTagsTree(TestCase):
    fixtures = ["tasks/tests/fixtures/v1.json"]

    def test_empty_user(self):
        """Пользователь без групп не видит перечень групп объектов."""
        user = User.objects.get(username="empty_user")
        context = {"user": user}
        nodes = ObjectsTagsTree(context).get_nodes()

        self.assertListEqual(
            [], nodes, f"Пользователь без групп доступов видит теги объектов в ObjectsTagsTree!"
        )

    def test_superuser(self):
        """Суперпользователь видит все объекты."""
        user = User.objects.get(username="admin")
        context = {"user": user}
        nodes = ObjectsTagsTree(context).get_nodes()

        # Через регулярку достаем все ID объектов и создаем отсортированный список.
        match_ids = find_all_ids_in_tree(nodes)
        valid_ids = sorted(Tag.objects.filter(objects_set__isnull=False).values_list("id", flat=True))

        # Проверяем, что все объекты есть в ответе.
        self.assertListEqual(
            valid_ids,
            match_ids,
            f"Суперпользователь НЕ видит все теги объектов в ObjectsTagsTree!",
        )

    def test_noc_user_without_engineer(self):
        """Пользователь с доступом 'noc' видит только теги объектов с доступом 'noc'."""
        user = User.objects.get(username="noc")
        context = {"user": user}
        nodes = ObjectsTagsTree(context).get_nodes()

        # Через регулярку достаем все ID объектов и создаем отсортированный список.
        match_ids = find_all_ids_in_tree(nodes)

        valid_ids = sorted(
            Tag.objects.filter(objects_set__isnull=False, objects_set__groups__users=user)
            .distinct()
            .values_list("id", flat=True)
        )

        # Проверяем, что все объекты есть в ответе.
        self.assertNotEqual(
            valid_ids > match_ids,
            "Пользователь 'noc' НЕ видит некоторые теги объектов в ObjectsTagsTree",
        )
        self.assertNotEqual(
            valid_ids < match_ids,
            "Пользователь 'noc' видит ЛИШНИЕ теги объектов в ObjectsTagsTree",
        )

        self.assertListEqual(
            valid_ids,
            match_ids,
            "Пользователь 'noc' видит не те теги объектов в ObjectsTagsTree",
        )

    def test_user_with_engineer(self):
        """Пользователь с доступом 'engineer' видит только теги объектов с доступом 'engineer'."""
        user = User.objects.get(username="noah_griffith")
        context = {"user": user}
        nodes = ObjectsTagsTree(context).get_nodes()

        # Через регулярку достаем все ID объектов и создаем отсортированный список.
        match_ids = find_all_ids_in_tree(nodes)

        valid_ids = sorted(
            Tag.objects.filter(objects_set__isnull=False, objects_set__groups__users=user)
            .distinct()
            .values_list("id", flat=True)
        )

        # Проверяем, что все объекты есть в ответе.
        self.assertNotEqual(
            valid_ids > match_ids,
            "Пользователь 'noah_griffith' НЕ видит некоторые теги объектов в ObjectsTagsTree",
        )
        self.assertNotEqual(
            valid_ids < match_ids,
            "Пользователь 'noah_griffith' видит ЛИШНИЕ теги объектов в ObjectsTagsTree",
        )

        self.assertListEqual(
            valid_ids,
            match_ids,
            "Пользователь 'noah_griffith' видит не те теги объектов в ObjectsTagsTree",
        )

    def test_no_context(self):
        """Проверяем, что при пустом контексте будет ошибка."""
        with self.assertRaises(TypeError):
            ObjectsTagsTree({}).get_nodes()

    def test_no_user(self):
        """Проверяем, что при отсутствии пользователя в контексте будет ошибка"""
        context = {"user": None}
        with self.assertRaises(TypeError):
            ObjectsTagsTree(context).get_nodes()

    def test_no_objects(self):
        """Проверяем, что при отсутствии объектов в базе данных, возвращается пустой список тегов объектов."""
        Object.objects.all().delete()
        context = {"user": User.objects.get(username="noah_griffith")}
        nodes = ObjectsTagsTree(context).get_nodes()
        self.assertListEqual(
            [],
            nodes,
            "При отсутствии объектов в базе данных возвращается "
            "не пустой список тегов объектов в ObjectsTagsTree.",
        )

    def test_no_groups(self):
        """Проверяем, что при отсутствии групп в базе данных, возвращается пустой список тегов объектов."""
        ObjectGroup.objects.all().delete()
        context = {"user": User.objects.get(username="noah_griffith")}
        nodes = ObjectsTagsTree(context).get_nodes()
        self.assertListEqual(
            [],
            nodes,
            "При отсутствии групп в базе данных возвращается "
            "не пустой список тегов объектов в ObjectsTagsTree",
        )

    def test_no_permissions(self):
        """Проверяем, что при отсутствии прав в базе данных, возвращается пустой список тегов объектов."""
        UserObjectGroup.objects.all().delete()
        context = {"user": User.objects.get(username="noah_griffith")}
        nodes = ObjectsTagsTree(context).get_nodes()
        self.assertListEqual(
            [],
            nodes,
            "При отсутствии прав в базе данных возвращается "
            "не пустой список тегов объектов в ObjectsTagsTree",
        )


class TestEngineersTree(TestCase):
    fixtures = ["tasks/tests/fixtures/v1.json"]

    @classmethod
    def setUpTestData(cls):
        cls.valid_node = [
            {
                "id": "dep_1",
                "label": "NOC",
                "children": [
                    {"id": "eng_1", "label": "Noah Griffith", "children": []},
                    {"id": "eng_2", "label": "Kyle Shields", "children": []},
                    {"id": "eng_3", "label": "Megan Horne", "children": []},
                ],
            },
            {
                "id": "dep_2",
                "label": "QA",
                "children": [
                    {"id": "eng_4", "label": "Sandra Schmidt", "children": []},
                    {"id": "eng_5", "label": "Adrian Robertson", "children": []},
                    {"id": "eng_6", "label": "Chad Orr", "children": []},
                    {"id": "eng_7", "label": "Sara Ray", "children": []},
                ],
            },
            {
                "id": "dep_3",
                "label": "IT",
                "children": [
                    {"id": "eng_8", "label": "Taylor Hickman", "children": []},
                    {"id": "eng_9", "label": "Jeffrey Mason", "children": []},
                    {"id": "eng_10", "label": "Richard Weiss", "children": []},
                ],
            },
        ]

    def perform_test(self, user):
        nodes = EngineersTree({"user": user}).get_nodes()

        self.assertListEqual(self.valid_node, nodes, f"Пользователь '{user}' НЕ видит всех инженеров.")

    def test_empty_user(self):
        """Пользователь без групп видит всех инженеров."""
        user = User.objects.get(username="empty_user")
        self.perform_test(user)

    def test_superuser(self):
        """Суперпользователь видит всех инженеров."""
        user = User.objects.get(username="admin")
        self.perform_test(user)

    def test_noc_user_without_engineer(self):
        """Пользователь с доступом 'noc' видит всех инженеров"""
        user = User.objects.get(username="noc")
        self.perform_test(user)

    def test_user_with_engineer(self):
        """Пользователь с доступом 'engineer' видит всех инженеров"""
        user = User.objects.get(username="noah_griffith")
        self.perform_test(user)

    def test_no_context(self):
        """Проверяем, что при пустом контексте будет ошибка."""
        nodes = EngineersTree({}).get_nodes()
        self.assertListEqual(self.valid_node, nodes, f"При пустом контексте не показывает инженеров.")

    def test_no_user(self):
        """Проверяем, что при отсутствии пользователя в контексте НЕ будет ошибки"""
        nodes = EngineersTree({"user": None}).get_nodes()
        self.assertListEqual(self.valid_node, nodes, f"При неверном пользователе не показывает инженеров.")

    def test_no_objects(self):
        """Проверяем, что при отсутствии инженеров в базе данных, возвращается пустой список."""
        Engineer.objects.all().delete()
        context = {"user": User.objects.get(username="admin")}
        nodes = EngineersTree(context).get_nodes()
        self.assertListEqual(
            [], nodes, "При отсутствии инженеров в базе данных возвращается не пустой список."
        )


# TODO: создать класс для тестирования тегов задач.
