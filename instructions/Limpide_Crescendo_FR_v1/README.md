# Limpide — Parcours Crescendo (FR) v1

Ce dossier contient :
- `lessons/` : **1 fichier Markdown par leçon** (avec frontmatter YAML)
- `quizzes/` : **1 fichier JSON par leçon** (QCM + corrigés + explications)
- `curriculum_index.json` : ordre des niveaux et des leçons
- `glossary_fr.json` : glossaire minimal v1

## Intégration Django (idée simple)
1) Crée un modèle `Lesson` (id, title, level, slug, path_md, duration, tags, prerequisites)
2) Charge les fichiers Markdown au runtime (ou en import management command)
3) Pour les quiz :
   - lis `quizzes/<lesson_id>.json`
   - affiche les questions (HTMX) et renvoie la correction immédiate
4) Progression :
   - `LessonProgress(user, lesson_id, completed_at, score_optional)`
   - pas de blocage (min_correct = 0), mais afficher une recommandation si erreurs

## Disclaimer
Ce contenu est éducatif. Il n’est pas un conseil financier, fiscal ou juridique.
