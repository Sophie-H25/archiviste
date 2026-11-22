"""Outils de l'agent Classeur : lecture de documents, recherche, registre, rapports.

Tous les outils font un travail réel sur le disque du atelier du run : un document
est réellement extrait, le registre est réellement écrit, le rapport est
réellement généré depuis le registre. Le mode « cassette » ne remplace que le
choix des étapes, pas leur exécution.
"""

from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from .lecture import SUPPORTED, ExtractionError, extraire_texte
from .boucle import Contexte, Registre, ErreurAtelier, ErreurOutil, normalize

KINDS = {
    "assurance": "assurance (auto, habitation, santé)",
    "controle_technique": "contrôle technique, entretien obligatoire",
    "garantie": "garantie d'un appareil ou de travaux",
    "abonnement": "abonnement ou reconduction tacite",
    "taxe": "taxe, impôt, redevance",
    "autre": "tout le reste",
}
MAX_READ_CHARS = 6000


def _ledger_path(ctx: Contexte) -> Path:
    return ctx.atelier.root / "registre.json"


def _load_ledger(ctx: Contexte) -> dict[str, Any]:
    path = _ledger_path(ctx)
    if not path.is_file():
        return {"items": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        raise ErreurOutil("registre illisible (JSON invalide) : relancer l'ingestion")
    if not isinstance(data, dict):
        raise ErreurOutil("registre illisible : structure inattendue")
    data.setdefault("items", [])
    return data


def _save_ledger(ctx: Contexte, data: dict[str, Any]) -> None:
    _ledger_path(ctx).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _parse_due(due: Any) -> dt.date:
    raw = str(due).strip()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
        raise ErreurOutil(
            f"due : format ISO AAAA-MM-JJ attendu, reçu {raw!r}. "
            "Une date en langage naturel doit d'abord être convertie en date réelle."
        )
    try:
        return dt.date.fromisoformat(raw)
    except ValueError as exc:
        raise ErreurOutil(f"due : date inexistante ({raw}) — {exc}") from exc


def _days_left(due: dt.date, as_of: dt.date) -> int:
    return (due - as_of).days


def _docs(ctx: Contexte) -> list[Path]:
    allowed = {s.lstrip(".") for s in SUPPORTED}
    out = []
    for path in sorted(ctx.atelier.root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(ctx.atelier.root).as_posix()
        if rel.startswith(("livrables/", "alertes/")) or rel == "registre.json":
            continue
        if path.suffix.lower().lstrip(".") in allowed:
            out.append(path)
    return out


def construire_registre(reg: Registre, ctx: Contexte) -> Registre:
    # -- mémoire procédurale -------------------------------------------------- #
    @reg.tool(
        "procedure_relire",
        "Relit les procédures apprises sur un sujet. À appeler en premier quand une difficulté connue peut se représenter.",
        required=("topic",),
        optional={"limit": 3},
    )
    def procedure_relire(topic: str, limit: int = 3) -> dict[str, Any]:
        found = ctx.skills.recall(topic, int(limit))
        return {"procedures": found, "found": len(found)}

    @reg.tool(
        "procedure_noter",
        "Écrit une procédure réutilisable (leçon d'une erreur ou d'une découverte coûteuse). Elle sera relue par les runs suivants.",
        required=("name", "content"),
    )
    def procedure_noter(name: str, content: str) -> dict[str, Any]:
        if len(content.strip()) < 20:
            raise ErreurOutil("procédure trop courte : décrire le symptôme, la cause et la règle à appliquer")
        return ctx.skills.write(name, content)

    # -- exploration ---------------------------------------------------------- #
    @reg.tool(
        "classeur_lister",
        "Liste les fichiers du classeur (récursif) avec leur taille.",
        optional={"dir": "."},
    )
    def classeur_lister(dir: str = ".") -> dict[str, Any]:
        base = ctx.atelier.resolve(dir)
        if not base.is_dir():
            raise ErreurOutil(f"répertoire introuvable : {dir}")
        rows = []
        for path in sorted(base.rglob("*")):
            if path.is_file():
                rows.append(
                    {
                        "path": path.relative_to(ctx.atelier.root).as_posix(),
                        "bytes": path.stat().st_size,
                        "format": path.suffix.lower() or "?",
                    }
                )
        return {"dir": dir, "count": len(rows), "files": rows}

    @reg.tool(
        "document_lire",
        "Extrait le texte d'un document (txt, md, csv, eml, html, pdf, docx). Le texte est tronqué à 6000 caractères.",
        required=("path",),
    )
    def document_lire(path: str) -> dict[str, Any]:
        target = ctx.atelier.resolve(path)
        if not target.is_file():
            raise ErreurOutil(f"document introuvable : {path}")
        try:
            text = extraire_texte(target)
        except (ExtractionError, OSError) as exc:
            raise ErreurOutil(str(exc)) from exc
        return {
            "path": path,
            "format": target.suffix.lower(),
            "chars": len(text),
            "truncated": len(text) > MAX_READ_CHARS,
            "text": text[:MAX_READ_CHARS],
        }

    @reg.tool(
        "document_chercher",
        "Recherche plein texte dans le classeur et renvoie des extraits avec leur source (fichier + position).",
        required=("query",),
        optional={"limit": 5},
    )
    def document_chercher(query: str, limit: int = 5) -> dict[str, Any]:
        tokens = [t for t in re.split(r"\W+", normalize(query)) if len(t) > 2]
        if not tokens:
            raise ErreurOutil("requête vide ou trop courte (3 caractères minimum par mot)")
        hits = []
        for path in _docs(ctx):
            try:
                text = extraire_texte(path)
            except (ExtractionError, OSError):
                continue
            haystack = normalize(text)
            score = sum(haystack.count(token) for token in tokens)
            if not score:
                continue
            first = min((haystack.find(t) for t in tokens if haystack.find(t) >= 0), default=0)
            start = max(0, first - 120)
            snippet = re.sub(r"\s+", " ", text[start : start + 320]).strip()
            hits.append(
                {
                    "source": path.relative_to(ctx.atelier.root).as_posix(),
                    "score": score,
                    "offset": first,
                    "snippet": snippet,
                }
            )
        hits.sort(key=lambda h: (-h["score"], h["source"]))
        return {"query": query, "terms": tokens, "count": len(hits), "hits": hits[: int(limit)]}

    # -- registre des échéances ---------------------------------------------- #
    @reg.tool(
        "echeance_ajouter",
        "Ajoute une échéance au registre (date ISO obligatoire). Refuse les doublons et les dates impossibles.",
        required=("kind", "label", "due", "source"),
        optional={"amount": "", "note": ""},
    )
    def echeance_ajouter(kind: str, label: str, due: str, source: str, amount: str = "", note: str = "") -> dict[str, Any]:
        kind_key = normalize(kind).strip()
        if kind_key not in KINDS:
            raise ErreurOutil(f"kind inconnu : {kind!r} — valeurs acceptées : {', '.join(sorted(KINDS))}")
        due_date = _parse_due(due)
        ctx.atelier.resolve(source)
        if not str(label).strip():
            raise ErreurOutil("label vide")
        data = _load_ledger(ctx)
        for item in data["items"]:
            if item["label"].strip().lower() == str(label).strip().lower() and item["due"] == due_date.isoformat():
                return {"duplicate": True, "item": item, "message": "échéance déjà présente, rien n'a été ajouté"}
        item = {
            "id": f"E{len(data['items']) + 1:02d}",
            "kind": kind_key,
            "label": str(label).strip(),
            "due": due_date.isoformat(),
            "source": source,
            "amount": str(amount).strip(),
            "note": str(note).strip(),
            "days_left": _days_left(due_date, ctx.as_of),
            "added_by": "classeur",
        }
        data["items"].append(item)
        _save_ledger(ctx, data)
        return {"added": True, "item": item, "total": len(data["items"])}

    @reg.tool(
        "echeance_lister",
        "Relit le registre des échéances, trié par date.",
        optional={"within_days": 0},
    )
    def echeance_lister(within_days: int = 0) -> dict[str, Any]:
        data = _load_ledger(ctx)
        items = sorted(data["items"], key=lambda i: i["due"])
        for item in items:
            item["days_left"] = _days_left(dt.date.fromisoformat(item["due"]), ctx.as_of)
        if int(within_days) > 0:
            items = [i for i in items if 0 <= i["days_left"] <= int(within_days)]
        return {"as_of": ctx.as_of.isoformat(), "count": len(items), "items": items}

    # -- livrables ------------------------------------------------------------ #
    @reg.tool(
        "rapport_ecrire",
        "Génère le rapport markdown des échéances depuis le registre (table triée, jours restants, sources).",
        optional={"name": "echeances.md"},
    )
    def rapport_ecrire(name: str = "echeances.md") -> dict[str, Any]:
        data = _load_ledger(ctx)
        items = sorted(data["items"], key=lambda i: i["due"])
        if not items:
            raise ErreurOutil("registre vide : rien à rapporter, ajouter au moins une échéance")
        lines = [
            "# Échéances du classeur",
            "",
            f"Référence de calcul : **{ctx.as_of.isoformat()}** · {len(items)} échéances suivies · "
            "généré par l'agent Classeur, hors ligne.",
            "",
            "| Échéance | Type | Objet | Dans | Montant | Source |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
        for item in items:
            days = _days_left(dt.date.fromisoformat(item["due"]), ctx.as_of)
            if days < 0:
                state = f"échue depuis {abs(days)} j"
            elif days == 0:
                state = "**aujourd'hui**"
            else:
                state = f"{days} j"
            lines.append(
                f"| {item['due']} | {item['kind']} | {item['label']} | {state} | "
                f"{item['amount'] or '—'} | `{item['source']}` |"
            )
        soon = [i for i in items if 0 <= _days_left(dt.date.fromisoformat(i["due"]), ctx.as_of) <= 30]
        lines += ["", "## À traiter sous 30 jours", ""]
        if soon:
            for item in soon:
                days = _days_left(dt.date.fromisoformat(item["due"]), ctx.as_of)
                lines.append(f"- **{item['label']}** dans {days} j ({item['due']}) — {item['kind']}")
        else:
            lines.append("- Aucune échéance dans les 30 jours.")
        path = ctx.atelier.write(f"livrables/{name}", "\n".join(lines) + "\n")
        return {"written": f"livrables/{name}", "bytes": path.stat().st_size, "rows": len(items)}

    @reg.tool(
        "alerte_emettre",
        "Écrit une alerte markdown pour les échéances comprises entre aujourd'hui et within_days.",
        optional={"within_days": 90},
    )
    def alerte_emettre(within_days: int = 90) -> dict[str, Any]:
        horizon = int(within_days)
        if horizon <= 0:
            raise ErreurOutil("within_days doit être positif")
        data = _load_ledger(ctx)
        due = []
        for item in data["items"]:
            days = _days_left(dt.date.fromisoformat(item["due"]), ctx.as_of)
            if 0 <= days <= horizon:
                due.append((days, item))
        due.sort(key=lambda pair: pair[0])
        if not due:
            return {"alertes": 0, "horizon_days": horizon, "message": "aucune échéance dans la fenêtre"}
        lines = [
            f"# Alerte — {len(due)} échéance(s) sous {horizon} jours",
            "",
            f"Émise le {ctx.as_of.isoformat()} par l'agent Classeur (traitement local).",
            "",
        ]
        for days, item in due:
            lines.append(f"- **{item['label']}** — {item['due']} ({days} j) · {item['kind']} · source `{item['source']}`")
            if item.get("amount"):
                lines.append(f"  - montant : {item['amount']}")
        name = f"alertes-{horizon}j.md"
        path = ctx.atelier.write(f"alertes/{name}", "\n".join(lines) + "\n")
        return {"alertes": len(due), "written": f"alertes/{name}", "bytes": path.stat().st_size}

    return reg
