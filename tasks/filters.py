import django_filters

from .models import Object


class ObjectFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr="icontains")

    class Meta:
        model = Object
        fields = ['name', 'tags', 'groups', 'priority']
