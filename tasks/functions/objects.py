from django.contrib.auth.decorators import login_required
from django.db.models import Count, OuterRef, Subquery, Case, When, Value, CharField, QuerySet
from django.db.models.functions import Concat, Substr, Length
from django.db.transaction import atomic

from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.urls import reverse
from tasks.models import Object, AttachedFile
from user.models import User
from .tasks_actions import create_tags
from .tasks_prepare import permission_filter
from ..forms import ObjectForm
from ..services.tree_nodes import GroupsTree


def get_objects_list(request) -> QuerySet[Object]:
    """
    Создает запрос к базе данных для получения объектов и добавляет дополнительные поля
    через аннотации и подзапросы, такие, как превью изображения, количество дочерних объектов и задач.
    """

    # Подзапрос для получения первого файла изображения (jpeg, jpg, png) для каждого объекта
    image_subquery = (
        AttachedFile.objects.filter(objects_set=OuterRef("pk"), file__iregex=r"\.(jpeg|jpg|png)$")
        .order_by("id")  # Сортировка по идентификатору файла (чтобы выбрать первый по порядку)
        .values("file")[:1]  # Получение только первого файла (поле 'file')
    )

    # Основной запрос для получения списка объектов
    objects = (
        Object.objects.all()  # Получаем все объекты из базы данных
        .prefetch_related("tags", "groups")  # Предзагрузка связанных тегов и групп для оптимизации запросов
        .filter(groups__users=request.user)  # Фильтрация объектов по пользователю, который связан с группой
        .annotate(
            img_preview=Subquery(image_subquery),  # Добавляем превью изображения как подзапрос
            child_count=Count("children", distinct=True),  # Подсчет уникальных дочерних объектов
            description_length=Length("description"),  # Подсчет длины описания объекта
            # tasks_count=Count('tasks', filter=Q(tasks__is_done=False), distinct=True),  # Подсчет активных задач
            short_description=Case(
                # Если длина описания больше 53 символов, обрезаем до 50 символов и добавляем "..."
                When(description_length__gt=53, then=Concat(Substr("description", 1, 50), Value("..."))),
                default="description",  # Если описание короче 53 символов, выводим его полностью
                output_field=CharField(),  # Поле с текстовым выводом
            ),
        )
        .only("id", "name", "priority", "slug", "zabbix_link", "notes_link", "ecstasy_link",
              "another_link")  # Ограничиваем выборку только нужными полями для оптимизации
        .distinct()  # Убираем дублирующиеся объекты (если были)
        .order_by("parent_id", "-id")  # Сортировка по полю `parent_id`, затем по убыванию `id`
    )
    return objects  # Возвращаем список объектов с аннотациями


def add_tasks_count_to_objects(queryset: QuerySet[Object], user: User, field_name: str) -> QuerySet[Object]:
    for obj in queryset:
        count: int = permission_filter(user).filter(objects_set=obj, is_done=False).count()
        setattr(obj, field_name, count)

    return queryset


@login_required
@atomic
def edit_object(request, slug):
    # Получаем объект по slug
    obj = get_object_or_404(Object, slug=slug)

    redirect_to = reverse("home")  # Путь к редиректу после редактирования
    print("1", redirect_to)
    if request.method == "POST":

        post_data = create_tags(request.POST, "obj_tags_edit")  # Сохраняем теги и возвращаем

        # Создаём форму с данными из POST-запроса
        form = ObjectForm(post_data, request.FILES, instance=obj)

        if form.is_valid():
            updated_object = form.save()  # Сохраняем изменения в объекте
            messages.add_message(request, messages.SUCCESS, f"Объект '{updated_object.name}' отредактирован")
        else:
            messages.add_message(request, messages.WARNING, form.errors)

    return redirect(redirect_to)

