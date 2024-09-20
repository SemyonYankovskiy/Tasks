import random

from django.template.library import Library

register = Library()


@register.filter(is_safe=True)
def shuffle_string(value):
    value_list = list(value)
    random.shuffle(value_list)
    return "".join(value_list)
