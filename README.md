**Français** · [English](README.en.md)

# Archiviste

Un agent qui lit un classeur de papiers administratifs et sort la liste des dates qui vont coûter cher, sans qu'aucun document ne quitte la machine.

**Ce que c'est, et ce que ce n'est pas.** C'est une candidature au palier **AI Entry** du [ASUS Agent Computer Challenge](https://fr.asus.click/ACC_CWCT), celui des premiers concepts et des premières expérimentations. Ce n'est pas un produit : c'est un prototype qui tourne, avec quatre essais rejouables, vingt et une vérifications automatiques et une image Docker. Il est incomplet, et la partie [Ce qui bloque aujourd'hui](#ce-qui-bloque-aujourdhui) dit exactement où.

---

## L'idée de départ

Un classeur, c'est cinq à trente papiers qui arrivent dans quatre formats différents : le PDF de l'assurance, le courriel de l'attestation, le `.docx` de la garantie, le CSV de l'abonnement. Les dates qui coûtent de l'argent sont enterrées dedans : la reconduction tacite, la fin de garantie de la chaudière, le préavis de deux mois.

Personne ne relit ce tas de fichiers. Le résultat est connu : un abonnement se reconduit, une garantie expire, un contrôle technique passe en retard.

Les outils qui savent lire ces documents existent déjà, mais ils demandent de les envoyer quelque part. Pour un avis d'imposition ou un contrat d'assurance, l'envoi est justement ce qu'on ne veut pas faire. D'où le sujet : est-ce qu'un agent local, sur un PC normal, peut faire ce travail tout seul ?

## Ce que j'ai réussi à faire marcher

```bash
git clone https://github.com/Sophie-H25/archiviste
cd archiviste
python -m archiviste servir --ouvrir          # interface locale
python -m archiviste executer echeances       # la même démonstration en terminal
```

Aucune dépendance à installer, aucune clé, aucun compte, rien à compiler : un Python 3.11 ou plus récent et c'est tout.

```bash
python -m unittest discover -s essais      # 21 vérifications, 0,6 s
```

Une image Docker existe (`compose.yaml`, publiée par la CI) pour qui préfère ça, mais elle n'est pas nécessaire.

Ce que l'agent fait vraiment, et comment le vérifier :

- il lit quatre formats pour de vrai, PDF avec couche texte, DOCX, courriel `.eml`, CSV : cinq documents, zéro erreur, en moins d'une demi-seconde ;
- il écrit les dates trouvées dans un registre JSON, refuse les doublons et les dates en français non convertibles, puis calcule un rapport avec les jours restants, depuis une date de référence fixée ;
- il produit une alerte à 90 jours, qui ne contient que ce qui tombe dans la fenêtre ;
- il répond à une question en citant le fichier et la section, pas seulement le chiffre ;
- il refuse une demande hors périmètre (un solde bancaire, un code de carte) au lieu d'inventer une valeur ;
- il écrit une procédure après une erreur, la relit au run suivant, et l'écart se mesure : cinq étapes et une erreur, puis quatre étapes et zéro.

## Les quatre essais

Tous rejouables sans modèle, en une commande chacun.

| Pièce | Ce que je demande | Ce qui sort |
| --- | --- | --- |
| `echeances` | « Relève toutes les échéances du classeur » | 13 étapes, 0 erreur, un rapport trié, une alerte, un registre |
| `question` | « Quelle franchise en cas de dégât des eaux ? » | 250 EUR, avec le fichier et la section en source |
| `garde-fous` | « Donne-moi mon solde et mon code de carte » | un refus argumenté, aucune pièce écrite |
| `apprentissage` | « Ajoute la taxe foncière au registre » | deux passes comparées, une procédure persistée sur disque |

Les documents de démonstration sont fabriqués : identités inventées, domaines en `.invalid`, immatriculation d'exemple. `python outils_dev/fabriquer_documents.py` les régénère.

## Ce qui bloque aujourd'hui

C'est la liste honnête, et c'est elle qui justifie le palier AI Entry.

1. **Les scans.** Un papier administratif arrive souvent en photo ou en PDF sans couche texte. Aujourd'hui, l'agent le dit et s'arrête. Lire une image demande un modèle vision, et la machine sur laquelle je développe n'a pas la mémoire vidéo pour ça. C'est le blocage numéro un, et il n'est pas logiciel.
2. **Le mode modèle est branché, et il échoue encore.** L'agent peut laisser un serveur compatible OpenAI (Ollama, LM Studio, vLLM) choisir ses étapes, et les outils s'exécutent pareil. Mesuré sur deux modèles locaux de 7 et 8 milliards de paramètres : les deux épuisent leur budget sans écrire une seule échéance, entre outils inventés et relectures du même fichier. Le détail est dans [`docs/MESURE-LIVE.md`](docs/MESURE-LIVE.md). La décision est le point faible, pas la boucle.
3. **L'alerte est un fichier.** Pas de courriel, pas de notification, pas d'agenda. Un fichier markdown qu'il faut penser à ouvrir.
4. **Rien ne tourne tout seul.** L'agent travaille quand on le lance. Pas de scan quotidien, pas d'état « déjà signalé ».
5. **Les procédures apprises ne sont pas vérifiées.** Si l'agent écrit une leçon fausse, elle sera relue et appliquée quand même.
6. **Un seul classeur, un seul dossier.** Pas de séparation famille, logement, voiture.
7. **Rien pour Windows ou macOS.** Le code est portable et l'image Docker tourne, mais quelqu'un qui ne code pas n'a pas de double-clic à se mettre sous la dent.

## Avec une machine qui tient la charge

Le prototype tourne sur une machine modeste, sans mémoire vidéo suffisante pour un modèle vision. Ce n'est pas une gêne de confort, c'est ce qui ferme le premier usage réel : un modèle vision de 3 milliards de paramètres en Q4 demande environ 3,2 Go une fois le contexte, le cache et le runtime comptés, donc il ne rentre pas.

Avec 16 Go de VRAM, trois choses changent d'un coup :

- les **scans** sont lus au lieu d'être refusés, donc un classeur réel devient traitable ;
- les **courriers multipages** sont jugés page par page, au lieu d'échantillonner celles qui portent déjà du texte ;
- le modèle **reste chargé** entre deux documents, et une seconde passe peut vérifier une date ambiguë sans repayer le chargement.

C'est exactement le périmètre du manque n°1, et c'est pour ça que le projet demande du matériel plutôt que du temps.

Le harnais de mesure est fourni pour que ces chiffres se vérifient, et pas seulement pour être crus :

```bash
python -m archiviste mesurer --url http://127.0.0.1:11434 --nom-modele qwen2.5-coder-7b-instruct --sortie mesure/mesure.md
```

Dix décisions courtes tirées du domaine, notées par correspondance exacte (jamais un modèle juge), avec le taux de réussite, les latences p50 et p95, et un coût pour mille runs. Le rapport généré contient sa section « ce que ces chiffres ne disent pas ». Le fichier `mesure/mesure-simulee.md` est produit contre un serveur simulé : il ne mesure rien, il prouve que la chaîne s'exécute, et il l'écrit en tête.

## Comment c'est fait

```
archiviste/
  commande.py          les sept commandes : lister, valider, creer, executer, servir, mesurer, modeles
  moteur/
    boucle.py          registre d'outils, atelier du run, budget, journal, exécution
    outils.py          les neuf outils métier (lister, lire, chercher, registre, rapport, alerte, mémoire)
    lecture.py         extraction de texte : PDF, DOCX, .eml, CSV, texte
    decisions.py       deux façons de décider : cassette enregistrée, ou serveur de modèle
  interface/
    serveur.py         HTTP et API JSON, bibliothèque standard
    page.py            une page, hors ligne, sans CDN
dossiers/              une pièce par dossier : objectif, budget, cassette
documents/             papiers de démonstration, synthétiques
mesure/                harnais de mesure et serveur simulé
essais/                les vérifications automatiques
```

Deux façons de décider, une seule façon d'agir. En mode cassette, un fichier enregistre les décisions et les outils s'exécutent quand même : les PDF sont réellement lus, le registre réellement écrit. En mode modèle, c'est le serveur local qui choisit chaque étape. Le reste du code ne fait pas la différence, et c'est ce qui rend la démonstration rejouable sans matériel.

Deux garde-fous, testés tous les deux : le budget d'étapes, qui arrête un run qui tourne en rond avec un statut explicite, et le périmètre du dossier de travail, qui refuse un chemin absolu ou une remontée `../` avant toute lecture. Chaque étape est écrite dans un journal JSONL, relisible.

2 350 lignes de Python, aucune dépendance tierce : l'extraction PDF, le serveur et l'interface tiennent dans la bibliothèque standard. Pas de `pip install`, pas de `requirements.txt`, pas de CDN dans la page.

## Vérifier en trois commandes

```bash
python -m unittest discover -s essais       # 21 vérifications, 0,56 s
python -m archiviste valider                  # les cassettes contre les signatures d'outils
python -m archiviste executer echeances       # la pièce principale, de bout en bout
```

Les vérifications couvrent les quatre pièces, le contenu des livrables, le refus de sortie de périmètre, le budget épuisé, un outil inconnu, l'extraction PDF et DOCX, et l'API qui sert un livrable en `charset=utf-8`. La CI rejoue tout ça sur trois versions de Python, construit l'image et démarre réellement le conteneur pour lancer une pièce par l'API.

## Ce que je ne sais pas encore

- Combien de documents réels l'agent traite sans se tromper : j'ai testé sur cinq papiers fabriqués, pas sur un vrai archiviste de trente pièces.
- Ce que valent les décisions d'un 3B ou d'un 7B sur des dates françaises ambiguës, en taux d'erreur mesuré et pas en impression.
- Si les gens corrigent une date fausse à la main ou s'ils font confiance au rapport. Il n'y a pas encore d'interface pour corriger.
- Ce qu'un courrier scanné, plié, photographié au téléphone donne entre les mains d'un modèle vision. C'est la prochaine mesure, et elle a besoin de matériel.

## Licence

MIT, voir [LICENSE](LICENSE). Les documents de démonstration sont fabriqués ; aucune donnée réelle ne figure dans ce dépôt.
