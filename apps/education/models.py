from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class LessonProgress(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="lesson_progress",
    )
    lesson_id = models.CharField(max_length=10)
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("lesson progress")
        verbose_name_plural = _("lesson progress")
        unique_together = [("user", "lesson_id")]

    def __str__(self):
        return f"{self.user.email} — {self.lesson_id}"


class QuizResponse(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="education_quiz_responses",
    )
    lesson_id = models.CharField(max_length=10)
    question_id = models.CharField(max_length=10)
    choice_id = models.CharField(max_length=5)
    is_correct = models.BooleanField()
    answered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("quiz response")
        verbose_name_plural = _("quiz responses")
        unique_together = [("user", "lesson_id", "question_id")]

    def __str__(self):
        return f"{self.user.email} — {self.lesson_id}/{self.question_id}"


class QuizCompletion(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="quiz_completions",
    )
    lesson_id = models.CharField(max_length=10)
    score = models.PositiveSmallIntegerField()
    total = models.PositiveSmallIntegerField()
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("quiz completion")
        verbose_name_plural = _("quiz completions")
        unique_together = [("user", "lesson_id")]

    def __str__(self):
        return f"{self.user.email} — {self.lesson_id}: {self.score}/{self.total}"
