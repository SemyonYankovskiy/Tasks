import os
import re
import uuid
from datetime import datetime

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator, MinValueValidator
from django.db import models


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
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="children"
    )
    name = models.CharField(max_length=64)
    address = models.ForeignKey("Address", on_delete=models.CASCADE)
    description = models.TextField(blank=True)
    tasks = models.ManyToManyField(
        "Task", related_name="objects_set", db_table="objects_tasks_m2m", blank=True
    )
    tags = models.ManyToManyField("Tag", related_name="objects_set", db_table="objects_tags_m2m", blank=True)
    files = models.ManyToManyField(
        "AttachedFile", related_name="objects_set", db_table="objects_files_m2m", blank=True
    )
    groups = models.ManyToManyField("ObjectGroup", related_name="objects_set", db_table="objects_groups_m2m")
    slug = models.SlugField(max_length=255, unique=True, db_index=True)

    class Meta:
        db_table = "objects"

    def __str__(self):
        return self.name

    def clean(self):
        # Check if the object is trying to set itself as a parent
        if self.parent == self:
            raise ValidationError("Сходи нахер со своей рекурсией")

        # Check if the parent object is trying to set itself as a parent
        if self.parent:
            # Initialize a variable to store the current parent
            current_parent = self.parent

            # Loop through the parents to check if self is already on the chain
            while current_parent:
                if current_parent == self:
                    raise ValidationError(
                        "ВИЧ-инфекция в дереве наследования объектов. Твой выбранный родитель это твой же потомок, инцест осуждаем"
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
    completion_time = models.DateTimeField()
    header = models.CharField(max_length=128)
    text = models.TextField(blank=True)
    engineers = models.ManyToManyField(
        "Engineer", related_name="tasks", db_table="tasks_engineers_m2m", blank=True
    )
    tags = models.ManyToManyField("Tag", related_name="tasks", db_table="tasks_tags_m2m", blank=True)
    files = models.ManyToManyField(
        "AttachedFile", related_name="tasks", db_table="tasks_files_m2m", blank=True
    )

    # slug = models.SlugField(max_length=255, unique=True, db_index=True, verbose_name="URL")

    class Meta:
        db_table = "object_tasks"

    def __str__(self):
        return self.header


class Tag(models.Model):
    tag_name = models.CharField(max_length=64)

    class Meta:
        db_table = "tags"

    def __str__(self):
        return self.tag_name


class Engineer(models.Model):
    first_name = models.CharField(max_length=128)
    second_name = models.CharField(max_length=128)
    position = models.CharField(max_length=256)
    user = models.OneToOneField(get_user_model(), on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        db_table = "engineers"

    def __str__(self):
        return f"{self.first_name} {self.second_name}"


def upload_directory_path(instance, filename):
    # файл будет загружен в MEDIA_ROOT/user_<id>/<filename>
    current_date = datetime.now()
    return f"uploads/{current_date.year}/{current_date.month}/{current_date.day}/{uuid.uuid4()}_._{filename}"


class AttachedFile(models.Model):
    file = models.FileField(upload_to=upload_directory_path, max_length=254)
    extension = models.CharField(max_length=10, blank=True)  # Поле для хранения расширения файла

    class Meta:
        db_table = "attached_files"

    def __str__(self):
        return self.file.name

    def is_image(self) -> bool:
        return self.extension in [".jpeg", ".jpg", ".png"]

    def save(self, *args, **kwargs):
        if self.file:
            # Определение расширения файла
            _, file_extension = os.path.splitext(self.file.name)
            self.extension = file_extension.lower()  # Приведение расширения к нижнему регистру
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
