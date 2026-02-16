import contextlib
import json
import re
from functools import lru_cache
from pathlib import Path

import markdown
from django.conf import settings
from django.utils.translation import get_language

from .models import LessonProgress, QuizCompletion

CURRICULUM_DIRS = {
    "en": Path(settings.BASE_DIR) / "instructions" / "Limpide_Crescendo_EN_v1",
    "fr": Path(settings.BASE_DIR) / "instructions" / "Limpide_Crescendo_FR_v1",
}


def _lang():
    """Return 'en' or 'fr' based on current language."""
    lang = get_language() or "en"
    return lang if lang in CURRICULUM_DIRS else "en"


def get_curriculum_path(language_code=None):
    """Return the Path to the curriculum directory for the given language."""
    lang = language_code or _lang()
    return CURRICULUM_DIRS.get(lang, CURRICULUM_DIRS["en"])


@lru_cache(maxsize=4)
def load_curriculum_index(language_code):
    """Parse and cache the curriculum_index.json."""
    path = get_curriculum_path(language_code) / "curriculum_index.json"
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=4)
def load_glossary(language_code):
    """Parse and cache the glossary JSON."""
    base = get_curriculum_path(language_code)
    for name in [f"glossary_{language_code}.json", "glossary.json"]:
        path = base / name
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    return []


def _parse_frontmatter(text):
    """Parse YAML-like frontmatter from markdown text.

    Returns (metadata_dict, body_text).
    """
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", text, re.DOTALL)
    if not match:
        return {}, text

    fm_block, body = match.group(1), match.group(2)
    metadata = {}
    current_key = None

    for line in fm_block.split("\n"):
        # List item (indented "  - value")
        list_match = re.match(r"^\s+-\s+(.+)$", line)
        if list_match and current_key is not None:
            if not isinstance(metadata[current_key], list):
                metadata[current_key] = []
            metadata[current_key].append(list_match.group(1).strip())
            continue

        # Key: value pair
        kv_match = re.match(r"^(\w[\w_]*):\s*(.*)$", line)
        if kv_match:
            key = kv_match.group(1)
            val = kv_match.group(2).strip().strip('"').strip("'")
            current_key = key
            if val:
                with contextlib.suppress(ValueError):
                    val = int(val)
                metadata[key] = val
            else:
                metadata[key] = []
            continue

    return metadata, body


@lru_cache(maxsize=64)
def _load_lesson_raw(lesson_id, language_code):
    """Load and cache raw lesson file content."""
    path = get_curriculum_path(language_code) / "lessons" / f"{lesson_id}.md"
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


def load_lesson(lesson_id, language_code=None):
    """Load a lesson: parse frontmatter + render markdown to HTML.

    Returns dict with 'metadata' and 'content_html', or None if not found.
    """
    lang = language_code or _lang()
    raw = _load_lesson_raw(lesson_id, lang)
    if raw is None:
        return None

    metadata, body = _parse_frontmatter(raw)
    content_html = markdown.markdown(
        body,
        extensions=["extra", "smarty"],
    )
    return {
        "metadata": metadata,
        "content_html": content_html,
    }


@lru_cache(maxsize=64)
def load_quiz(lesson_id, language_code=None):
    """Load and cache a quiz JSON file. Returns dict or None."""
    lang = language_code or _lang()
    path = get_curriculum_path(lang) / "quizzes" / f"{lesson_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=4)
def get_lesson_titles(language_code):
    """Return a dict mapping lesson_id -> short title for all lessons."""
    index = load_curriculum_index(language_code)
    titles = {}
    for level_data in index["levels"]:
        for lid in level_data["lessons"]:
            raw = _load_lesson_raw(lid, language_code)
            if raw:
                meta, _ = _parse_frontmatter(raw)
                titles[lid] = meta.get("title", lid)
            else:
                titles[lid] = lid
    return titles


def get_user_progress_summary(user, language_code=None):
    """Build a progress summary for the learning path view."""
    lang = language_code or _lang()
    index = load_curriculum_index(lang)

    completed_ids = set(LessonProgress.objects.filter(user=user).values_list("lesson_id", flat=True))
    quiz_scores = dict(QuizCompletion.objects.filter(user=user).values_list("lesson_id", "score"))

    total = 0
    completed = 0
    by_level = []

    titles = get_lesson_titles(lang)

    for level_data in index["levels"]:
        lesson_ids = level_data["lessons"]
        level_total = len(lesson_ids)
        level_completed = sum(1 for lid in lesson_ids if lid in completed_ids)
        total += level_total
        completed += level_completed
        by_level.append(
            {
                "level": level_data["level"],
                "title": level_data["title"],
                "lessons": [{"id": lid, "title": titles.get(lid, lid)} for lid in lesson_ids],
                "total": level_total,
                "completed": level_completed,
                "is_complete": level_completed == level_total,
            }
        )

    percentage = round(completed / total * 100) if total > 0 else 0

    return {
        "total": total,
        "completed": completed,
        "percentage": percentage,
        "completed_ids": completed_ids,
        "quiz_scores": quiz_scores,
        "by_level": by_level,
    }


def get_next_lesson(user, language_code=None):
    """Return the first uncompleted lesson as {id, title, level} or None."""
    lang = language_code or _lang()
    index = load_curriculum_index(lang)
    completed_ids = set(LessonProgress.objects.filter(user=user).values_list("lesson_id", flat=True))
    titles = get_lesson_titles(lang)

    for level_data in index["levels"]:
        for lid in level_data["lessons"]:
            if lid not in completed_ids:
                return {
                    "id": lid,
                    "title": titles.get(lid, lid),
                    "level": level_data["level"],
                }
    return None
