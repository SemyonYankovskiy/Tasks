import django_filters
from .models import Object

class ObjectFilter(django_filters.FilterSet):
    class Meta:
        model = Object
        fields = {
            'name': ['icontains'],
            'tags': ['exact'],
            'groups': ['exact'],
            'priority': ['exact'],
        }