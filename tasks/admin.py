from django.contrib import admin

from .models import UserObjectGroup, ObjectGroup, Object, Tag, Task, Address, AttachedFile, Engineer

admin.site.register(UserObjectGroup)
admin.site.register(ObjectGroup)
admin.site.register(Tag)
admin.site.register(Task)
admin.site.register(Address)
admin.site.register(AttachedFile)
admin.site.register(Engineer)


@admin.register(Object)
class ObjectAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
