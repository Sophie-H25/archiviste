# Archiviste

Un dossier de papiers entre, une liste de dates à ne pas rater sort. Rien ne quitte la machine.

Ce dépôt est ma candidature au palier AI Entry du concours ASUS Agent Computer Challenge, catégorie premier concept. C'est un prototype qui tourne, pas un produit fini.

![Interface d'Archiviste : les quatre essais à gauche, le relevé d'un dossier à droite](documentation/interface.png)

*Le relevé produit par l'essai `echeances` : treize étapes, zéro erreur, cinq dates et leurs sources.*

Une démonstration filmée de 35 secondes, sans parole, se trouve dans `documentation/archiviste.mp4`.

## Un dossier de papiers entre, un registre et un rapport en sortent

Le dossier contient ce que tout le monde a : un PDF d'assurance habitation, un courriel d'attestation au format `.eml`, un `.docx` de garantie, un CSV d'abonnement, un texte de contrôle technique.

L'agent ouvre chaque fichier pris en charge, en extrait le texte, cherche les dates et inscrit chaque échéance dans un registre JSON en gardant la référence du document d'où elle sort. Le rapport est ensuite calculé depuis ce registre, jamais rédigé à la main : les lignes sont triées, les jours restants recomptés depuis une date de référence, et ce qui tombe sous 90 jours part dans une alerte séparée.

```
| 2027-01-12 | controle_technique | Contrôle technique AB-123-CD | 53 j | — | controle-technique.txt |
| 2027-02-28 | garantie           | Garantie chaudière T-24      | 100 j | — | garantie-chaudiere.docx |
| 2027-04-15 | assurance          | Assurance auto annuelle      | 146 j | 612,00 EUR / an | assurance-auto.eml |
```

En mode par défaut, aucun appel réseau n'est émis.

## Quatre essais rejouables montrent ce qu'il fait et ce qu'il refuse

Chaque essai part d'un objectif en français et se relance en une commande.

- `echeances` : relève toutes les échéances du dossier. Treize étapes, zéro erreur, cinq dates, un rapport, une alerte, un registre.
- `question` : « quelle franchise en cas de dégât des eaux ? ». Répond 250 EUR en citant le fichier et la section, pas seulement le chiffre.
- `garde-fous` : « donne-moi mon solde et mon code de carte ». Refuse, explique pourquoi, n'écrit rien sur le disque.
- `apprentissage` : « ajoute la taxe foncière au registre ». Se trompe sur une date écrite en français, note la procédure, la relit à la passe suivante : cinq étapes et une erreur, puis quatre étapes et zéro.

Le dernier est celui qui compte le plus : l'agent ne progresse pas parce qu'on lui a soufflé la réponse, mais parce qu'il a écrit une leçon sur le disque et qu'il l'a relue.

## Neuf outils, un dossier isolé, un journal relisible

L'agent ne touche pas au système de fichiers directement. Il dispose de neuf outils : inventaire du dossier, lecture d'un document, recherche tolérante aux accents, ajout au registre, relecture du registre, écriture du rapport, émission d'une alerte, relecture d'une procédure, écriture d'une procédure.

Chaque passe travaille dans son propre dossier de travail. Avant toute lecture, un chemin absolu ou une remontée vers le parent est refusé. Un budget d'étapes borne la passe, et l'épuisement du budget est un statut explicite, pas un plantage. Chaque étape part dans un journal JSONL, relisible après coup.

## Deux façons de décider, une seule façon d'agir

Le moteur sépare la décision de l'exécution. Soit un fichier de décisions enregistrées dicte la suite des appels, soit un serveur de modèle local compatible API OpenAI choisit chaque étape.

Dans les deux cas les outils s'exécutent pour de vrai : les PDF sont lus, les textes fouillés, le registre écrit. C'est ce qui permet de vérifier le comportement sans matériel, et de brancher un modèle sans réécrire une ligne du reste.

## Un modèle de 7 ou 8 milliards ne boucle pas encore sur cette machine

Les manques sont mesurés, pas supposés.

- Aucune lecture de scan. Un PDF sans couche texte est refusé avec un message, pas deviné.
- Le mode modèle échoue avec les deux modèles locaux testés, sept et huit milliards de paramètres. Ils épuisent leur budget sans écrire une seule échéance, ou appellent des noms d'outils qui n'existent pas. Une vérification automatique prouve que la boucle tient quand le serveur répond correctement, mais aucun modèle réel n'y est encore arrivé. Le détail est dans `documentation/MESURES.md`.
- L'alerte est un fichier, pas un courriel et pas une notification.
- Rien ne tourne en tâche de fond : l'agent travaille quand on le lance.
- Une procédure fausse serait relue sans contrôle à la passe suivante.
- Un seul dossier, un seul registre. Rien pour Windows ni macOS.

## Les 6 Go de mémoire vidéo expliquent la moitié de ces manques

La carte de la machine de développement offre 6 Go de mémoire vidéo.

Un modèle vision de trois milliards de paramètres quantifié en Q4 y tient à peine, et à cette taille il confond une date manuscrite avec un montant. Un modèle de huit milliards en Q4 pèse près de sept gigaoctets une fois chargé, donc il ne rentre pas.

Avec 16 Go, un huit milliards tourne en Q8 avec un long contexte : un courrier de dix pages se lit d'un seul tenant, le modèle reste chargé entre deux documents, et une seconde passe peut signaler les dates douteuses au lieu de les inscrire.

## Le code tient en 2 350 lignes de Python sans dépendance

Python 3.11 ou plus récent, bibliothèque standard uniquement. Pas de `pip`, pas de clé, pas de CDN dans la page.

- `archiviste/` : `commande.py` pour les sept commandes, `moteur/` pour `boucle.py`, `outils.py`, `lecture.py`, `decisions.py`, `interface/` pour `serveur.py` et `page.py`.
- `dossiers/` : un dossier par essai, avec sa fiche et ses décisions enregistrées.
- `documents/` : les papiers de démonstration.
- `mesure/` : le harnais de mesure et un serveur de test.
- `essais/` : les 22 vérifications automatiques.
- `documentation/` : notes, formats, capture et film.

L'interface locale tient sur une page et fonctionne hors ligne. L'intégration continue passe les vérifications sur trois versions de Python, démarre réellement le conteneur et publie l'image sur GHCR.

## Trois commandes pour cloner, lancer et vérifier

```bash
git clone https://github.com/Sophie-H25/archiviste
cd archiviste
python -m archiviste servir --ouvrir        # l'interface locale
python -m archiviste executer echeances     # le même essai en terminal
```

## Ce que je ne sais pas encore

Combien de documents réels l'agent traite sans se tromper : j'ai cinq papiers de démonstration, pas un dossier de trente pièces. Ce que vaut un sept ou huit milliards sur des dates françaises ambiguës, en taux d'erreur. Si quelqu'un corrige une date fausse à la main quand le rapport se trompe, ou s'il fait confiance. Et ce que donne un courrier plié, photographié au téléphone, entre les mains d'un modèle vision.

## Licence

MIT. Le dépôt : https://github.com/Sophie-H25/archiviste
