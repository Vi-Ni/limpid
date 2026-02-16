from django.contrib import admin

from .models import LessonProgress, QuizCompletion, QuizResponse


@admin.register(LessonProgress)
class LessonProgressAdmin(admin.ModelAdmin):
    list_display = ("user", "lesson_id", "completed_at")
    list_filter = ("lesson_id",)
    search_fields = ("user__email",)


@admin.register(QuizResponse)
class QuizResponseAdmin(admin.ModelAdmin):
    list_display = ("user", "lesson_id", "question_id", "choice_id", "is_correct", "answered_at")
    list_filter = ("lesson_id", "is_correct")
    search_fields = ("user__email",)


@admin.register(QuizCompletion)
class QuizCompletionAdmin(admin.ModelAdmin):
    list_display = ("user", "lesson_id", "score", "total", "completed_at")
    list_filter = ("lesson_id",)
    search_fields = ("user__email",)
