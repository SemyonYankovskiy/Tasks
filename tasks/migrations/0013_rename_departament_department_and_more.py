# Generated by Django 5.1.1 on 2024-09-25 08:25

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("tasks", "0012_engineer_head_of_department_alter_engineer_position"),
    ]

    operations = [
        migrations.RenameModel(
            old_name="Departament",
            new_name="Department",
        ),
        migrations.RenameField(
            model_name="engineer",
            old_name="departament",
            new_name="department",
        ),
    ]
