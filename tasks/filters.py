import django_filters
from django.db.models import Q

from .models import Object, Task


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

    class Meta:
        model = Task
        fields = ["search", "tags", "engineers", "priority", "objects_set"]

    def dep_to_engineers(self, queryset, header: str, value: str):
        print(value)

        type_id = value.split("_")
        type = type_id[0]
        id = int(type_id[1])

        if type == "eng":
            # Фильтрация по конкретному инженеру через поле 'engineer'
            return queryset.filter(engineers__id=id)
        elif type == "dep":
            # Фильтрация по департаменту через связь с инженером
            return queryset.filter(engineers__departament__id=id)
        else:
            # Если значение не соответствует ожидаемым типам, возвращаем исходный queryset
            return queryset

    def search_filter(self, queryset, header: str, value: str):
        return queryset.filter(Q(header__icontains=value) | Q(text__icontains=value))
