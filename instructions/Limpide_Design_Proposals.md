# Limpide — Propositions de design (UI/UX) + Design System (v1)

## Objectifs UX
- **Confiance** : interface sobre, claire, “banque/outil sérieux” mais chaleureuse.
- **Compréhension** : chaque chiffre doit être expliqué (tooltip + lien).
- **Action consciente** : pas de CTA agressifs, pas de “Buy now”. Plutôt “Comprendre” / “Explorer”.
- **Responsive** : expérience mobile 1ère classe (lecture/éducation), desktop optimisé (dashboard).

---

## Directions visuelles (3 pistes)

### A) “Clair & calme” (recommandé pour Limpide)
- Fond : blanc cassé / gris très clair
- Accent : bleu-gris / indigo doux
- Vibe : “outil médical/ingénierie” → précision + sérénité  
**Pourquoi :** la transparence radicale nécessite un design qui rassure et ne “vend” pas.

### B) “Terre & impact”
- Fond : blanc chaud
- Accent : vert profond + beige
- Vibe : local, agriculture, impact  
**Pourquoi :** cohérent avec la mission “investir localement”.

### C) “Nuit & data”
- Dark mode natif
- Accent : cyan/bleu  
**Pourquoi :** agréable pour dashboards mais peut être moins rassurant en finance au début.

➡️ Reco : commencer par **A**, ajouter **B** comme palette alternative (impact) + dark mode plus tard.

---

## Architecture de navigation (IA)

### Desktop
- **Topbar** : logo Limpide, recherche (plus tard), profil
- **Sidebar** (icônes + labels) :
  1) Accueil
  2) Portefeuilles
  3) Transparence
  4) Apprendre
  5) Scénarios
  6) Impact (annuaire)

### Mobile
- **Bottom nav** (5 items) : Accueil, Portefeuille, Apprendre, Scénarios, Profil
- Impact accessible via “Plus” ou dans Apprendre (module Impact)

---

## Layout de base

### Grille
- Max width contenu : 1100–1200px
- Layout principal : `min-h-screen` + zone content + footer
- Sidebar fixe desktop, drawer mobile

### Hiérarchie
- H1 : 24–32px, max 1 par page
- H2 : 18–22px
- Texte : 15–16px
- Lignes : 1.5–1.7

### Règles de lisibilité
- Pas de blocs “full width” trop larges : la lecture souffre.
- Cartes avec espace interne généreux.
- Utiliser des “badges” (frais, risque, liquidité) plutôt que trop de texte.

---

## Composants (Tailwind) à standardiser

### 1) Card
- Header : titre + icône info
- Body : métriques / texte
- Footer : liens “Comprendre” / “Voir détails”
Variants :
- `card-default`
- `card-warning` (risque/frais élevé)
- `card-success` (checklist complétée)

### 2) Metric row
- label (gauche)
- value (droite)
- mini-annotation (gris) : “Pourquoi ça bouge ?”
- tooltip (i)

### 3) Tooltip “éducatif”
Contient :
- définition 1 phrase
- “Pourquoi c’est important”
- lien “Lire la leçon”  
⚠️ sur mobile : tooltip → bottom sheet/modal

### 4) Progress / Learning stepper
- niveaux en cartes
- barre de progression
- “prochaine leçon recommandée”

### 5) Table holdings
Colonnes :
- Nom
- Poids (%)
- Pays / secteur
- Score transparence
- Controverses (si dispo)  
Actions : “Voir fiche”, “Pourquoi c’est dans mon ETF ?”

### 6) Callouts dans les leçons
- `callout-info` : définition
- `callout-warning` : piège courant
- `callout-example` : exemple
- `callout-impact` : angle impact/local

### 7) Badges “transparence”
- Frais : `0.05%` (badge)
- Liquidité : `Élevée / Moyenne / Faible`
- Horizon : `Court / Moyen / Long`
- Risque : `Faible / Modéré / Élevé`
- Impact : `ESG / Impact / Local`

---

## Pages : wireframes textuels + contenu

### Page 1 — Accueil (home)
Objectif : expliquer la promesse, rassurer, orienter.

Sections :
1) Hero
- Titre : “Comprendre avant d’investir.”
- Sous-texte : “Transparence radicale + parcours pédagogique.”
- CTA : “Commencer (5 min)” / “Explorer le parcours”

2) 3 piliers
- Transparence (holdings, frais, risques)
- Éducation (crescendo)
- Scénarios (tester sans se brûler)

3) “Comment ça marche” (3 étapes)
- Définir ton profil
- Explorer / importer un portefeuille (sandbox)
- Comprendre : holdings → frais → risques → impact

