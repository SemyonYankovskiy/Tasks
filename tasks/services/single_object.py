from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.transaction import atomic
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse

from tasks.forms import ObjectForm
from tasks.models import Object, AttachedFile
from .service import remove_unused_attached_files
from .tasks_actions import create_tags


@login_required
@atomic
def edit_object(request, slug):
    # Получаем объект по slug
    obj = get_object_or_404(Object, slug=slug)

    # Определяем путь для редиректа по умолчанию
    redirect_to = reverse("home")

    if request.method == "POST":

        post_data = create_tags(request.POST, "obj_tags_edit")  # Сохраняем теги и возвращаем
        form = ObjectForm(post_data, request.FILES, instance=obj)

        if form.is_valid():

            updated_object = form.save()  # Сохраняем изменения в объекте

            # Удаляем неиспользуемые прикрепленные файлы
            remove_unused_attached_files(request.POST.get("fileuploader-list-files"), updated_object)

            # Обработка прикрепленных файлов
            for file in request.FILES.getlist("files[]"):
                updated_object.files.add(AttachedFile.objects.create(file=file))
            updated_object.save()

            messages.add_message(request, messages.SUCCESS, f"Объект '{updated_object.name}' отредактирован")

            redirect_to = reverse("show-object", kwargs={"object_slug": updated_object.slug})

        else:
            messages.add_message(request, messages.WARNING, form.errors)

    return redirect(redirect_to)