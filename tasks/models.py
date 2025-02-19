import os
import re
import uuid
from datetime import datetime

from ckeditor_uploader.fields import RichTextUploadingField
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator, MinValueValidator
from django.db import models
from django.db.models.signals import post_save, post_delete, m2m_changed
from django.dispatch import receiver

from tasks.services.cache_version import CacheVersion


class UserObjectGroup(models.Model):
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    group = models.ForeignKey("ObjectGroup", on_delete=models.CASCADE)

    class Permission(models.TextChoices):
        R = "R", "Только чтение"
        W = "RW", "Чтение/Запись"

    permission = models.CharField(choices=Permission.choices, max_length=10)

    class Meta:
        db_table = "users_objects_groups_m2m"

    def __str__(self):
        return f"{self.user}-{self.group}-{self.permission}"


class ObjectGroup(models.Model):
    name = models.CharField(max_length=128, unique=True)
    users = models.ManyToManyField(get_user_model(), related_name="object_groups", through=UserObjectGroup)

    class Meta:
        db_table = "object_groups"

    def __str__(self):
        return self.name


class Object(models.Model):
    class Priority(models.TextChoices):
        CRITICAL = "CRITICAL", "Критический"
        HIGH = "HIGH", "Высокий"
        MEDIUM = "MEDIUM", "Средний"
        LOW = "LOW", "Низкий"

    priority = models.CharField(choices=Priority.choices, max_length=10)
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="children")
    name = models.CharField(max_length=64)
    address = models.ForeignKey("Address", on_delete=models.CASCADE, blank=True, null=True)
    description = RichTextUploadingField(blank=True)
    zabbix_link = models.CharField(max_length=256, blank=True)
    ecstasy_link = models.CharField(max_length=256, blank=True)
    notes_link = models.CharField(max_length=256, blank=True)
    another_link = models.CharField(max_length=256, blank=True)
    tasks = models.ManyToManyField("Task", related_name="objects_set", db_table="objects_tasks_m2m", blank=True)
    tags = models.ManyToManyField("Tag", related_name="objects_set", db_table="objects_tags_m2m", blank=True)
    files = models.ManyToManyField("AttachedFile", related_name="objects_set", db_table="objects_files_m2m", blank=True)
    groups = models.ManyToManyField("ObjectGroup", related_name="objects_set", db_table="objects_groups_m2m")
    slug = models.SlugField(max_length=255, unique=True, db_index=True)

    class Meta:
        db_table = "objects"

    def __str__(self):
        return self.name

    def clean(self):
        # Check if the object is trying to set itself as a parent
        if self.parent == self:
            raise ValidationError("Рекурсия")

        # Check if the parent object is trying to set itself as a parent
        if self.parent:
            # Initialize a variable to store the current parent
            current_parent = self.parent

            # Loop through the parents to check if self is already on the chain
            while current_parent:
                if current_parent == self:
                    raise ValidationError(
                        "Твой выбранный родитель это твой же потомок, осуждаем"
                    )
                # Move up the chain
                current_parent = current_parent.parent


class Task(models.Model):
    class Priority(models.TextChoices):
        CRITICAL = "CRITICAL", "Критический"
        HIGH = "HIGH", "Высокий"
        MEDIUM = "MEDIUM", "Средний"
        LOW = "LOW", "Низкий"

    priority = models.CharField(choices=Priority.choices, max_length=10)
    is_done = models.BooleanField()
    deleted = models.BooleanField()
    completion_time = models.DateTimeField()
    create_time = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    header = models.CharField(max_length=128)
    text = RichTextUploadingField(blank=True)
    completion_text = RichTextUploadingField(blank=True)
    engineers = models.ManyToManyField("Engineer", related_name="tasks", db_table="tasks_engineers_m2m", blank=True)
    departments = models.ManyToManyField("Department", related_name="tasks", db_table="tasks_departments_m2m", blank=True)
    tags = models.ManyToManyField("Tag", related_name="tasks", db_table="tasks_tags_m2m", blank=True)
    files = models.ManyToManyField("AttachedFile", related_name="tasks", db_table="tasks_files_m2m", blank=True)
    creator = models.ForeignKey(get_user_model(), related_name="created_tasks", on_delete=models.PROTECT)
    status_changed_by = models.CharField(max_length=32, blank=True, null=True)

    # slug = models.SlugField(max_length=255, unique=True, db_index=True, verbose_name="URL")

    class Meta:
        db_table = "object_tasks"
        ordering = ["create_time"]

    def __str__(self):
        return self.header

    def save(self, *args, **kwargs):
        # Проверяем, существовала ли задача ранее
        is_new = self.pk is None
        previous = None
        if not is_new:
            previous = Task.objects.filter(pk=self.pk).first()

        # Вызываем стандартное сохранение
        super().save(*args, **kwargs)

        # Определяем контекст изменения
        if is_new:
            self.status_changed_by = "create"
        elif previous and previous.is_done and not self.is_done:
            self.status_changed_by = "restore"
        else:
            self.status_changed_by = "edit"

        # Дополнительное сохранение, если статус изменился
        super().save(update_fields=["status_changed_by"])


