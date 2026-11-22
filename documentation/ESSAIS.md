# Écrire une pièce

Une pièce = un objectif + un jeu de documents + une ou plusieurs conducteurs. Le format est
vérifié mécaniquement : `python -m archiviste valider`.

## Arborescence

```
dossiers/<slug>/
  fiche.json     objectif, budget, date de référence, passes
  conducteur.json     étapes enregistrées (une passe)
  conducteur-1.json   passe 1 (pièce à deux passes)
  conducteur-2.json   passe 2
```

Les documents viennent de `documents/<nom>/`. Le champ `fixtures` de la pièce pointe vers ce
nom ; à défaut, le nom de la pièce est utilisé.

## fiche.json

```json
{
  "slug": "echeances",
  "title": "Échéances du classeur",
  "objective": "Passe en revue tous les documents du classeur...",
  "as_of": "2026-11-20",
  "budget": 14,
  "fixtures": "archiviste",
  "passes": [{ "label": "passe unique", "conducteur": "conducteur.json" }]
}
```

- `as_of` : date de référence des calculs « jours restants ». La fixer rend la démonstration
  déterministe ; l'omettre utilise la date du jour.
- `budget` : nombre maximum d'appels d'outils. Au delà, le run s'arrête en `status: budget`
  (jamais un délai dépassé, jamais une boucle infinie).
- `passes` : une entrée = une passe. Deux entrées = pièce à deux passes, exécutées
  séquentiellement, avec comparaison des étapes et des erreurs.

## Conducteur

```json
{
  "steps": [
    { "thought": "Commencer par l'inventaire.", "tool": "classeur_lister", "args": { "dir": "." } },
    { "thought": "Lire le contrat.", "tool": "document_lire", "args": { "path": "assurance-habitation.pdf" } },
    { "thought": "C'est fait.", "final": "Franchise : 250 EUR (source : assurance-habitation.pdf)." }
  ]
}
```

Une étape porte soit `tool` + `args`, soit `final`. La dernière étape doit être un `final`,
sinon `valider` le signale.

`valider` vérifie trois choses, sans exécuter la pièce :

1. la conducteur est un JSON valide, non vide ;
2. chaque outil cité existe dans le registre ;
3. les arguments correspondent exactement à la signature de l'outil (ni manquant, ni en
   trop), ce qui évite les fautes de frappe silencieuses.

## Créer une pièce vide

```bash
python -m archiviste creer ma-piece
```

Le dossier est créé avec un `fiche.json` et une conducteur minimale. Il reste à déposer
les documents dans `documents/` et à écrire les étapes.

## Ajouter un outil

Un outil est une fonction décorée dans `archiviste/outils.py` :

```python
@registre.outil("ma_fonction", "Ce qu'elle fait, en une phrase.", required=("arg",), optional={"opt": 0})
def ma_fonction(arg: str, opt: int = 0) -> dict:
    ...
```

La signature affichée à l'agent (`specs()`) est dérivée des paramètres : c'est elle que le
modèle reçoit en mode `--modele`, et c'est elle que `valider` compare aux conducteurs. Une
exception levée dans l'outil devient une observation d'erreur, jamais un arrêt du run.

Deux règles pour un nouvel outil :

- **écrire dans l'atelier uniquement**, via `ctx.atelier.resolve(chemin)` : un chemin
  absolu ou une remontée `../` est refusé avant toute lecture ;
- **échouer franchement**. Un outil qui ne sait pas faire doit lever `ErreurOutil` avec un
  message lisible, pas renvoyer un résultat plausible. C'est ce que fait `document_lire`
  sur un PDF sans couche texte.
