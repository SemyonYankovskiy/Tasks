import random
import string

from tasks.models import Notification


class RandomString:

    def __str__(self):
        text = ""
        for i in range(8):
            text += random.choices(string.ascii_lowercase)[0]
        print(text)
        return text


def random_string(request):
    return {"random_str": RandomString()}


def ascii_letters(request):
    return {
        "ascii_lowercase": string.ascii_lowercase,
        "ascii_uppercase": string.ascii_uppercase,
    }


def notifications_processor(request):
    if request.user.is_authenticated:
        return {'notifications': Notification.objects.filter(user=request.user, is_read=False)}
    return {}
