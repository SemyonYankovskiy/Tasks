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
    completion_time_after = django_filters.DateFilter(field_name='completion_time', lookup_expr='date__gte', label='От')
    completion_time_before = django_filters.DateFilter(field_name='completion_time', lookup_expr='date__lte',
                                                       label='До')

    class Meta:
        model = Task
        fields = ["search", "tags", "engineers", "priority", "objects_set", "completion_time_after",
                  "completion_time_before"]

    def dep_to_engineers(self, queryset, header: str, value: str):
        values = self.data.getlist('engineers')

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
                q_objects |= Q(engineers__departament__id=id)

        return queryset.filter(q_objects)

    def search_filter(self, queryset, header: str, value: str):
        return queryset.filter(Q(header__icontains=value) | Q(text__icontains=value))
