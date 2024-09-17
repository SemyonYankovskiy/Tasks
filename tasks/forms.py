from datetime import datetime

from django import forms

from .models import Task, Engineer, Tag, Object


class AddTaskForm(forms.ModelForm):
    engineers_create = forms.ModelMultipleChoiceField(queryset=Engineer.objects.all(), required=True)
    tags_create = forms.ModelMultipleChoiceField(queryset=Tag.objects.all(), required=True)
    objects_create = forms.ModelMultipleChoiceField(queryset=Object.objects.all(), required=True)
    completion_time_only = forms.TimeField(required=True)
    completion_date_only = forms.DateField(required=True)

    class Meta:
        model = Task
        fields = ['header', 'priority', 'is_done', 'completion_time_only', 'completion_date_only', 'text', 'engineers_create', 'tags_create', 'files',
                  'objects_create']

    def save(self, commit=True):
        instance: Task = super().save(commit=False)

        # Получаем очищенные данные из полей формы: дата и время
        completion_date_only = self.cleaned_data['completion_date_only']
        completion_time_only = self.cleaned_data['completion_time_only']
        print(completion_date_only)
        print(completion_time_only)
        # Объединяем дату и время в один объект datetime, который сохранится в поле completion_time модели
        completion_time = datetime.strptime(f'{completion_date_only} {completion_time_only}', '%Y-%m-%d %H:%M:%S')

        # Присваиваем собранное значение поля completion_time модели Task
        instance.completion_time = completion_time

        if commit:
            instance.save()

        instance.tags.set(self.cleaned_data['tags_create'])
        instance.engineers.set(self.cleaned_data['engineers_create'])
        instance.objects_set.set(self.cleaned_data['objects_create'])


        return instance


class EditTaskForm(forms.ModelForm):
    # Поля для редактирования связанных объектов (engineers, tags, objects)
    engineers_edit = forms.ModelMultipleChoiceField(queryset=Engineer.objects.all(), required=True)
    tags_edit = forms.ModelMultipleChoiceField(queryset=Tag.objects.all(), required=True)
    objects_edit = forms.ModelMultipleChoiceField(queryset=Object.objects.all(), required=True)

    # Отдельные поля для даты и времени завершения
    completion_time_only = forms.TimeField(required=True)
    completion_date_only = forms.DateField(required=True)

    class Meta:
        model = Task
        # Включаем необходимые поля модели в форму
        fields = ['header', 'priority', 'is_done', 'completion_time_only', 'completion_date_only', 'text',
                  'engineers_edit', 'tags_edit', 'files', 'objects_edit']

    def save(self, commit=True):
        # Получаем объект задачи (Task) из данных формы, но пока не сохраняем его в базу данных
        instance: Task = super().save(commit=False)

        # Получаем очищенные данные из полей формы: дата и время
        completion_date_only = self.cleaned_data['completion_date_only']
        completion_time_only = self.cleaned_data['completion_time_only']

        # Объединяем дату и время в один объект datetime, который сохранится в поле completion_time модели
        completion_time = datetime.strptime(f'{completion_date_only} {completion_time_only}', '%Y-%m-%d %H:%M:%S')

        # Присваиваем собранное значение поля completion_time модели Task
        instance.completion_time = completion_time

        # Если commit=True, сохраняем объект задачи в базе данных
        if commit:
            instance.save()

        # Связываем задачу с выбранными тегами, инженерами и объектами
        instance.tags.set(self.cleaned_data['tags_edit'])
        instance.engineers.set(self.cleaned_data['engineers_edit'])
        instance.objects_set.set(self.cleaned_data['objects_edit'])

        # Возвращаем сохранённый экземпляр задачи
        return instance