class Notification(models.Model):
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, related_name="notifications")
    message = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)  # Флаг для прочитанных уведомлений

    def str(self):
        return f"{self.user} - {self.message}"


class Comment(models.Model):
    task = models.ForeignKey(Task, related_name="comments", on_delete=models.CASCADE)
    author = models.ForeignKey(get_user_model(), related_name="comments", on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment {self.task.header} by {self.author} on {self.created_at}"


class Tag(models.Model):
    tag_name = models.CharField(max_length=64, unique=True)

    class Meta:
        db_table = "tags"

    def __str__(self):
        return self.tag_name


class Engineer(models.Model):
    first_name = models.CharField(max_length=128)
    second_name = models.CharField(max_length=128)
    position = models.CharField(max_length=256, null=True, blank=True)
    user = models.OneToOneField(get_user_model(), on_delete=models.CASCADE, null=True, blank=True)
    department = models.ForeignKey(
        "Department", null=True, blank=True, on_delete=models.SET_NULL, related_name="engineers"
    )
    head_of_department = models.BooleanField(default=False)

    class Meta:
        db_table = "engineers"

    def __str__(self):
        return f"{self.first_name} {self.second_name}"


class Department(models.Model):
    name = models.CharField(max_length=128)

    class Meta:
        db_table = "departments"

    def __str__(self):
        return self.name


def upload_directory_path(instance, filename):
    # файл будет загружен в MEDIA_ROOT/user_<id>/<filename>
    current_date = datetime.now()
    return f"uploads/{current_date.year}/{current_date.month:>02}/{current_date.day:>02}/{uuid.uuid4()}_._{filename}"


class AttachedFile(models.Model):
    file = models.FileField(upload_to=upload_directory_path, max_length=254)
    extension = models.CharField(max_length=10, blank=True)  # Поле для хранения расширения файла
    is_image = models.BooleanField(default=False)  # Новое поле для указания, является ли файл изображением

    class Meta:
        db_table = "attached_files"

    def str(self):
        return self.file.name

    def clear_file_name(self):
        """
        Возвращает оригинальное имя файла без UUID, '._' и расширения.
        """
        # Получаем базовое имя файла (без пути)
        base_name = os.path.basename(self.file.name)

        # Удаляем UUID и "._" из имени файла
        parts = base_name.split("_._")

        # Если есть хотя бы один элемент после split, берём последний
        if parts:
            original_name = parts[-1]

            # Если у файла есть расширение, убираем его
            if "." in original_name:
                original_name = os.path.splitext(original_name)[0]

            return original_name  # Возвращаем только имя без расширения
        return ""  # Если split не сработал

    def save(self, *args, **kwargs):
        if self.file:
            # Получаем базовое имя файла
            base_name = os.path.basename(self.file.name)

            # Проверяем, является ли файл скрытым (например, .env)
            if base_name.startswith(".") and base_name.count(".") == 1:
                self.extension = base_name  # Для .env расширение будет .env
            else:
                # Используем splitext() для корректного извлечения расширения
                _, file_extension = os.path.splitext(base_name)
                self.extension = file_extension.lower() if file_extension else ""

            # Установка поля is_image на основе расширения
            self.is_image = self.extension in [".jpeg", ".jpg", ".png"]

        super().save(*args, **kwargs)





class Address(models.Model):
    region = models.CharField(
        max_length=128,
        verbose_name="Регион",
        default="Севастополь",
    )
    settlement = models.CharField(
        max_length=128,
        verbose_name="Населенный пункт",
        help_text="Любимовка, Верхнесадовое",
        default="Севастополь",
    )
    plan_structure = models.CharField(
        max_length=128,
        verbose_name="ТСН СНТ, СТ",
        help_text="Рыбак-7",
        null=True,
        blank=True,
    )
    street = models.CharField(
        max_length=128,
        verbose_name="Улица",
        help_text="Полное название с указанием типа (улица/проспект/проезд/бульвар/шоссе/переулок/тупик)",
        null=True,
        blank=True,
    )
    house = models.CharField(
        max_length=16,
        validators=[RegexValidator(r"^\d+[а-яА-Я]?$", message="Неверный формат дома")],
        verbose_name="Дом",
        help_text="Можно с буквой (русской)",
    )
    block = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1)],
        verbose_name="Корпус",
        null=True,
        blank=True,
    )
    floor = models.SmallIntegerField(
        verbose_name="Этаж",
        null=True,
        blank=True,
    )
    apartment = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1)],
        verbose_name="Кабинет",
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "gpon_addresses"

    @property
    def verbose(self) -> str:
        string = ""
        if self.region != "СЕВАСТОПОЛЬ":
            string += f"{self.region.lower()}, "
        if self.settlement != "СЕВАСТОПОЛЬ":
            string += f"{self.settlement.lower()}, "
        if self.plan_structure and len(self.plan_structure):
            string += f"СНТ {self.plan_structure.title()}, "
        if self.street and len(self.street):
            street = re.sub(
                r"Улица|Проспект|площадь|Проезд|Бульвар|Шоссе|Переулок|Тупик",
                lambda x: x.group(0).lower(),
                self.street.title(),
            )
            string += f"{street}, "
        string += f"д. {self.house}"
        if self.block:
            string += f"/{self.block}"

        if self.floor:
            string += f" {self.floor} этаж"
        if self.apartment:
            string += f" кв. {self.apartment}"
        return string

    def __str__(self):
        return self.verbose

    def __repr__(self):
        return f"Address: ({self.__str__()})"


