# Journal des versions

## 0.1.0 — premier POC

Première version publiable, celle qui accompagne la candidature AI Entry.

- quatre essais rejouables sans modèle : `echeances`, `question`, `garde-fous`, `apprentissage` ;
- extraction de texte réelle pour PDF avec couche texte, DOCX, courriel `.eml` et CSV ;
- registre JSON, rapport calculé et alerte à 90 jours écrits sur le disque ;
- budget d'étapes, atelier par passe, journal JSONL, refus de sortie de périmètre ;
- mémoire procédurale : une leçon écrite après une erreur, relue à l'essai suivant ;
- interface locale d'une page, sans CDN, et serveur HTTP en bibliothèque standard ;
- 21 vérifications automatiques, CI sur trois versions de Python, image GHCR.

Ce qui manque, et qui viendra ensuite : lecture des scans, rappels réels, passe
quotidienne, et une mesure sérieuse du mode modèle.
