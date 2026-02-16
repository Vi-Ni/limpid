from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import redirect, render
from django.utils.translation import get_language

from .models import LessonProgress, QuizCompletion, QuizResponse
from .services import (
    get_user_progress_summary,
    load_lesson,
    load_quiz,
)


def _lang():
    lang = get_language() or "en"
    return lang if lang in ("en", "fr") else "en"


@login_required
def learning_path(request):
    """Learning path overview with progress."""
    lang = _lang()
    summary = get_user_progress_summary(request.user, lang)
    return render(request, "education/path.html", {"summary": summary})


@login_required
def lesson_detail(request, lesson_id):
    """Render a single lesson."""
    lang = _lang()
    lesson = load_lesson(lesson_id, lang)
    if lesson is None:
        raise Http404

    is_completed = LessonProgress.objects.filter(user=request.user, lesson_id=lesson_id).exists()

    quiz = load_quiz(lesson_id, lang)
    quiz_completion = QuizCompletion.objects.filter(user=request.user, lesson_id=lesson_id).first()

    return render(
        request,
        "education/lesson.html",
        {
            "lesson_id": lesson_id,
            "metadata": lesson["metadata"],
            "content_html": lesson["content_html"],
            "is_completed": is_completed,
            "has_quiz": quiz is not None,
            "quiz_completion": quiz_completion,
        },
    )


@login_required
def mark_lesson_complete(request, lesson_id):
    """HTMX POST: toggle lesson completion."""
    if request.method != "POST":
        return redirect("education:lesson", lesson_id=lesson_id)

    progress, created = LessonProgress.objects.get_or_create(user=request.user, lesson_id=lesson_id)
    if not created:
        progress.delete()
        is_completed = False
    else:
        is_completed = True

    return render(
        request,
        "education/partials/lesson_complete_button.html",
        {"lesson_id": lesson_id, "is_completed": is_completed},
    )


@login_required
def quiz_start(request, lesson_id):
    """Quiz shell page — clears previous responses for a fresh attempt."""
    lang = _lang()
    quiz = load_quiz(lesson_id, lang)
    if quiz is None:
        raise Http404

    lesson = load_lesson(lesson_id, lang)

    # Clear previous responses for fresh attempt
    QuizResponse.objects.filter(user=request.user, lesson_id=lesson_id).delete()
    QuizCompletion.objects.filter(user=request.user, lesson_id=lesson_id).delete()

    question = quiz["questions"][0]
    total = len(quiz["questions"])

    return render(
        request,
        "education/quiz.html",
        {
            "lesson_id": lesson_id,
            "lesson_title": lesson["metadata"].get("title", "") if lesson else "",
            "question": question,
            "step": 1,
            "total": total,
        },
    )


@login_required
def quiz_step(request, lesson_id, step):
    """Handle quiz question: POST saves answer + shows feedback, GET shows question."""
    lang = _lang()
    quiz = load_quiz(lesson_id, lang)
    if quiz is None:
        raise Http404

    questions = quiz["questions"]
    total = len(questions)
    index = step - 1

    if index < 0 or index >= total:
        return redirect("education:quiz_start", lesson_id=lesson_id)

    question = questions[index]

    if request.method == "POST":
        choice_id = request.POST.get("choice")
        is_correct = choice_id == question["answer"]

        QuizResponse.objects.update_or_create(
            user=request.user,
            lesson_id=lesson_id,
            question_id=question["id"],
            defaults={"choice_id": choice_id or "", "is_correct": is_correct},
        )

        return render(
            request,
            "education/partials/quiz_feedback.html",
            {
                "lesson_id": lesson_id,
                "question": question,
                "choice_id": choice_id,
                "is_correct": is_correct,
                "step": step,
                "total": total,
            },
        )

    # GET: show question
    return render(
        request,
        "education/partials/quiz_question.html",
        {
            "lesson_id": lesson_id,
            "question": question,
            "step": step,
            "total": total,
        },
    )


@login_required
def quiz_next(request, lesson_id, step):
    """Advance to next question or show results."""
    lang = _lang()
    quiz = load_quiz(lesson_id, lang)
    if quiz is None:
        raise Http404

    questions = quiz["questions"]
    total = len(questions)
    next_step = step + 1

    if next_step <= total:
        question = questions[next_step - 1]
        return render(
            request,
            "education/partials/quiz_question.html",
            {
                "lesson_id": lesson_id,
                "question": question,
                "step": next_step,
                "total": total,
            },
        )

    # Quiz complete — calculate score
    responses = QuizResponse.objects.filter(user=request.user, lesson_id=lesson_id)
    score = responses.filter(is_correct=True).count()

    QuizCompletion.objects.update_or_create(
        user=request.user,
        lesson_id=lesson_id,
        defaults={"score": score, "total": total},
    )

    # Auto-mark lesson as complete
    LessonProgress.objects.get_or_create(user=request.user, lesson_id=lesson_id)

    percentage = round(score / total * 100) if total > 0 else 0

    return render(
        request,
        "education/partials/quiz_result.html",
        {
            "lesson_id": lesson_id,
            "score": score,
            "total": total,
            "percentage": percentage,
        },
    )
