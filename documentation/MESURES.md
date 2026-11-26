# Ce que donne un vrai modèle local

Trois runs réels, en mode `--modele`, contre LM Studio sur le réseau local, le 22 novembre 2026.
Même objectif à chaque fois : « relève toutes les échéances du classeur ». Aucune décision
préenregistrée, les outils s'exécutent pour de vrai.

| Modèle | Budget | Étapes utilisées | Erreurs | Statut | Ce qui s'est passé |
| --- | --- | --- | --- | --- | --- |
| `qwen2.5-coder-7b-instruct` | 14 | 14 | 3 | budget épuisé | lit les 5 documents, puis se met à relire et à inventer des outils (`list_documents`, `documents_examiner`) au lieu d'écrire une échéance |
| `qwen2.5-coder-7b-instruct` | 14 | 14 | 5 | budget épuisé | même schéma : deux relectures du même CSV, un outil inventé, aucune écriture |
| `qwen3-vl-8b` | 22 | 22 | 6 | budget épuisé | lit les documents, appelle `echeance_lister` trois fois, invente `relevé_echéances`, propose `procedure_noter` sur un constat faux (« aucun document avec une échéance ») |

## Ce que ça dit

Le harnais est réel : les appels d'outils partent, les fichiers sont lus, les erreurs sont
celles du modèle et pas celles du code. Un outil inventé produit une observation d'erreur,
l'agent la voit, et il continue : le mécanisme de correction existe.

Ce qui ne marche pas encore, c'est la décision. Un modèle de 7 à 8 milliards de paramètres,
même bon en code, ne tient pas le contrat : il oublie qu'il a déjà lu un fichier, traduit le
nom des outils, et termine parfois en affirmant qu'il n'a rien trouvé alors que les dates
étaient dans les documents qu'il venait de lire. C'est exactement le manque n°2 du README.

Deux pistes, dans cet ordre :

1. envoyer les signatures d'outils au format `tools` de l'API (function calling) plutôt que
   dans le prompt, ce que LM Studio et Ollama exposent tous les deux ;
2. un modèle plus gros, ce qui ramène la question du matériel.

En attendant, la démonstration reproductible est le mode conducteur : les décisions sont
enregistrées, les effets sont réels, et le résultat est vérifiable à chaque run.

## Le format `tools` de l'API

Les signatures partent désormais dans le champ `tools` de `chat/completions`, et la boucle lit les
`tool_calls` de la réponse. Vérifié par une vérification automatique qui fait tourner l'essai
`echeances` complet contre `mesure/serveur_simule.py`, lequel répond en `tool_calls` : quatorze
étapes, registre rempli, rapport écrit, zéro erreur, sans modèle.

Avec LM Studio, `qwen2.5-coder-7b-instruct` accepte le champ `tools` mais répond le JSON dans le
texte au lieu d'émettre des `tool_calls` : la boucle retombe alors sur son analyse de texte, ce qui
fonctionne mais ne prouve rien de plus. Et `qwen/qwen3-vl-8b` ne se charge pas du tout sur cette
machine : `Engine protocol startup was aborted`, faute de mémoire vidéo. Les deux constats datent du
26 novembre 2026.
