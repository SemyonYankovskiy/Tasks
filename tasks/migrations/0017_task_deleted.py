# Generated by Django 5.1.1 on 2024-11-11 06:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tasks", "0016_attachedfile_is_image"),
    ]

    operations = [
        migrations.AddField(
            model_name="task",
            name="deleted",
            field=models.BooleanField(default=False),
            preserve_default=False,
        ),
    ]