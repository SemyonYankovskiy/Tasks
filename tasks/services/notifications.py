
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404

from tasks.models import Notification


@login_required
def mark_notifications_as_read(request):
    request.user.notifications.update(is_read = True)
    return JsonResponse({'status': 'ok'})


@login_required
def mark_one_notifications_as_read(request, notification_id):

    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    print(notification)
    notification.is_read = True
    notification.save()
    return JsonResponse({"status": "ok"})