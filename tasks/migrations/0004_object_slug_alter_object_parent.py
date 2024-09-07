# Generated by Django 4.2.14 on 2024-08-14 07:39

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tasks", "0003_alter_engineer_user_alter_object_files_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="object",
            name="slug",
            field=models.SlugField(max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name="object",
            name="parent",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="children",
                to="tasks.object",
            ),
        ),
    ]