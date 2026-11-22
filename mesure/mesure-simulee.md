# Rapport de mesure — Classeur

> **RAPPORT SIMULÉ — ne mesure rien.** L'endpoint interrogé renvoie des décisions préenregistrées. Ce fichier prouve seulement que le harness s'exécute de bout en bout.

Backend : `http://127.0.0.1:8099` · modèle `qwen2.5-coder:7b` · 10 tâches.

- Exactitude (correspondance exacte) : **10/10 (100 %)**
- Latence p50 / p95 : **1 ms / 1 ms**
- Coût pour 1 000 runs : **0.00 €** (endpoint local : 0 € de tokens, hors matériel et électricité)

| # | Décision attendue | Obtenu | OK | ms |
| --- | --- | --- | --- | --- |
| 1 | echeance_ajouter | echeance_ajouter | oui | 1 |
| 2 | echeance_ajouter | echeance_ajouter | oui | 1 |
| 3 | __final__ | final | oui | 1 |
| 4 | echeance_ajouter | echeance_ajouter | oui | 1 |
| 5 | rapport_ecrire | rapport_ecrire | oui | 1 |
| 6 | alerte_emettre | alerte_emettre | oui | 1 |
| 7 | __final__ | final | oui | 1 |
| 8 | echeance_ajouter | echeance_ajouter | oui | 0 |
| 9 | classeur_lister | classeur_lister | oui | 0 |
| 10 | document_lire | document_lire | oui | 1 |

## Ce que ces chiffres ne disent pas

- Jeu de tâches volontairement court (10 décisions) et fermé : il mesure le respect du contrat JSON et des signatures d'outils, pas la qualité rédactionnelle d'un briefing.
- La latence inclut la variance réseau et le chargement du modèle à froid ; un premier appel sur un modèle non chargé peut être dix fois plus lent.
- Le coût local exclut l'amortissement du matériel, l'électricité et le temps d'installation : « 0 € de tokens » n'est pas « gratuit ».
- Si ce rapport a été produit contre `mesure/serveur_simule.py`, l'endpoint répond des réponses préenregistrées : le score vaut **zéro** et ne sert qu'à vérifier que la CI exécute le harness.

