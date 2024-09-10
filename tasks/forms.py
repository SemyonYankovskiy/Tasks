from django import forms

from .models import Task, Engineer, Tag, Object


class AddTaskForm(forms.ModelForm):
    engineers_create = forms.ModelMultipleChoiceField(queryset=Engineer.objects.all(), required=True)
    tags_create = forms.ModelMultipleChoiceField(queryset=Tag.objects.all(), required=True)
    objects_create = forms.ModelMultipleChoiceField(queryset=Object.objects.all(), required=True)

    class Meta:
        model = Task
        fields = ['header', 'priority', 'is_done', 'completion_time', 'text', 'engineers_create', 'tags_create',
                  'objects_create']

    def save(self, commit=True):
        instance = super().save(commit=False)

        def save_m2m():
            self.cleaned_data['engineers_create'].update(tasks=instance)
            self.cleaned_data['tags_create'].update(tasks=instance)
            self.cleaned_data['objects_create'].update(tasks=instance)

        if commit:
            instance.save()
            save_m2m()

        return instance
