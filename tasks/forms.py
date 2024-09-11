from django import forms

from .models import Task, Engineer, Tag, Object


class AddTaskForm(forms.ModelForm):
    engineers_create = forms.ModelMultipleChoiceField(queryset=Engineer.objects.all(), required=True)
    tags_create = forms.ModelMultipleChoiceField(queryset=Tag.objects.all(), required=True)
    objects_create = forms.ModelMultipleChoiceField(queryset=Object.objects.all(), required=True)

    class Meta:
        model = Task
        fields = ['header', 'priority', 'is_done', 'completion_time', 'text', 'engineers_create', 'tags_create', 'files',
                  'objects_create']

    def save(self, commit=True):
        instance: Task = super().save(commit=False)

        if commit:
            instance.save()

        instance.tags.set(self.cleaned_data['tags_create'])
        instance.engineers.set(self.cleaned_data['engineers_create'])
        instance.objects_set.set(self.cleaned_data['objects_create'])

        return instance


class EditTaskForm(forms.ModelForm):
    engineers_edit = forms.ModelMultipleChoiceField(queryset=Engineer.objects.all(), required=True)
    tags_edit = forms.ModelMultipleChoiceField(queryset=Tag.objects.all(), required=True)
    objects_edit = forms.ModelMultipleChoiceField(queryset=Object.objects.all(), required=True)

    class Meta:
        model = Task
        fields = ['header', 'priority', 'is_done', 'completion_time', 'text', 'engineers_edit', 'tags_edit', 'files',
                  'objects_edit']

    def save(self, commit=True):
        instance: Task = super().save(commit=False)

        if commit:
            instance.save()

        instance.files.set(self.cleaned_data["files"])
        instance.tags.set(self.cleaned_data['tags_edit'])
        instance.engineers.set(self.cleaned_data['engineers_edit'])
        instance.objects_set.set(self.cleaned_data['objects_edit'])

        return instance