# --- Task ---
@receiver(post_save, sender=Task)
def update_cache_version1_save(sender, created, **kwargs):
    CacheVersion("tasks_page_version_cache").increment_cache_version()
    CacheVersion("objects_page_cache_version").increment_cache_version()


@receiver(post_delete, sender=Task)
def update_cache_version1_delete(sender, instance, **kwargs):
    CacheVersion("tasks_page_version_cache").increment_cache_version()
    CacheVersion("objects_page_cache_version").increment_cache_version()


# --- Object ---
@receiver(post_save, sender=Object)
def update_cache_version2_save(sender, created, **kwargs):
    CacheVersion("objects_page_cache_version").increment_cache_version()
    CacheVersion("filter_components_cache_version_tasks").increment_cache_version()


@receiver(post_delete, sender=Object)
def update_cache_version2_delete(sender, instance, **kwargs):
    CacheVersion("objects_page_cache_version").increment_cache_version()
    CacheVersion("filter_components_cache_version_tasks").increment_cache_version()


# --- Tag ---
@receiver(post_save, sender=Tag)
def update_cache_version3_save(sender, created, **kwargs):
    CacheVersion("filter_components_cache_version_objects").increment_cache_version()
    CacheVersion("filter_components_cache_version_tasks").increment_cache_version()


@receiver(post_delete, sender=Tag)
def update_cache_version3_delete(sender, instance, **kwargs):
    CacheVersion("filter_components_cache_version_objects").increment_cache_version()
    CacheVersion("filter_components_cache_version_tasks").increment_cache_version()


# --- ObjectGroup ---
@receiver(post_save, sender=ObjectGroup)
def update_cache_version4_save(sender, created, **kwargs):
    CacheVersion("filter_components_cache_version_objects").increment_cache_version()


@receiver(post_delete, sender=ObjectGroup)
def update_cache_version4_delete(sender, instance, **kwargs):
    CacheVersion("filter_components_cache_version_objects").increment_cache_version()


# --- Engineer ---
@receiver(post_save, sender=Engineer)
def update_cache_version5_save(sender, created, **kwargs):
    CacheVersion("filter_components_cache_version_tasks").increment_cache_version()


@receiver(post_delete, sender=Engineer)
def update_cache_version5_delete(sender, instance, **kwargs):
    CacheVersion("filter_components_cache_version_tasks").increment_cache_version()


# --- Department ---
@receiver(post_save, sender=Department)
def update_cache_version6_save(sender, created, **kwargs):
    CacheVersion("filter_components_cache_version_tasks").increment_cache_version()


@receiver(post_delete, sender=Department)
def update_cache_version6_delete(sender, instance, **kwargs):
    CacheVersion("filter_components_cache_version_tasks").increment_cache_version()


