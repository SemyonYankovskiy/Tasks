# Generated by Django 5.1.1 on 2024-09-23 10:05

import datetime

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tasks", "0010_departament_alter_task_engineers_and_more"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="task",
            options={"ordering": ["create_time"]},
        ),
        migrations.AddField(
            model_name="task",
            name="create_time",
            field=models.DateTimeField(
                auto_now_add=True,
                default=datetime.datetime(2024, 9, 23, 13, 5, 17, 730075),
                verbose_name="Created At",
            ),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="task",
            name="departments",
            field=models.ManyToManyField(
                blank=True,
                db_table="tasks_departments_m2m",
                related_name="tasks",
                to="tasks.departament",
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
    ]