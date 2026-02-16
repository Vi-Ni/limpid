from django.urls import path

from . import views

app_name = "education"

urlpatterns = [
    path("", views.learning_path, name="path"),
    path("<str:lesson_id>/", views.lesson_detail, name="lesson"),
    path("<str:lesson_id>/complete/", views.mark_lesson_complete, name="lesson_complete"),
    path("<str:lesson_id>/quiz/", views.quiz_start, name="quiz_start"),
    path("<str:lesson_id>/quiz/<int:step>/", views.quiz_step, name="quiz_step"),
    path("<str:lesson_id>/quiz/<int:step>/next/", views.quiz_next, name="quiz_next"),
]
