#!/usr/bin/env bash
# Remplace le compte GitHub « VOTRE-COMPTE » partout dans le dépôt.
#
#   ./scripts/migrer-vers-compte.sh <compte-github> [nom-du-depot]
#
# Exemple : ./scripts/migrer-vers-compte.sh marie-huon le-classeur
#
# Le script ne pousse rien et ne crée aucun dépôt : il réécrit les fichiers,
# vérifie qu'il ne reste aucun marqueur, puis affiche la marche à suivre.
set -euo pipefail

compte="${1:-}"
depot="${2:-classeur}"

if [ -z "$compte" ]; then
  echo "usage : $0 <compte-github> [nom-du-depot]" >&2
  exit 2
fi

cd "$(dirname "$0")/.."

echo "→ remplacement VOTRE-COMPTE/classeur → ${compte}/${depot}"
grep -rl "VOTRE-COMPTE" --exclude-dir=.git . | while IFS= read -r fichier; do
  sed -i.bak "s#VOTRE-COMPTE/classeur#${compte}/${depot}#g; s#cd classeur\$#cd ${depot}#" "$fichier"
  rm -f "${fichier}.bak"
  echo "   ${fichier}"
done

# Le nom du dossier cloné suit le nom du dépôt.
sed -i.bak "s#^cd classeur\$#cd ${depot}#" README.md README.en.md 2>/dev/null || true
rm -f README.md.bak README.en.md.bak

echo
if grep -rn "VOTRE-COMPTE" --exclude-dir=.git . >/dev/null 2>&1; then
  echo "✗ il reste des marqueurs :" >&2
  grep -rn "VOTRE-COMPTE" --exclude-dir=.git . >&2
  exit 1
fi
echo "✓ aucun marqueur restant"

echo
echo "Vérifications utiles :"
echo "   grep -rn 'ghcr.io/${compte}' README.md compose.yaml docs/"
echo "   grep -rn 'github.com/${compte}' README.md"
echo
echo "Ensuite, à la main :"
echo "   1. créer le dépôt ${compte}/${depot} (public, sans README ni licence)"
echo "   2. git remote add origin git@github.com:${compte}/${depot}.git"
echo "   3. git push -u origin main"
echo "   4. attendre la CI, puis rendre le paquet ghcr.io/${compte}/${depot} public"
echo "      (onglet Packages → Package settings → Change visibility → Public)"