# --- Comments ---
@receiver(post_save, sender=Comment)
def update_cache_version7_save(sender, created, **kwargs):
    CacheVersion("tasks_page_version_cache").increment_cache_version()
    CacheVersion("objects_page_cache_version").increment_cache_version()


@receiver(post_delete, sender=Comment)
def update_cache_version7_delete(sender, instance, **kwargs):
    CacheVersion("tasks_page_version_cache").increment_cache_version()
    CacheVersion("objects_page_cache_version").increment_cache_version()


@receiver(m2m_changed, sender=Task.engineers.through)
def notify_assigned_engineers(sender, instance, action, **kwargs):
    """Создаёт уведомления для инженеров, назначенных на задачу"""
    if action in ["post_add"]:  # Если инженеры добавлены в задачу
        for engineer in instance.engineers.all():
            if engineer.user:  # Проверяем, есть ли у инженера связанный пользователь
                Notification.objects.create(
                    user=engineer.user,
                    message=f"{datetime.now().strftime('%H:%M')} | Вам назначена  задача: '{instance.header}'"
                )

@receiver(m2m_changed, sender=Task.departments.through)
def notify_department_engineers(sender, instance, action, **kwargs):
    """Создаёт уведомления для всех инженеров департамента, на который назначена задача"""
    if action in ["post_add"]:  # Если департамент добавлен в задачу
        for department in instance.departments.all():
            for engineer in department.engineers.all():
                if engineer.user:
                    Notification.objects.create(
                        user=engineer.user,
                        message=f"{datetime.now().strftime('%H:%M')} | Вашему отделу назначена  задача: '{instance.header}'"
                    )



@receiver(post_save, sender=Task)
def notify_task_status_change(sender, instance, created, **kwargs):
    """Создаёт уведомления при изменении статуса задачи"""
    if created:
        return  # Не уведомляем при создании

    message = None

    # Уведомление о закрытии задачи
    if instance.is_done:
        message = f"{datetime.now().strftime('%H:%M')} | Задача '{instance.header}' была выполнена."
        # Уведомление для создателя задачи
        if instance.creator:
            if not Notification.objects.filter(user=instance.creator, message=message).exists():
                Notification.objects.create(user=instance.creator,message=f"{datetime.now().strftime('%H:%M')} | Задача '{instance.header}' была выполнена."
                )
    elif instance.deleted:
        message = f"{datetime.now().strftime('%H:%M')} | Задача '{instance.header}' была удалена."
    elif instance.status_changed_by == "restore":
        message = f"{datetime.now().strftime('%H:%M')} | Задача '{instance.header}' была возвращена в работу."
        # Уведомление для создателя задачи
        if instance.creator:
            if not Notification.objects.filter(user=instance.creator, message=message).exists():
                Notification.objects.create(user=instance.creator,
                                            message=f"{datetime.now().strftime('%H:%M')} | Задача '{instance.header}' была возвращена в работу."
                                            )
    if message:
        for engineer in instance.engineers.all():
            if engineer.user:
                # Проверяем, есть ли уже такое уведомление
                if not Notification.objects.filter(user=engineer.user, message=message).exists():
                    Notification.objects.create(user=engineer.user, message=message)


@receiver(m2m_changed, sender=Task.engineers.through)
def notify_removed_engineers(sender, instance, action, pk_set, **kwargs):
    """
    Уведомляет инженера, если его убрали из задачи.
    pk_set содержит ID удалённых инженеров.
    """
    if action == "post_remove":  # Если кого-то удалили из исполнителей
        for engineer_id in pk_set:
            engineer = Engineer.objects.filter(id=engineer_id).first()
            if engineer and engineer.user:
                Notification.objects.create(
                    user=engineer.user,
                    message=f"{datetime.now().strftime('%H:%M')} | Вы больше не являетесь исполнителем задачи '{instance.header}'."
                )


@receiver(post_save, sender=Comment)
def notify_task_creator_on_comment(sender, instance, created, **kwargs):
    """Создаёт уведомление для создателя задачи, когда добавлен новый комментарий"""
    if created:
        task = instance.task
        # Создаём уведомление для создателя задачи
        if task.creator and task.creator != instance.author:
            Notification.objects.create(
                user=task.creator,
                message=f"{datetime.now().strftime('%H:%M')} | {instance.author} добавил ответ к задаче '{task.header}'"
            )