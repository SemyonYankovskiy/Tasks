# Generated by Django 4.2.14 on 2024-08-23 10:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tasks", "0006_attachedfile_type_alter_object_description"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="attachedfile",
            name="type",
        ),
        migrations.AddField(
            model_name="attachedfile",
            name="extension",
            field=models.CharField(blank=True, max_length=10),
        ),
    ]
