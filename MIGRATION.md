# Passer le dépôt sur un autre compte GitHub

Tout est prêt pour un dépôt sur un compte qui n'est pas celui qui a servi au développement.
Il reste quatre choses à faire, dans cet ordre.

## 1. Réécrire le compte dans les fichiers

```bash
./scripts/migrer-vers-compte.sh <compte-github> [nom-du-depot]
```

Sans second argument, le dépôt s'appelle `classeur`. Le script réécrit les fichiers et
échoue s'il reste un marqueur `VOTRE-COMPTE`.

## 2. Les endroits exacts qui contiennent le nom du compte

Cette liste est celle d'avant le script : elle sert à vérifier qu'il n'a rien oublié.

| Fichier | Ce qui change | Pourquoi |
| --- | --- | --- |
| `README.md` | badge CI (deux fois : image et lien) | le badge pointe sur l'Action du dépôt |
| `README.md` | `docker run ... ghcr.io/VOTRE-COMPTE/classeur:latest` | l'image est publiée par la CI du compte |
| `README.md` | `git clone https://github.com/VOTRE-COMPTE/classeur` et `cd classeur` | commande de démarrage |
| `README.en.md` | les trois mêmes lignes, en anglais | version anglaise |
| `compose.yaml` | `image: ghcr.io/VOTRE-COMPTE/classeur:latest` | `docker compose up` tire cette image |
| `docs/DEMO.md` | `docker run ... ghcr.io/VOTRE-COMPTE/classeur:latest` | la démonstration en trois minutes |
| `scripts/migrer-vers-compte.sh` | n'est **pas** modifié par lui-même | il contient le marqueur par construction |

Rien d'autre ne porte le nom du compte :

- **`LICENSE`** dit « Classeur contributors », pas un nom de personne ;
- **`.github/workflows/ci.yml`** utilise `${{ github.repository_owner }}` et
  `${{ github.actor }}` : le nom du compte est lu à l'exécution, il n'est écrit nulle part ;
- **aucun Docker Hub** : la publication se fait sur GHCR uniquement, donc aucun
  `secrets.DOCKERHUB_*` à créer ;
- **aucune adresse, aucun courriel, aucun identifiant** dans le dépôt.

## 3. Créer le dépôt et pousser

```bash
git init -b main            # si le dépôt local n'existe pas encore
git add -A
git commit -m "Le Classeur — agent local d'échéances (candidature AI Entry)"
git remote add origin git@github.com:<compte>/classeur.git
git push -u origin main
```

Le dépôt doit être **public** : le palier AI Entry demande un lien consultable.

## 4. Après le premier push

1. **La CI tourne** (onglet Actions). Trois jobs : tests, image, fumée. Le badge du README
   passe au vert quand tout est bon.
2. **Rendre le paquet public.** Un paquet GHCR naît privé, même dans un dépôt public. Sans
   cette étape, `docker run` renvoie `denied` à un jury pourtant muni du bon lien :
   onglet *Packages* → le paquet `classeur` → *Package settings* → *Change visibility* →
   *Public*.
3. **Vérifier l'image** : `docker run --rm -p 8080:8080 ghcr.io/<compte>/classeur:latest`
   doit démarrer sans `docker login`.
4. **Vérifier le badge** dans le README publié : s'il est cassé, c'est que le nom du dépôt
   dans l'URL ne correspond pas.

## 5. Ce qu'il faut supprimer de l'ancien compte

Un même projet publié sur deux comptes se lit comme une candidature déposée deux fois.
Avant de soumettre :

- supprimer (ou passer en privé) le dépôt `hollow313/ASUS-Agent-Computer-Challenge---AI-Entry`
  et son paquet `holloow313/asus-agent-computer-challenge-ai-entry` sur Docker Hub ;
- ne laisser qu'un seul dépôt public pour cette candidature.

Le règlement du concours demande un projet et un palier. Deux dépôts ouverts du même projet
sont le genre de détail qui se remarque.

## 6. Vérification finale, la veille de la soumission

```bash
# 1. aucun marqueur
grep -rn "VOTRE-COMPTE" --exclude-dir=.git . || echo "ok"

# 2. les tests passent, en local
python -m unittest discover -s essais

# 3. l'image se lance et répond
docker run --rm -d --name classeur -p 8080:8080 ghcr.io/<compte>/classeur:latest
curl -fsS http://127.0.0.1:8080/healthz && docker rm -f classeur

# 4. les liens du README répondent autre chose que 404
curl -o /dev/null -w '%{http_code}\n' https://github.com/<compte>/classeur
```
