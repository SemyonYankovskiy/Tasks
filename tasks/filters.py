from urllib.parse import urlencode

import django_filters
from django.core.cache import cache
from django.db.models import Q

from .models import Object, Task, Engineer
from .services.cache_version import CacheVersion
from .services.service import default_date
from .services.tree_nodes import GroupsTree, ObjectsTree, EngineersTree
from .services.tree_nodes.tree_nodes import AllTagsTree


class ObjectFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(method="search_filter")



    class Meta:
        model = Object
        fields = ["search", "tags", "groups", "priority"]

    def search_filter(self, queryset, name: str, value: str):
        return queryset.filter(Q(name__icontains=value) | Q(description__icontains=value))


def get_fields_for_filter(user, page):
    """
    Возвращает древовидную структуру полей для отображения в фильтре
    """

    cache_key = f'filter_components:{page}:{user}'
    version_cache_key = f"filter_components_cache_version_{page}"
    cache_version = CacheVersion(version_cache_key)
    cache_version_value = cache_version.get_cache_version()
    context = {"user": user}

    # Попытка получить данные из кеша
    cached_data = cache.get(cache_key, version=cache_version_value)
    if cached_data:
        return cached_data
    # context = {"user": user}
    # Заполняем filter_fields_content в зависимости от страницы
    if page == "objects":
        filter_fields_content = {
            "tags_json": AllTagsTree(context).get_nodes(),
            "groups_json": GroupsTree(context).get_nodes(),
            "objects_json": ObjectsTree(context).get_nodes()
        }
    elif page == "tasks":
        filter_fields_content = {
            "tags_json": AllTagsTree(context).get_nodes(),
            "engineers_json": EngineersTree(context).get_nodes(),
            "objects_json": ObjectsTree(context).get_nodes(),
            "default_date": default_date(),
            "default_time": "17:30",
        }
    else:
        # Обработка неизвестного значения page
        raise ValueError(f"Неизвестное значение параметра 'page': {page}")

    # # Устанавливаем данные в кеш
    cache.set(cache_key, filter_fields_content, timeout=600, version=cache_version_value)
    return filter_fields_content


def get_current_filter_params(request, page):
    if page == "objects":
        current_params = {
            "current_tags": request.GET.getlist("tags"),
            "current_groups": request.GET.getlist("groups")}

    elif page == "tasks":
        current_params = {
            "current_tags": request.GET.getlist("tags"),
            "current_engineers": request.GET.getlist("engineers"),
            "current_objects": request.GET.getlist("objects_set")}

    else:
        # Обработка неизвестного значения page
        raise ValueError(f"Неизвестное значение параметра 'page': {page}")

    return current_params


class TaskFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(method="search_filter")
    engineers = django_filters.CharFilter(method="dep_to_engineers")
    completion_time_after = django_filters.DateFilter(
        field_name="completion_time", lookup_expr="date__gte", label="От"
    )
    completion_time_before = django_filters.DateFilter(
        field_name="completion_time", lookup_expr="date__lte", label="До"
    )
    sort_order = django_filters.CharFilter(method="filter_sort_order")
    show_my_tasks_only = django_filters.BooleanFilter(method="filter_show_my_tasks_only")

    class Meta:
        model = Task
        fields = [
            "search",
            "tags",
            "engineers",
            "priority",
            "objects_set",
            "completion_time_after",
            "completion_time_before",
        ]

    def __init__(self, *args, **kwargs):
        # Инициализируем базовый класс
        super().__init__(*args, **kwargs)
        self.data = self.data.copy()

        # Ensure 'show_my_tasks_only' is set based on user's staff status if request is available
        if self.data.get("show_my_tasks_only") is None:
            # Check if request exists and user is staff
            if hasattr(self, 'request') and self.request and hasattr(self.request,'user') and self.request.user.is_staff:
                print("не сука")
                self.data["show_my_tasks_only"] = "false"
            else:
                self.data["show_my_tasks_only"] = "true"

        if self.data.get("sort_order") is None:
            self.data["sort_order"] = "desc"

    @staticmethod
    def filter_sort_order(queryset, name: str, value: str):
        # Применяем сортировку по дате завершения
        if value == "asc":
            return queryset.order_by("completion_time", "create_time")
        return queryset.order_by("-completion_time", "-create_time")

    def filter_show_my_tasks_only(self, queryset, name: str, value: bool):
        engineer: Engineer | None = self.request.user.get_engineer_or_none()

        if engineer and value:
            return queryset.filter(engineers=engineer)
        return queryset

    def dep_to_engineers(self, queryset, name: str, value: str):
        values = self.data.getlist("engineers")

        if not values:
            return queryset

        q_objects = Q()
        for val in values:
            type_id = val.split("_")
            type = type_id[0]
            id = int(type_id[1])

            if type == "eng":
                q_objects |= Q(engineers__id=id)
            elif type == "dep":
                q_objects |= Q(engineers__department__id=id)

        return queryset.filter(q_objects)

    @staticmethod
    def search_filter(queryset, name: str, value: str):
        return queryset.filter(Q(header__icontains=value) | Q(text__icontains=value))

    @property
    def applied_filters_count_taks(self):
        """
        Считаем только те параметры, которые не в списке `not_count_params` и имеют значение
        :return:  int
        """
        not_count_params = ["show_my_tasks_only", "sort_order", "page", "show_active_task", "show_done_task",
                            "per_page"]

        applied_params = [param for key, param in self.data.items() if param and key not in not_count_params]

        # Количество примененных фильтров
        params_count = len(applied_params)

        # Проверяем наличие completion_time_after и completion_time_before и учитываем их как один фильтр
        if self.data.get("completion_time_after") and self.data.get("completion_time_before"):
            params_count -= 1

        return params_count


def applied_filters_count(request):
    """
    Считаем только те параметры, которые не в списке `not_count_params` и имеют значение
    :return:  int
    """
    not_count_params = ["page", "per_page"]
    return len([
        param for param, value in request.GET.items()
        if value and param not in not_count_params
    ])


def filter_url(request):
    """
    Формируем строку URL с параметрами, исключая параметры из `exclude_params`
    """
    filter_data = {key: value for key, value in request.GET.items() if key not in ["page"]}
    return urlencode(filter_data, doseq=True)


class TaskFilterByDone(django_filters.FilterSet):
    show_active_task = django_filters.BooleanFilter(method="filter_tasks")
    show_done_task = django_filters.BooleanFilter(method="filter_tasks")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.data = self.data.copy()
        # Принудительно устанавливаем show_active_task в True, если оно None
        if self.data.get("show_active_task") is None:
            self.data["show_active_task"] = "true"

        # Принудительно устанавливаем show_done_task в False, если оно None
        if self.data.get("show_done_task") is None:
            self.data["show_done_task"] = "false"

    def filter_tasks(self, queryset, name: str, value: bool):
        show_active = self.data.get("show_active_task") == "true"
        show_done = self.data.get("show_done_task") == "true"

        if show_active and show_done:
            # Показываем и активные, и завершённые задачи
            return queryset.filter(is_done__in=[False, True])
        elif show_active:
            # Показываем только активные задачи
            return queryset.filter(is_done=False)
        elif show_done:
            # Показываем только завершённые задачи
            return queryset.filter(is_done=True)

        # Если никакие фильтры не применены, возвращаем пустой queryset
        return queryset.none()
