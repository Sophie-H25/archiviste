"""Interface en ligne de commande d'Classeur."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import tempfile
from pathlib import Path

from .moteur import boucle as noyau
from .moteur.boucle import SCENARIO_DIR, Contexte, Registre, Atelier, MemoireProcedures
from .moteur.decisions import list_models
from .moteur.outils import construire_registre

TEMPLATE_SCENARIO = {
    "title": "Nouveau scénario",
    "objective": "Décrire l'objectif confié à l'agent en une phrase.",
    "as_of": "2026-12-01",
    "budget": 14,
    "passes": [{"label": "passe unique", "cassette": "cassette.json"}],
}
TEMPLATE_CASSETTE = {
    "steps": [
        {"thought": "Commencer par lister le classeur.", "tool": "classeur_lister", "args": {"dir": "."}},
        {"thought": "Conclusion.", "final": "À compléter."},
    ]
}


def _fmt_size(size: int) -> str:
    return f"{size} o" if size < 1024 else f"{size / 1024:.1f} ko"


def _registre_jetable() -> Registre:
    """Registre jetable, utilisé pour valider les cassettes hors exécution."""
    tmp = Path(tempfile.mkdtemp(prefix="classeur-validate-"))
    ctx = Contexte(atelier=Atelier(tmp / "atelier"), as_of=dt.date.today(), skills=MemoireProcedures(tmp / "skills"), scenario="_validate")
    registre = Registre()
    construire_registre(registre, ctx)
    ctx.registre = registre
    return registre


def parametres_signature(signature: str) -> tuple[list[str], list[str]]:
    inner = signature[signature.index("(") + 1 : signature.rindex(")")]
    required: list[str] = []
    optional: list[str] = []
    for part in (p.strip() for p in inner.split(",")):
        if not part:
            continue
        name = part.split("=")[0].strip().replace("[]", "")
        if "=" in part or part.endswith("=None"):
            optional.append(name)
        else:
            required.append(name)
    return required, optional


def valider_scenarios() -> list[str]:
    registre = _registre_jetable()
    problems: list[str] = []

    for scen in noyau.lister_scenarios():
        slug = scen["slug"]
        base = SCENARIO_DIR / slug
        for entry in noyau.charger_scenario(slug)["passes"]:
            cassette_rel = entry.get("cassette", "cassette.json")
            cassette_path = base / cassette_rel
            label = f"{slug}/{cassette_rel}"
            if not cassette_path.is_file():
                problems.append(f"{label} : cassette absente")
                continue
            try:
                payload = json.loads(cassette_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                problems.append(f"{label} : JSON invalide ({exc})")
                continue
            steps = payload.get("steps", payload) if isinstance(payload, dict) else payload
            if not isinstance(steps, list) or not steps:
                problems.append(f"{label} : cassette vide")
                continue
            if "final" not in (steps[-1] or {}):
                problems.append(f"{label} : la dernière étape doit être un 'final'")
            for index, step in enumerate(steps, start=1):
                if not isinstance(step, dict):
                    problems.append(f"{label} étape {index} : objet JSON attendu")
                    continue
                if "final" in step:
                    continue
                tool_name = step.get("tool")
                args = step.get("args", {})
                tool = registre.get(tool_name) if isinstance(tool_name, str) else None
                if tool is None:
                    problems.append(f"{label} étape {index} : outil inconnu {tool_name!r}")
                    continue
                required, optional = parametres_signature(tool.signature())
                if not isinstance(args, dict):
                    problems.append(f"{label} étape {index} : args doit être un objet")
                    continue
                missing = [p for p in required if p not in args]
                extra = [k for k in args if k not in required and k not in optional]
                if missing:
                    problems.append(f"{label} étape {index} : argument(s) manquant(s) {missing} pour {tool.signature()}")
                if extra:
                    problems.append(f"{label} étape {index} : argument(s) inconnu(s) {extra} pour {tool.signature()}")
    return problems


def cmd_lister(_: argparse.Namespace) -> int:
    for scen in noyau.lister_scenarios():
        flag = "apprentissage" if scen["learning"] else "simple"
        print(f"{scen['slug']:<14} {flag:<14} budget {scen['budget']:>2} · {len(scen['fixtures'])} doc(s) · {scen['title']}")
    return 0


def cmd_valider(_: argparse.Namespace) -> int:
    problems = valider_scenarios()
    if problems:
        print(f"{len(problems)} problème(s) de cassette :")
        for problem in problems:
            print(f"  ✗ {problem}")
        return 1
    count = sum(len(noyau.charger_scenario(s["slug"])["passes"]) for s in noyau.lister_scenarios())
    print(f"✓ {count} cassette(s) valides : outils connus, arguments conformes, conclusion présente.")
    return 0


def cmd_creer(args: argparse.Namespace) -> int:
    slug = args.slug.strip().lower()
    target = SCENARIO_DIR / slug
    if target.exists():
        print(f"✗ {target} existe déjà", file=sys.stderr)
        return 1
    (target / "fixtures").mkdir(parents=True)
    (target / "fixtures" / ".gitkeep").write_text("", encoding="utf-8")
    (target / "scenario.json").write_text(json.dumps({**TEMPLATE_SCENARIO, "slug": slug}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (target / "cassette.json").write_text(json.dumps(TEMPLATE_CASSETTE, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"✓ scénario créé : {target}")
    print("  1. déposer les documents de test dans documents/")
    print("  2. décrire l'objectif dans scenario.json")
    print("  3. écrire la cassette puis vérifier : python -m classeur validate")
    return 0


def cmd_executer(args: argparse.Namespace) -> int:
    modele = None
    if args.modele:
        modele = {"base_url": args.url, "model": args.model, "api_key": args.api_key, "timeout": args.timeout}
    try:
        result = noyau.executer_scenario(
            args.scenario,
            mode="modele" if args.modele else "cassette",
            modele=modele,
            as_of=args.as_of,
            max_steps=args.steps,
        )
    except FileNotFoundError as exc:
        print(f"✗ {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["status"] == "done" else 1

    print(f"Scénario   : {result['title']} ({result['scenario']})")
    print(f"Objectif   : {result['objective']}")
    print(f"Mode       : {'modele · ' + args.model if args.modele else 'cassette (déterministe, aucun réseau)'}")
    print(f"Référence  : {result['as_of']} · budget {result['budget']} étapes")
    print()
    for entry in result["passes"]:
        if len(result["passes"]) > 1:
            print(f"── {entry['label']} ──")
        for record in entry["records"]:
            mark = "✓" if record["ok"] else "✗"
            args_txt = json.dumps(record["args"], ensure_ascii=False)
            print(f"{record['step']:>2} {mark} {record['tool']}({args_txt[:96]})")
            observation = record["observation"]
            detail = observation.get("error") if not observation.get("ok") else _summarize(observation.get("result"))
            if detail:
                print(f"      → {detail[:150]}")
        print(f"   conclusion : {entry['final'][:220]}")
        print()
    print(f"Statut     : {result['status']} · {sum(p['steps'] for p in result['passes'])} étapes · {result['errors']} erreur(s)")
    if result["artifacts"]:
        print("Artefacts  :")
        for artifact in result["artifacts"]:
            print(f"  - {artifact['name']} ({_fmt_size(artifact['bytes'])})")
    if len(result["passes"]) > 1:
        left, right = result["passes"][0], result["passes"][1]
        gain = left["steps"] - right["steps"]
        print()
        print(
            f"Apprentissage : {left['label']} → {left['steps']} étapes · {left['errors']} erreur(s) | "
            f"{right['label']} → {right['steps']} étapes · {right['errors']} erreur(s)"
            + (f" ({gain} étape(s) en moins)" if gain > 0 else "")
        )
    if result["skills"]:
        print(f"Procédures apprises : {', '.join(s['slug'] for s in result['skills'])}")
    print(f"Journal    : {result['journal']}")
    return 0 if result["status"] == "done" else 1


def _summarize(result: object, width: int = 130) -> str:
    if result is None:
        return ""
    if isinstance(result, dict):
        for key in ("count", "written", "added", "alertes", "files", "hits", "rows", "total"):
            if key in result:
                return f"{key}={result[key]}"
        return json.dumps(result, ensure_ascii=False)[:width]
    return str(result)[:width]


def cmd_mesurer(args: argparse.Namespace) -> int:
    from mesure.harnais import executer_mesure  # import tardif : le bench reste optionnel

    return executer_mesure(args)


def cmd_servir(args: argparse.Namespace) -> int:
    from .interface.serveur import serve

    return serve(host=args.host, port=args.port, open_browser=args.open)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="classeur", description="Le classeur : un agent local qui relève vos échéances administratives.")
    sub = parser.add_subparsers(dest="commande", required=True)

    sub.add_parser("lister", help="lister les scénarios").set_defaults(func=cmd_lister)
    sub.add_parser("valider", help="valider les cassettes contre les signatures d'outils").set_defaults(func=cmd_valider)

    nouveau = sub.add_parser("creer", help="créer un scénario vide")
    nouveau.add_argument("slug")
    nouveau.set_defaults(func=cmd_creer)

    lancer = sub.add_parser("executer", help="exécuter un scénario")
    lancer.add_argument("scenario")
    lancer.add_argument("--modele", action="store_true", help="laisser un modèle local choisir les étapes au lieu de la cassette")
    lancer.add_argument("--url", default="http://127.0.0.1:11434", help="URL du serveur de modèle (Ollama par défaut)")
    lancer.add_argument("--nom-modele", dest="model", default="qwen2.5-coder:7b")
    lancer.add_argument("--cle", dest="api_key", default=None)
    lancer.add_argument("--delai", dest="timeout", type=int, default=180)
    lancer.add_argument("--reference", dest="as_of", default=None, help="date de référence AAAA-MM-JJ (défaut : aujourd'hui)")
    lancer.add_argument("--etapes", dest="steps", type=int, default=None, help="budget d'étapes")
    lancer.add_argument("--json", action="store_true")
    lancer.set_defaults(func=cmd_executer)

    servir = sub.add_parser("servir", help="servir l'interface locale")
    servir.add_argument("--hote", dest="host", default="127.0.0.1")
    servir.add_argument("--port", type=int, default=8080)
    servir.add_argument("--ouvrir", dest="open", action="store_true", help="ouvrir le navigateur")
    servir.set_defaults(func=cmd_servir)

    mesurer = sub.add_parser("mesurer", help="mesurer un serveur de modèle local (latence, exactitude)")
    mesurer.add_argument("--url", dest="base_url", default="http://127.0.0.1:11434")
    mesurer.add_argument("--nom-modele", dest="model", default="qwen2.5-coder:7b")
    mesurer.add_argument("--cle", dest="api_key", default=None)
    mesurer.add_argument("--taches", dest="tasks", type=int, default=10)
    mesurer.add_argument("--prix-million", dest="price_per_million", type=float, default=0.0)
    mesurer.add_argument("--sortie", dest="out", default="mesure/mesure.md")
    mesurer.set_defaults(func=cmd_mesurer)

    modeles = sub.add_parser("modeles", help="sonder un serveur : liste les modèles exposés")
    modeles.add_argument("--url", dest="base_url", default="http://127.0.0.1:11434")
    modeles.set_defaults(func=lambda a: _print_modeles(a.base_url))
    return parser


def _print_modeles(base_url: str) -> int:
    try:
        payload = list_models(base_url)
    except Exception as exc:  # noqa: BLE001
        print(f"✗ backend injoignable sur {base_url} : {exc}", file=sys.stderr)
        return 1
    print(f"Endpoint normalisé : {payload['base_url']}")
    for model in payload["models"]:
        print(f"  - {model}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
