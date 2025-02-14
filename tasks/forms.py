from datetime import datetime

from ckeditor.widgets import CKEditorWidget
from django import forms
from django.utils.text import slugify

from .models import Task, Engineer, Tag, Object, Department, ObjectGroup, AttachedFile
from .services.service import transliterate


class CKEditorCreateForm(forms.Form):
    text = forms.CharField(widget=CKEditorWidget, label='', required=False)


class CKEditorAnswerForm(forms.Form):
    answer = forms.CharField(widget=CKEditorWidget(config_name='minimal'), label='',  required=False)


class ObjectForm(forms.ModelForm):
    answer = forms.CharField(required=False)

    class Meta:
        model = Task
        fields = [
            'answer'
        ]

    def save(self, commit=True):
        instance: Task = super().save(commit=False)
        instance.text = self.cleaned_data["answer"]

        if commit:
            instance.save()

        return instance


class CKEditorEditForm(forms.Form):
    text_edit = forms.CharField(widget=CKEditorWidget, label='', required=False)


class AddTaskForm(forms.ModelForm):
    # Поле, которое будет принимать значения в виде eng_число и dep_число
    engineers_create = forms.MultipleChoiceField(choices=[], required=False)
    tags_create = forms.ModelMultipleChoiceField(queryset=Tag.objects.all(), required=False)
    objects_create = forms.ModelMultipleChoiceField(queryset=Object.objects.all(), required=False)
    completion_time_only = forms.TimeField(required=True)
    completion_date_only = forms.DateField(required=True)

    class Meta:
        model = Task
        fields = [
            "header",
            "priority",
            "is_done",
            "completion_time_only",
            "completion_date_only",
            "text",
            "engineers_create",
            "tags_create",
            "files",
            "objects_create",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Формирование списка вариантов для инженеров и департаментов
        engineers_choices = [
            (f"eng_{eng.id}", f"{eng.first_name} {eng.second_name}") for eng in Engineer.objects.all()
        ]
        departments_choices = [(f"dep_{dep.id}", f"{dep.name}") for dep in Department.objects.all()]
        # Устанавливаем эти выборы для поля engineers_create
        self.fields["engineers_create"].choices = engineers_choices + departments_choices

    def save(self, commit=True):
        instance: Task = super().save(commit=False)
        # Обрабатываем дату и время завершения задачи
        completion_date_only = self.cleaned_data["completion_date_only"]
        completion_time_only = self.cleaned_data["completion_time_only"]
        completion_time = datetime.strptime(
            f"{completion_date_only} {completion_time_only}", "%Y-%m-%d %H:%M:%S"
        )
        instance.completion_time = completion_time
        instance.deleted = False

        if commit:
            instance.save()

        # Обработка поля engineers_create (ManyToMany связь)
        engineers_create = self.cleaned_data["engineers_create"]
        engineers = []
        departments = []

        for val in engineers_create:
            type_id = val.split("_")
            type = type_id[0]
            id = int(type_id[1])

            if type == "eng":
                engineers.append(id)  # Если это конкретный инженер, добавляем его ID
            elif type == "dep":
                # Если это департамент, находим всех инженеров, связанных с этим департаментом
                # dep_engineers = Engineer.objects.filter(department__id=id)
                # engineers.extend(dep_engineers.values_list('id', flat=True))  # Добавляем ID всех инженеров департамента
                departments.append(id)  # Также сохраняем ID департамента

        # Устанавливаем найденных инженеров и департаменты задаче
        if engineers:
            instance.engineers.set(engineers)

        if departments:
            instance.departments.set(departments)  # Сохраняем департаменты

        if self.cleaned_data["tags_create"]:
            instance.tags.set(self.cleaned_data["tags_create"])

        if self.cleaned_data["objects_create"]:
            instance.objects_set.set(self.cleaned_data["objects_create"])

        if commit:
            instance.save()

        return instance


class EditTaskForm(forms.ModelForm):
    engineers_edit = forms.MultipleChoiceField(
        choices=[], required=False
    )  # Поддержка департаментов и инженеров
    tags_edit = forms.ModelMultipleChoiceField(queryset=Tag.objects.all(), required=False)
    objects_edit = forms.ModelMultipleChoiceField(
        queryset=Object.objects.all(), required=False
    )  # Поле для объектов
    completion_time_only = forms.TimeField(required=True)
    completion_date_only = forms.DateField(required=True)
    text_edit = forms.CharField(required=False)

    class Meta:
        model = Task
        fields = [
            "header",
            "priority",
            "is_done",
            "completion_time_only",
            "completion_date_only",
            "text_edit",
            "engineers_edit",
            "tags_edit",
            "files",
            "objects_edit",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Формирование списка вариантов для инженеров и департаментов
        engineers_choices = [
            (f"eng_{eng.id}", f"{eng.first_name} {eng.second_name}") for eng in Engineer.objects.all()
        ]
        departments_choices = [(f"dep_{dep.id}", f"{dep.name}") for dep in Department.objects.all()]
        # Устанавливаем эти выборы для поля engineers_create
        self.fields["engineers_edit"].choices = engineers_choices + departments_choices

    def save(self, commit=True):
        instance: Task = super().save(commit=False)
        # Обрабатываем дату и время завершения задачи
        completion_date_only = self.cleaned_data["completion_date_only"]
        completion_time_only = self.cleaned_data["completion_time_only"]
        completion_time = datetime.strptime(
            f"{completion_date_only} {completion_time_only}", "%Y-%m-%d %H:%M:%S"
        )
        instance.completion_time = completion_time
        instance.text = self.cleaned_data["text_edit"]
        instance.deleted = False

        if commit:
            instance.save()

        # Обработка поля engineers_create (ManyToMany связь)
        engineers_create = self.cleaned_data["engineers_edit"]
        engineers = []
        departments = []

        for val in engineers_create:
            type_id = val.split("_")
            type = type_id[0]
            id = int(type_id[1])

            if type == "eng":
                engineers.append(id)  # Если это конкретный инженер, добавляем его ID
            elif type == "dep":
                # Если это департамент, находим всех инженеров, связанных с этим департаментом
                # dep_engineers = Engineer.objects.filter(department__id=id)
                # engineers.extend(dep_engineers.values_list('id', flat=True))  # Добавляем ID всех инженеров департамента
                departments.append(id)  # Также сохраняем ID департамента

        # Устанавливаем найденных инженеров и департаменты задаче
        if engineers:
            instance.engineers.set(engineers)
        else:
            instance.engineers.clear()

        if departments:
            instance.departments.set(departments)  # Сохраняем департаменты
        else:
            instance.departments.clear()

        if self.cleaned_data["tags_edit"]:
            instance.tags.set(self.cleaned_data["tags_edit"])

        if self.cleaned_data["objects_edit"]:
            instance.objects_set.set(self.cleaned_data["objects_edit"])

        if commit:
            instance.save()

        return instance


class CKEditorEditObjForm(forms.Form):
    description = forms.CharField(widget=CKEditorWidget, label='', required=False)


class ObjectForm(forms.ModelForm):
    obj_tags_edit = forms.ModelMultipleChoiceField(queryset=Tag.objects.all(), required=False)

    class Meta:
        model = Object
        fields = [
            'name',
            'priority',
            'description',
            'zabbix_link',
            'ecstasy_link',
            'notes_link',
            'another_link',
            'obj_tags_edit',
            'files',
            'groups'
        ]

    def save(self, commit=True):
        instance: Object = super().save(commit=False)

        if commit:
            instance.save()

        # Обновление групп
        if 'groups' in self.cleaned_data and self.cleaned_data['groups']:
            instance.groups.set(self.cleaned_data['groups'])  # Здесь вы должны передавать список ID групп
        else:
            instance.groups.clear()  # Если ничего не передано, удаляем все группы

        # Обновление тегов
        if 'obj_tags_edit' in self.cleaned_data:
            instance.tags.set(self.cleaned_data["obj_tags_edit"])  # Установите теги
        else:
            instance.tags.clear()  # Удалите все теги, если нет переданных данных

        return instance


class CKEditorCreateObjForm(forms.Form):
    description = forms.CharField(widget=CKEditorWidget, label='', required=False)


class ObjectCreateForm(forms.ModelForm):
    tags_create = forms.ModelMultipleChoiceField(
        queryset=Tag.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple(),
        label="Теги"
    )
    groups_create = forms.ModelMultipleChoiceField(
        queryset=ObjectGroup.objects.all(),
        required=True,
        widget=forms.CheckboxSelectMultiple(),
        label="Группы"
    )
    files = forms.ModelMultipleChoiceField(
        queryset=AttachedFile.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple(),
        label="Файлы"
    )

    class Meta:
        model = Object
        fields = [
            'name',
            'priority',
            'parent',
            'description',
            'zabbix_link',
            'ecstasy_link',
            'notes_link',
            'another_link',
            'tags_create',
            'files',
            'groups_create'
        ]

    def save(self, commit=True):
        instance: Object = super().save(commit=False)

        # Генерация slug на основе name
        if not instance.slug:  # Генерируем slug только если он еще не задан
            base_slug = slugify(transliterate(instance.name))  # Преобразуем кириллицу и генерируем slug
            slug = base_slug
            counter = 1

            # Проверяем уникальность slug
            while Object.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1

            instance.slug = slug

        if commit:
            instance.save()

        # Обновление групп
        if 'groups_create' in self.cleaned_data and self.cleaned_data['groups_create']:
            instance.groups.set(self.cleaned_data['groups_create'])
        else:
            instance.groups.clear()

        # Обновление тегов
        if 'tags_create' in self.cleaned_data:
            instance.tags.set(self.cleaned_data["tags_create"])
        else:
            instance.tags.clear()

        # Обновление файлов
        if 'files' in self.cleaned_data:
            instance.files.set(self.cleaned_data["files"])
        else:
            instance.files.clear()

        return instance
