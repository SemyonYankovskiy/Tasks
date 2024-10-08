# Generated by Django 5.1.1 on 2024-09-25 08:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tasks", "0011_alter_task_options_task_create_time_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="engineer",
            name="head_of_department",
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name="engineer",
            name="position",
            field=models.CharField(blank=True, max_length=256, null=True),
        ),
    ]
