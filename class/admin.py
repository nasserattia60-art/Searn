from django.contrib import admin
from .models import (
    Class, Lesson, Membership, LessonProgress,
    Quiz, QuizQuestion, QuizAnswer, QuizAttempt, QuizUserResponse
)


class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 0
    fields = ['order', 'title', 'video_id']


class MembershipInline(admin.TabularInline):
    model = Membership
    extra = 0


class QuizAnswerInline(admin.TabularInline):
    model = QuizAnswer
    extra = 0
    fields = ['order', 'answer_text', 'is_correct']


class QuizQuestionInline(admin.TabularInline):
    model = QuizQuestion
    extra = 0
    fields = ['order', 'question_text', 'question_type']


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
    list_display = ['order', 'title', 'class_room', 'video_id', 'has_cache', 'has_quiz']
    list_filter = ['class_room']
    search_fields = ['title']

    def has_cache(self, obj):
        return bool(obj.cached_video_url)
    has_cache.short_description = 'Cached'
    has_cache.boolean = True
    
    def has_quiz(self, obj):
        return hasattr(obj, 'quiz')
    has_quiz.short_description = 'Has Quiz'
    has_quiz.boolean = True


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ['user', 'class_room', 'joined_at']
    list_filter = ['class_room']


@admin.register(LessonProgress)
class LessonProgressAdmin(admin.ModelAdmin):
    list_display = ['user', 'lesson', 'completed', 'last_position']
    list_filter = ['completed', 'lesson__class_room']


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ['lesson', 'title', 'question_count', 'passing_score', 'generated_by_ai']
    list_filter = ['generated_by_ai', 'created_at']
    search_fields = ['title', 'lesson__title']
    inlines = [QuizQuestionInline]
    
    def question_count(self, obj):
        return obj.get_questions_count()
    question_count.short_description = 'Questions'


@admin.register(QuizQuestion)
class QuizQuestionAdmin(admin.ModelAdmin):
    list_display = ['order', 'quiz', 'question_text', 'question_type', 'difficulty']
    list_filter = ['question_type', 'quiz']
    search_fields = ['question_text']
    inlines = [QuizAnswerInline]
    
    def difficulty(self, obj):
        # You can extract this from explanation or add a field
        return "Medium"


@admin.register(QuizAnswer)
class QuizAnswerAdmin(admin.ModelAdmin):
    list_display = ['question', 'answer_text', 'is_correct', 'order']
    list_filter = ['is_correct', 'question__quiz']
    search_fields = ['answer_text']


@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = ['user', 'quiz', 'score', 'passed', 'completed_at']
    list_filter = ['passed', 'quiz__lesson__class_room']
    search_fields = ['user__username', 'quiz__lesson__title']
    readonly_fields = ['score', 'correct_answers', 'total_questions']


@admin.register(QuizUserResponse)
class QuizUserResponseAdmin(admin.ModelAdmin):
    list_display = ['attempt', 'question', 'is_correct', 'is_answered']
    list_filter = ['is_correct', 'is_answered']
    search_fields = ['attempt__user__username']