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
        # Получаем список всех значений параметра engineers
        values = self.data.getlist('engineers')

        if not values:
            return queryset  # Если значений нет, возвращаем исходный queryset

        # Создаем Q объект для фильтрации по нескольким значениям
        q_objects = Q()

        # Проходим по каждому значению и добавляем условия в Q объект
        for val in values:
            type_id = val.split("_")
            type = type_id[0]
            id = int(type_id[1])

            if type == "eng":
                # Фильтрация по конкретному инженеру через поле 'engineers'
                q_objects |= Q(engineers__id=id)
            elif type == "dep":
                # Фильтрация по департаменту через связь с инженером
                q_objects |= Q(engineers__departament__id=id)

        # Применяем фильтрацию с помощью Q объекта
        return queryset.filter(q_objects)

    def search_filter(self, queryset, header: str, value: str):
        return queryset.filter(Q(header__icontains=value) | Q(text__icontains=value))
