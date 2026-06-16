from django.contrib import admin
from .models import Class, Lesson, Membership, LessonProgress


class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 0
    fields = ['order', 'title', 'video_id']


class MembershipInline(admin.TabularInline):
    model = Membership
    extra = 0


@admin.register(Class)
class ClassAdmin(admin.ModelAdmin):
    list_display = ['name', 'lesson_count', 'member_count', 'created_at']
    search_fields = ['name', 'description']
    inlines = [LessonInline, MembershipInline]

    def lesson_count(self, obj):
        return obj.lessons.count()
    lesson_count.short_description = 'Lessons'

    def member_count(self, obj):
        return obj.members.count()
    member_count.short_description = 'Members'


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ['order', 'title', 'class_room', 'video_id', 'has_cache']
    list_filter = ['class_room']
    search_fields = ['title']

    def has_cache(self, obj):
        return bool(obj.cached_video_url)
    has_cache.short_description = 'Cached'
    has_cache.boolean = True


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ['user', 'class_room', 'joined_at']
    list_filter = ['class_room']


@admin.register(LessonProgress)
class LessonProgressAdmin(admin.ModelAdmin):
    list_display = ['user', 'lesson', 'completed', 'last_position']
    list_filter = ['completed', 'lesson__class_room']