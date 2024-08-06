import re
import uuid

from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator, MinValueValidator
from django.db import models


class UserObjectGroup(models.Model):
    user = models.ForeignKey(get_user_model(), on_delete = models.CASCADE)
    group = models.ForeignKey("ObjectGroup", on_delete=models.CASCADE)
    class Permission(models.TextChoices):
        R = 'R', "Чтение"
        W = 'W', "Запись"
    permission = models.CharField(choices=Permission.choices, max_length=10)
    class Meta:
        db_table = "users_objects_groups"

class ObjectGroup(models.Model):
    name = models.CharField(max_length=128)
    users = models.ManyToManyField(get_user_model(), related_name="object_groups", through=UserObjectGroup)
    class Meta:
        db_table = "objects_groups"


class Object(models.Model):
    class Priority(models.TextChoices):
        CRITICAL = 'CRITICAL', "Критический"
        HIGH = 'HIGH', "Высокий"
        MEDIUM = 'MEDIUM', "Средний"
        LOW = "LOW", "Низкий"
    priority = models.CharField(choices=Priority.choices, max_length=10)
    name = models.CharField(max_length=64)
    address = models.ForeignKey("Address", on_delete = models.CASCADE)
    description = models.TextField()
    tasks = models.ManyToManyField("Task", related_name="objects")
    tags = models.ManyToManyField("Tag", related_name="objects")
    files = models.ManyToManyField("AttachedFile", related_name="objects")
    groups = models.ManyToManyField("ObjectGroup", related_name="objects")
    class Meta:
        db_table = "objects"


class Task(models.Model):
    class Priority(models.TextChoices):
        CRITICAL = 'CRITICAL', "Критический"
        HIGH = 'HIGH', "Высокий"
        MEDIUM = 'MEDIUM', "Средний"
        LOW = "LOW", "Низкий"
    priority = models.CharField(choices=Priority.choices, max_length=10)
    is_done = models.BooleanField()
    completion_time = models.DateTimeField()
    header = models.CharField(max_length=128)
    text = models.TextField()
    engineers = models.ManyToManyField("Engineer", related_name="tasks")
    tags = models.ManyToManyField("Tag", related_name="tasks")
    files = models.ManyToManyField("AttachedFile", related_name="tasks")
    class Meta:
        db_table = "objects_tasks"

class Tag(models.Model):
    tag_name = models.CharField(max_length=64)
    class Meta:
        db_table = "tags"

class Engineer(models.Model):
    first_name = models.CharField(max_length=128)
    second_name = models.CharField(max_length=128)
    position = models.CharField(max_length=256)
    user = models.OneToOneField(get_user_model(), on_delete=models.CASCADE, null=True)

    class Meta:
        db_table = "engineers"

def upload_directory_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/user_<id>/<filename>
    return f"uploads/%Y/%m/%d/{uuid.uuid4()}_{filename}"


class AttachedFile(models.Model):
    file = models.FileField(upload_to=upload_directory_path, max_length=254)
    class Meta:
        db_table = "attached_files"


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
    )
    floor = models.SmallIntegerField(
        verbose_name="Этаж",
        null=True,
    )
    apartment = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1)],
        verbose_name="Кабинет",
        null=True,
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

