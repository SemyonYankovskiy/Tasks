import django_filters
from django.db.models import Q

from .models import Object, Task, Engineer


class ObjectFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(method="search_filter")

    class Meta:
        model = Object
        fields = ["search", "tags", "groups", "priority"]

    def search_filter(self, queryset, name: str, value: str):
        return queryset.filter(Q(name__icontains=value) | Q(description__icontains=value))


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
        # Принудительно устанавливаем show_active_task в True, если оно None
        if self.data.get("show_my_tasks_only") is None:
            self.data["show_my_tasks_only"] = "false"
        # Принудительно устанавливаем show_active_task в True, если оно None
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
        print("filter_show_my_tasks_only", name, value)

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
