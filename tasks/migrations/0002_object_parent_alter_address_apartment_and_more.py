# Generated by Django 4.2.14 on 2024-08-06 12:25

import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tasks", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="object",
            name="parent",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="tasks.object",
            ),
        ),
        migrations.AlterField(
            model_name="address",
            name="apartment",
            field=models.PositiveSmallIntegerField(
                blank=True,
                null=True,
                validators=[django.core.validators.MinValueValidator(1)],
                verbose_name="Кабинет",
            ),
        ),
        migrations.AlterField(
            model_name="address",
            name="block",
            field=models.PositiveSmallIntegerField(
                blank=True,
                null=True,
                validators=[django.core.validators.MinValueValidator(1)],
                verbose_name="Корпус",
            ),
        ),
        migrations.AlterField(
            model_name="address",
            name="floor",
            field=models.SmallIntegerField(blank=True, null=True, verbose_name="Этаж"),
        ),
        migrations.AlterField(
            model_name="object",
            name="files",
            field=models.ManyToManyField(
                blank=True,
                db_table="objects_files_m2m",
                related_name="objects",
                to="tasks.attachedfile",
            ),
        ),
        migrations.AlterField(
            model_name="object",
            name="tags",
            field=models.ManyToManyField(
                blank=True,
                db_table="objects_tags_m2m",
                related_name="objects",
                to="tasks.tag",
            ),
        ),
        migrations.AlterField(
            model_name="object",
            name="tasks",
            field=models.ManyToManyField(
                blank=True,
                db_table="objects_tasks_m2m",
                related_name="objects",
                to="tasks.task",
            ),
        ),
        migrations.AlterField(
            model_name="task",
            name="engineers",
            field=models.ManyToManyField(
                blank=True,
                db_table="tasks_engineers_m2m",
                related_name="tasks",
                to="tasks.engineer",
            ),
        ),
        migrations.AlterField(
            model_name="task",
            name="files",
            field=models.ManyToManyField(
                blank=True,
                db_table="tasks_files_m2m",
                related_name="tasks",
                to="tasks.attachedfile",
            ),
        ),
        migrations.AlterField(
            model_name="task",
            name="tags",
            field=models.ManyToManyField(
                blank=True,
                db_table="tasks_tags_m2m",
                related_name="tasks",
                to="tasks.tag",
            ),
        ),
    ]