4) Disclaimer footer (sobre, non anxiogène)

---

### Page 2 — Onboarding (wizard 5 étapes)
**Étape 1 :** objectifs  
**Étape 2 :** horizon & liquidité  
**Étape 3 :** tolérance/capacité de risque  
**Étape 4 :** valeurs / impact  
**Étape 5 :** résumé (profil + parcours conseillé)

UI :
- progress bar en haut
- 1 question par écran (mobile-friendly)
- “Pourquoi on demande ça ?” (tooltip)

Sortie :
- carte “Ton profil”
- carte “Tes priorités d’apprentissage”
- bouton “Aller au dashboard”

---

### Page 3 — Dashboard (overview)
Header :
- “Bonjour, …”
- chips : Profil (Prudent/Équilibré/Dynamique), Horizon principal

Cards (grid 2 colonnes desktop, 1 mobile) :
1) Valeur totale (si connecté à un portefeuille / sinon sandbox)
2) Allocation (donut)
3) Frais estimés (annuels)
4) Risque : drawdown historique / volatilité (explications)
5) Holdings top 10 (table mini)
6) “Prochaine leçon”

Toujours :
- chaque métrique a un (i) + lien “Comprendre”

---

### Page 4 — Portefeuilles
- Liste : “Sandbox”, “Import CSV”, “Manuel”
- Chaque portefeuille : tags (devise, enveloppe, date)
- CTA : “Voir transparence”

---

### Page 5 — Détail portefeuille
Tabs :
1) Vue d’ensemble
2) Holdings
3) Frais
4) Risques
5) Impact

UX :
- Tabs → accordéon sur mobile
- Graph performance : simple, avec avertissement (pas de promesse)

---

### Page 6 — Transparence (rapport)
Structure “audit” :
- “Ce que tu détiens vraiment” (look-through)
- “Ce que ça coûte” (tous frais)
- “Risques principaux” (concentration, devise, drawdown)
- “Ce que tu peux apprendre maintenant” (leçons liées)

CTA : “Comprendre ces risques” (vers leçon, pas vers achat)

---

### Page 7 — Apprendre (learning path)
- Niveaux 0→5
- Chaque niveau : description + temps estimé + prérequis
- Leçon : titre + durée + objectif + bouton “Commencer”
- Indicateur : complété / en cours

---

### Page 8 — Leçon (lecture)
Layout :
- colonne centrale (prose)
- à droite (desktop) : “Résumé”, “Mini-quiz”, “Voir dans mon dashboard”

Bas :
- bouton “Marquer comme compris”
- “Leçon suivante”

---

### Page 9 — Scénarios
2 modes :
1) “Scénarios guidés” (chute -30%, inflation, taux +2%, devise)
2) “Mode libre” (sliders)

Résultat :
- impact sur valeur / allocation
- “ce que ça signifie” + liens leçons

---

### Page 10 — Impact (annuaire)
- recherche + filtres
- cartes d’initiatives (type, région, horizon, liquidité)
- fiche détail :
  - modèle économique
  - risque/liquidité
  - transparence (reporting)
  - impact (mesure)
  - liens externes

⚠️ Toujours : disclaimer “pas une recommandation”.

---

## Microcopy / ton
- Simple, concret, non moralisateur.
- Éviter : “optimal”, “le meilleur”, “battre le marché”.
- Préférer : “Comprendre”, “Comparer”, “Explorer”, “Voir à l’intérieur”.

Exemples :
- “Ce chiffre bouge parce que…”
- “Voici 3 questions utiles à te poser.”
- “Ce n’est pas grave de ne pas savoir — on construit étape par étape.”

---

## Accessibilité (a11y) + inclusivité
- Contraste AA minimum
- Focus visible
- Navigation clavier
- Tooltips accessibles (aria-describedby)
- Graphs avec textes alternatifs / valeurs

---

## Recommandations front (adaptées à Django + HTMX + Tailwind)
- Utiliser des “partials” HTMX :
  - `components/metric_row.html`
  - `components/tooltip.html`
  - `education/_lesson_card.html`
- Un “design system” dans `templates/components/` + page interne `/styleguide` (dev only)
- Le contenu des leçons en Markdown, rendu côté serveur (`markdown` déjà dans deps)

---

## Checklist “Design Done”
- [ ] Home claire + 1 CTA principal
- [ ] Onboarding 5 étapes fluide mobile
- [ ] Dashboard lisible : 6 cartes max
- [ ] Chaque métrique a “Pourquoi / lien”
- [ ] Leçons lisibles (typography)
- [ ] Scénarios compréhensibles (pas trop de sliders)
- [ ] Impact : fiches standardisées, pas de promesses

