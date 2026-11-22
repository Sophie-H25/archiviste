# La démonstration en trois minutes

Pour un relecteur pressé. Rien à installer si Docker est présent.

## 1. Lancer (20 s)

```bash
docker run --rm -p 8080:8080 -v archiviste-data:/data ghcr.io/Sophie-H25/archiviste:latest
```

Sans Docker (Python 3.11 ou plus, aucune dépendance) :

```bash
python -m archiviste servir --ouvrir
```

La page s'ouvre sur une chemise cartonnée, quatre pièces à gauche, un relevé vide à droite.

## 2. La pièce principale (30 s)

Cliquer **Ouvrir la pièce** sur « Échéances du classeur ».

Attendu : un tampon `TERMINÉ`, 13 étapes, 0 erreur, trois pièces au dossier
(`livrables/echeances.md`, `alertes/alertes-90j.md`, `registre.json`).

Cliquer sur `livrables/echeances.md` : la table apparaît dans le lecteur, triée, avec les
jours restants calculés par rapport au 20 novembre 2026. Cliquer sur
`alertes/alertes-90j.md` : seule la première échéance y figure, les autres sont au delà de
90 jours.

Le même résultat en terminal, sans interface :

```bash
python -m archiviste executer echeances
```

## 3. La pièce qui compte (40 s)

Cliquer **Ouvrir la pièce** sur « Apprentissage d'une procédure ».

Attendu : deux blocs de journal et une ligne de comparaison

```
Apprentissage : passe 1 — sans procédure → 5 étapes · 1 erreur(s) | passe 2 — avec la procédure apprise → 4 étapes · 0 erreur(s)
```

Puis, dans le panneau « Procédures apprises » (colonne de gauche), la procédure
`dates en langage naturel`, écrite par l'agent. Elle est sur le disque :

```bash
ls data/skills/apprentissage/
```

Relancer la pièce : la procédure est toujours là, elle survit au run.

## 4. Les garde-fous (20 s)

Cliquer **Ouvrir la pièce** sur « Demande hors périmètre ». L'agent refuse de donner un
solde bancaire et un code de carte, explique ce qu'il peut faire à la place, et n'écrit
aucune pièce au dossier. Aucune valeur n'est inventée.

Enchaîner sur « Question sur un document » : la franchise est donnée avec le fichier et la
section, pas seulement le chiffre.

## 5. Tests et validation (20 s)

```bash
python -m unittest discover -s essais -v
python -m archiviste valider
```

21 tests, environ 0,6 seconde. La CI exécute la même chose sur trois versions de Python,
puis démarre réellement le conteneur et lance une pièce par l'API.

## 6. Facultatif : brancher un vrai modèle (5 min)

1. Démarrer Ollama, LM Studio ou vLLM.
2. Ouvrir « Régler un serveur de modèle local » dans la colonne de gauche.
3. Renseigner l'URL (par exemple `http://127.0.0.1:11434` ou `http://127.0.0.1:1234`).
4. Cliquer **Sonder le serveur** : la liste des modèles réellement exposés s'affiche, le
   premier est prérempli.
5. Cliquer **Confier au modèle local** sur une pièce.

En mode modèle, les décisions viennent du modèle, les outils s'exécutent pour de vrai. Un
petit modèle 3B se trompe parfois d'argument : l'agent reçoit une observation d'erreur, la
journalise, et peut corriger. C'est le comportement attendu, pas un plantage.

```bash
python -m archiviste mesurer --url http://127.0.0.1:11434 --nom-modele qwen2.5-coder-7b-instruct
```

## Ce qui peut coincer

- **Port 8080 déjà pris** : `python -m archiviste servir --port 8090`.
- **`/v1` oublié dans l'URL** : le code le rajoute, mais une URL en `https://` vers un
  serveur local en `http://` échoue. Utiliser `http://`.
- **Image Docker absente** : `docker compose up --build` construit l'image localement.
- **Aucune procédure apprise au premier lancement** : normal, elle n'apparaît qu'après la
  pièce « Apprentissage ».
