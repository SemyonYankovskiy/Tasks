
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.db.models import Count, Q, F
from django.db.models import OuterRef, Subquery, Case, When, Value, CharField, QuerySet
from django.db.models.functions import Concat, Substr, Length
from django.db.transaction import atomic
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse

from tasks.forms import ObjectForm
from tasks.models import Object, AttachedFile
from .cache_version import CacheVersion
from .service import paginate_queryset
from .service import remove_unused_attached_files
from .tasks_actions import create_tags
from .tasks_prepare import permission_filter
from ..filters import ObjectFilter


def get_objects_list(user) -> QuerySet[Object]:
    # Подзапрос для получения первого файла изображения (jpeg, jpg, png) для каждого объекта
    image_subquery = (
        AttachedFile.objects.filter(objects_set=OuterRef("pk"), file__iregex=r"\.(jpeg|jpg|png)$")
        .order_by("id")
        .values("file")[:1]
    )

    tasks_count_subquery = (
        permission_filter(user)
        .filter(objects_set=OuterRef("pk"), is_done=False)
        .values("objects_set")
        .annotate(tasks_count=Count("id"))
        .values("tasks_count")[:1]
    )

    objects = (
        Object.objects.all()
        .prefetch_related("tags", "groups")
        .filter(groups__users=user)
        .annotate(
            img_preview=Subquery(image_subquery, output_field=CharField()),  # Используем подзапрос с одним значением
            child_count=Count("children", distinct=True),  # Подсчет уникальных дочерних объектов
            description_length=Length("description"),
            tasks_count=Subquery(tasks_count_subquery, output_field=CharField()),  # Используем подзапрос с одним значением
            short_description=Case(
                When(description_length__gt=53, then=Concat(Substr("description", 1, 50), Value("..."))),
                default="description",
                output_field=CharField(),
            ),
        )
        .only("id", "name", "priority", "slug", "zabbix_link", "notes_link", "ecstasy_link", "another_link")
        .distinct()
        .order_by("parent_id", "-id")
    )

    return objects


def get_objects(request, filter_params, page_number, per_page):
    """
    Возвращает список объектов. Если не применяются фильтры - возвращает объекты из кэша
    """
    cache_key = f'objects_page:{page_number}:{request.user}'

    version_cache_key = "objects_page_cache_version"
    cache_version = CacheVersion(version_cache_key)
    cache_version_value = cache_version.get_cache_version()

    cached_data = cache.get(cache_key, version=cache_version_value) if not filter_params else None

    if cached_data:
        return cached_data

    # Получение списка объектов и пагинирование
    filtered_objects = ObjectFilter(request.GET, queryset=get_objects_list(request.user)).qs
    pagination_data = paginate_queryset(filtered_objects, page_number, per_page)

    result = {
        "objects_qs": pagination_data["page_obj"],
        "pagination_data": pagination_data,
    }

    # Кэшируем результат, если отсутствуют фильтры
    if not filter_params:
        cache.set(cache_key, result, timeout=600, version=cache_version_value)

    return result


def get_obj(object_slug, user):

    obj = (
        Object.objects.filter(slug=object_slug)
            .prefetch_related("files", "tags", "groups")
            .annotate(
            parent_name=F("parent__name"),
            parent_slug=F("parent__slug"),
            done_tasks_count=Count("id", filter=Q(tasks__is_done=True)),
            undone_tasks_count=Count("id", filter=Q(tasks__is_done=False)),
        )
            .filter(groups__users=user)
            .first()
    )

    # Если объект не найден, выбрасываем исключение 404 (страница не найдена)
    if obj is None:
        raise Http404()

    if obj:
        # Получаем все связанные файлы
        attached_files = obj.files.all()

        # Разделяем файлы на изображения и не-изображения
        images = [file for file in attached_files if file.is_image]  # Используем поле is_image
        non_images = [file for file in attached_files if not file.is_image]  # Используем поле is_image
    else:
        images = []
        non_images = []

    return {
        "object": obj,
        "obj_images": images,
        "obj_files": non_images,
        "object_id_list": [obj.id],
    }


def get_single_object(user, object_slug):
    """
    Возвращает список объектов. Если не применяются фильтры - возвращает объекты из кэша
    """
    cache_key = f'single_obj_{object_slug}'
    cached_data = cache.get(cache_key)

    if cached_data:
        return cached_data

    obj = get_obj(object_slug, user)
    result = {**obj}
    cache.set(cache_key, result, timeout=600)

    return result


@login_required
@atomic
def edit_object(request, object_slug):
    # Получаем объект по slug
    obj = get_object_or_404(Object, slug=object_slug)

    # Определяем путь для редиректа по умолчанию
    redirect_to = reverse("home")

    if request.method == "POST":

        post_data = create_tags(request.POST, "obj_tags_edit")  # Сохраняем теги и возвращаем
        form = ObjectForm(post_data, request.FILES, instance=obj)

        if form.is_valid():

            updated_object = form.save(commit=False)  # Сохраняем изменения в объекте

            # Удаляем неиспользуемые прикрепленные файлы
            remove_unused_attached_files(request.POST.get("fileuploader-list-files"), updated_object)

            # Обработка прикрепленных файлов
            for file in request.FILES.getlist("files[]"):
                updated_object.files.add(AttachedFile.objects.create(file=file))
            updated_object.save()

            cache.delete(f'single_obj_{object_slug}')
            cache.delete(f'obj_{object_slug}_childs')

            messages.add_message(request, messages.SUCCESS, f"Объект '{updated_object.name}' отредактирован")

            redirect_to = reverse("show-object", kwargs={"object_slug": updated_object.slug})

        else:
            messages.add_message(request, messages.WARNING, form.errors)

    return redirect(redirect_to)


def get_child_objects(user, parent):
    """
    Возвращает список объектов. Если не применяются фильтры - возвращает объекты из кэша
    """

    cache_key = f'obj_{parent.slug}_childs'
    cached_data = cache.get(cache_key)
    if cached_data is not None:

        return cached_data

    result = get_objects_list(user).filter(parent=parent)


    cache.set(cache_key, result, timeout=600)

    return result
