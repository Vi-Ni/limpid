## From: https://boristane.com/blog/how-i-use-claude-code/

## Phase 1: Research

go through the task scheduling flow, understand it deeply and look for potential bugs. there definitely are bugs in the system as it sometimes runs tasks that should have been cancelled. keep researching the flow until you find all the bugs, don’t stop until all the bugs are found. when you’re done, write a detailed report of your findings in research.md

read this repo in depth, understand how it works deeply, what it does and all its specificities. when that’s done, update in detail the research.md report in docs/research with your learnings and findings. Don't ask to read all files in this repo, you have access to everything

## Phase 2: Planning

I want to build un nouveau design de formulaire pour le real estate avec une sorte de carroussel, étape par étape, comme le risk quizz qui explique simplement ce qu'on demande. 

Aussi j'aimerais que le monthly cost devienne une petite carte à la place de your share (car au final en selection ma part je vois 2 fois l'information dans les petite cartes).

Write a very detailed plan in docs/plans/plan_real_estate_forms.md document outlining how to implement this.

I added a few notes to the document, address all the notes and update the document accordingly. don’t implement yet

add a detailed todo list to the plan, with all the phases and individual tasks necessary to complete the plan - don’t implement yet

## Phase 3: Implementation

implement it all. when you’re done with a task or phase, mark it as completed in the plan document. do not stop until all tasks and phases are completed. do not add unnecessary comments or jsdocs, do not use any or unknown types. continuously run typecheck to make sure you’re not introducing new issues.

I want to build some new features on the real estate part. The following features are explained in french:

- Je veux avoir la possibilité de changer le taux à partir d'une certaine date (lors du renouvellement ou juste pour simuler l'impact d'un nouveau taux)
- Ajouter le loyer et les charges d'agence si on passe par une agence pour les biens en location
- Je veux voir combien par mois coûte le bien (incluant donc l'hypothèque mais aussi les taxes lissées sur 12 mois et le cas échéant en enlevant le loyer perçus)
- je veux voir un bouton qui montre uniquement ce que MOI je paye (une sorte de toggle, le total vs uniquement moi)
- je veux avoir la possibilité de changer dans l'échéancier (ou d'une autre façon) ce que mets chacun des propriétaires par mois comme remboursement (en dollars ou euros) car même si de base la mise de fond est 50% chacun, le remboursement peut changer par mois et donc sur long terme changer la part.
- je veux avoir la possibilité de supprimer un bien
- lorsque l'on liste des travaux rajouter un lien vers un google drive où on retrouve la preuve des travaux
- dans les datavizs, il serait plus naturel de voir aussi des courbes d'évolution, voir par exemple quand le remboursement du capital croise celui des interet, ou l'évolution de ce qu'on paye par mois.

Base on all the knowledge in research.md and all the file in this repo, write a very detailed plan in docs/plans/plan_miscelianous_realestate_features.md document outlining how to implement this.

Voici mes retours:

- j'aimerais que les cartes en haut fassent la même taille pour plus d'harmonie, donc ajouter un pourcentage ou une sparkline pour chacune, mais il faut qu'elles soient de la même taille
- pour le monthly cost, pas la peine d'afficher le total ET my share car on a un bouton pour ça. J'aimerais d'ailleurs changer le bouton en un toggle
- pour la partie ownership, je trouve que ça se repête un peu, uniquement avoir l'ownership breakdown serait suffisant avec la gestion de la suppression d'un co-owner. Aussi au lieu d'afficher les emails, affichons les name des utilisateurs, c'est plus sympa
- Dans la vue amortization schedule, le pre-owner summary est pas bon, les calculs ne sont pas bons. Fix ça. J'aimerais aussi dans le payment schedule voir les taux d'interet pour chaque mois (car il peut changer), ainsi de la repartition du paiement entre les co-owners refletant l'historique. Par defaut c'est la repartition à l'achat, puis prendre en compte les informations dans le payments split.
- Il faut que je puisse pouvoir editer un payment split (et remove)
- If I sell today, je le mettrais tout en bas
- Dans le mortgage evolution, j'aimerais highlighter le mois courant

### Per-Owner Summary

## Liste features

- home page dashboard
  - voir combien je paye en tout par mois dans mes biens
  - ⁠⁠bouton on off je vends / je garde pour voir l’impact
