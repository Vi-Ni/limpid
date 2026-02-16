# Limpide — Crescendo Path (EN) v1

This folder contains:
- `lessons/`: **1 Markdown file per lesson** (with YAML frontmatter)
- `quizzes/`: **1 JSON file per lesson** (MCQ + answers + explanations)
- `curriculum_index.json`: level and lesson ordering
- `glossary_en.json`: minimal glossary v1

## Django Integration (simple approach)
1) Create a `Lesson` model (id, title, level, slug, path_md, duration, tags, prerequisites)
2) Load Markdown files at runtime (or via an import management command)
3) For quizzes:
   - read `quizzes/<lesson_id>.json`
   - display questions (HTMX) and return immediate feedback
4) Progress:
   - `LessonProgress(user, lesson_id, completed_at, score_optional)`
   - no blocking (min_correct = 0), but show a recommendation if errors occur

## Disclaimer
This content is educational. It is not financial, tax, or legal advice.
