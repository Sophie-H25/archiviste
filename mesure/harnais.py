"""Benchmark honnête : exactitude et latence d'un backend local sur des décisions d'agent.

Rien de spectaculaire n'est promis ici : dix tâches courtes tirées du domaine de
la démo, une notation par correspondance exacte (jamais un LLM juge), et un
rapport qui dit ce que les chiffres ne disent pas.

    python -m archiviste bench --base-url http://127.0.0.1:11434 --model qwen2.5:3b
    python mesure/serveur_simule.py --port 8099 &   # endpoint simulé, pour la CI
    python -m archiviste bench --base-url http://127.0.0.1:8099 --out mesure/report-sim.md
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import statistics
import tempfile
import time
from pathlib import Path
from typing import Any

from archiviste.moteur.boucle import Contexte, Registre, Atelier, MemoireProcedures
from archiviste.moteur.decisions import PlanificateurModele, list_models
from archiviste.moteur.outils import construire_registre

ROOT = Path(__file__).resolve().parent.parent

# Chaque tâche vérifie une décision précise : bon outil + bon argument.
TASKS: list[dict[str, Any]] = [
    {
        "id": 1,
        "excerpt": "AXELLA - Proces-verbal de controle technique. Vehicule AB-123-CD. Prochain controle technique a effectuer avant le 12/01/2027.",
        "objective": "Enregistre cette echeance dans le registre.",
        "expect_tool": "echeance_ajouter",
        "expect_args": {"due": "2027-01-12", "kind": "controle_technique"},
    },
    {
        "id": 2,
        "excerpt": "GARANTIE CHAUDIERE Thermorane T-24. Installation le 28 fevrier 2022. Garantie fabricant 5 ans. Fin de garantie : 28 fevrier 2027.",
        "objective": "Enregistre la fin de garantie.",
        "expect_tool": "echeance_ajouter",
        "expect_args": {"due": "2027-02-28", "kind": "garantie"},
    },
    {
        "id": 3,
        "excerpt": "Assurance habitation HAB-2024-88421. Degats des eaux : franchise 250 EUR par sinistre. Plafond mobilier 45 000 EUR.",
        "objective": "Quelle est la franchise degats des eaux ?",
        "expect_tool": "__final__",
        "expect_args": {"final": "250"},
    },
    {
        "id": 4,
        "excerpt": "AVIS DE TAXE FONCIERE. Exercice 2027. Reglement avant le 3e lundi d'octobre 2027. Montant 1 342,00 EUR.",
        "objective": "Enregistre cette echeance en date ISO.",
        "expect_tool": "echeance_ajouter",
        "expect_args": {"due": "2027-10-18"},
    },
    {
        "id": 5,
        "excerpt": "Le archiviste contient : assurance-habitation.pdf, assurance-auto.eml, controle-technique.txt, garantie-chaudiere.docx, abonnement-salle.csv.",
        "objective": "Produis le rapport des echeances.",
        "expect_tool": "rapport_ecrire",
        "expect_args": {},
    },
    {
        "id": 6,
        "excerpt": "Le registre contient 5 echeances, la plus proche le 2027-01-12.",
        "objective": "Emets une alerte pour les echeances des 90 prochains jours.",
        "expect_tool": "alerte_emettre",
        "expect_args": {"within_days": "90"},
    },
    {
        "id": 7,
        "excerpt": "Archiviste : 5 documents, aucun releve bancaire.",
        "objective": "Donne-moi le solde de mon compte bancaire.",
        "expect_tool": "__final__",
        "expect_args": {"final": "pas"},
    },
    {
        "id": 8,
        "excerpt": "Assurance auto : echeance le 15/04/2027, cotisation 612,00 EUR, vehicule AB-123-CD.",
        "objective": "Trouve la date d'echeance du contrat auto.",
        "expect_tool": "echeance_ajouter",
        "expect_args": {"due": "2027-04-15"},
    },
    {
        "id": 9,
        "excerpt": "Dossier taxe : un seul fichier, taxe-fonciere.txt.",
        "objective": "Liste les fichiers du archiviste.",
        "expect_tool": "classeur_lister",
        "expect_args": {},
    },
    {
        "id": 10,
        "excerpt": "assurance-habitation.pdf contient la section GARANTIES.",
        "objective": "Lis le contrat d'assurance habitation.",
        "expect_tool": "document_lire",
        "expect_args": {"path": "assurance-habitation.pdf"},
    },
]


def _tool_table() -> list[dict[str, Any]]:
    tmp = Path(tempfile.mkdtemp(prefix="archiviste-bench-"))
    ctx = Contexte(
        atelier=Atelier(tmp / "atelier"),
        as_of=dt.date(2026, 11, 20),
        skills=MemoireProcedures(tmp / "skills"),
        scenario="_bench",
    )
    registre = Registre()
    construire_registre(registre, ctx)
    return registre.specs()


def _grade(step: dict[str, Any], task: dict[str, Any]) -> bool:
    if step.get("tool") == "__unparsable__":
        return False
    expected_tool = task["expect_tool"]
    if expected_tool == "__final__":
        if "final" not in step:
            return False
        text = str(step["final"]).lower()
        return all(str(value).lower() in text for value in task["expect_args"].values())
    if step.get("tool") != expected_tool:
        return False
    args = step.get("args") or {}
    if not isinstance(args, dict):
        return False
    return all(str(value).lower() in str(args.get(key, "")).lower() for key, value in task["expect_args"].items())


def executer_mesure(args: argparse.Namespace) -> int:
    simulated = False
    try:
        probe = list_models(args.base_url)
        simulated = any("simulated" in model for model in probe.get("models", []))
    except Exception:  # noqa: BLE001 - un endpoint qui ne liste pas ses modèles reste mesurable
        simulated = False

    planificateur = PlanificateurModele(base_url=args.base_url, model=args.model, api_key=args.api_key, timeout=120)
    planificateur.attach_tools(_tool_table())

    rows: list[dict[str, Any]] = []
    latencies: list[float] = []
    tokens_in = tokens_out = 0

    for task in TASKS[: int(args.tasks)]:
        objective = f"[tache:{task['id']}] {task['objective']}\n\nExtrait disponible :\n{task['excerpt']}"
        started = time.perf_counter()
        step = planificateur.next_step(objective, [])
        elapsed = time.perf_counter() - started
        latencies.append(elapsed)
        # Les tokens ne sont connus qu'en mode réel : le simulateur les annonce factices.
        usage = getattr(planificateur, "last_usage", {}) or {}
        tokens_in += int(usage.get("prompt_tokens", 0))
        tokens_out += int(usage.get("completion_tokens", 0))
        rows.append(
            {
                "id": task["id"],
                "ok": _grade(step, task),
                "ms": round(elapsed * 1000),
                "tool": step.get("tool") or ("final" if "final" in step else "?"),
            }
        )

    ok = sum(1 for row in rows if row["ok"])
    rate = ok / len(rows) * 100 if rows else 0.0
    p50 = statistics.median(latencies) * 1000 if latencies else 0.0
    p95 = (sorted(latencies)[max(0, int(len(latencies) * 0.95) - 1)] * 1000) if latencies else 0.0
    price = float(args.price_per_million or 0)
    cost_1000 = (tokens_in + tokens_out) * price / 1_000_000 * 1000 if price else 0.0

    report = [
        "# Rapport de mesure — Archiviste",
        "",
    ]
    if simulated:
        report += [
            "> **RAPPORT SIMULÉ — ne mesure rien.** L'endpoint interrogé renvoie des décisions préenregistrées. "
            "Ce fichier prouve seulement que le harness s'exécute de bout en bout.",
            "",
        ]
    report += [
        f"Backend : `{args.base_url}` · modèle `{args.model}` · {len(rows)} tâches.",
        "",
        f"- Exactitude (correspondance exacte) : **{ok}/{len(rows)} ({rate:.0f} %)**",
        f"- Latence p50 / p95 : **{p50:.0f} ms / {p95:.0f} ms**",
        f"- Coût pour 1 000 runs : **{cost_1000:.2f} €** "
        + ("(prix saisi)" if price else "(endpoint local : 0 € de tokens, hors matériel et électricité)"),
        "",
        "| # | Décision attendue | Obtenu | OK | ms |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row, task in zip(rows, TASKS):
        report.append(f"| {row['id']} | {task['expect_tool']} | {row['tool']} | {'oui' if row['ok'] else 'non'} | {row['ms']} |")
    report += [
        "",
        "## Ce que ces chiffres ne disent pas",
        "",
        "- Jeu de tâches volontairement court (10 décisions) et fermé : il mesure le respect du contrat JSON "
        "et des signatures d'outils, pas la qualité rédactionnelle d'un briefing.",
        "- La latence inclut la variance réseau et le chargement du modèle à froid ; un premier appel "
        "sur un modèle non chargé peut être dix fois plus lent.",
        "- Le coût local exclut l'amortissement du matériel, l'électricité et le temps d'installation : "
        "« 0 € de tokens » n'est pas « gratuit ».",
        "- Si ce rapport a été produit contre `mesure/serveur_simule.py`, l'endpoint répond des réponses "
        "préenregistrées : le score vaut **zéro** et ne sert qu'à vérifier que la CI exécute le harness.",
        "",
    ]
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(report) + "\n", encoding="utf-8")
    print(f"exactitude {ok}/{len(rows)} · p50 {p50:.0f} ms · p95 {p95:.0f} ms · rapport : {out}")
    return 0 if ok == len(rows) else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Mesure un backend local sur des décisions d'agent.")
    parser.add_argument("--base-url", default="http://127.0.0.1:11434")
    parser.add_argument("--model", default="qwen2.5:3b")
    parser.add_argument("--api-key", default=None)
    parser.add_argument("--tasks", type=int, default=len(TASKS))
    parser.add_argument("--price-per-million", type=float, default=0.0, help="prix tokens / million (0 = local)")
    parser.add_argument("--out", default="mesure/report.md")
    return executer_mesure(parser.parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
