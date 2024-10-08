# Generated by Django 4.2.14 on 2024-09-03 08:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tasks", "0007_remove_attachedfile_type_attachedfile_extension"),
    ]

    operations = [
        migrations.AlterField(
            model_name="objectgroup",
            name="name",
            field=models.CharField(max_length=128, unique=True),
        ),
        migrations.AlterField(
            model_name="task",
            name="text",
            field=models.TextField(blank=True),
        ),
    ]
