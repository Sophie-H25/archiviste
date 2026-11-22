"""Deux planificateurs derrière une seule interface.

* ``PlanificateurEnregistre`` : conducteur enregistrée, déterministe, aucun réseau, aucune clé.
* ``PlanificateurModele``   : backend OpenAI-compatible (Ollama, LM Studio, llama.cpp, vLLM).

Les outils s'exécutent pour de vrai dans les deux modes ; seul le choix de
l'étape suivante change. C'est ce qui rend la démo vérifiable : un run conducteur
produit de vrais fichiers, avec des timings honnêtement nuls.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from typing import Any

CONTRAT_JSON = """Réponds UNIQUEMENT par un objet JSON, sans texte autour, sans bloc markdown.
Deux formes possibles :
{"thought": "raisonnement court", "tool": "nom_outil", "args": {"cle": "valeur"}}
{"thought": "raisonnement court", "final": "réponse finale pour l'utilisateur"}
Règles :
- un seul appel d'outil par étape ;
- les clés d'args doivent correspondre EXACTEMENT à la signature de l'outil (ni manquante, ni inventée) ;
- ne jamais inventer une date, une source ou un montant : lire le document d'abord ;
- après une erreur d'outil, appeler procedure_noter pour capitaliser la leçon ;
- les noms d'outils sont exactement ceux de la liste fournie : ne pas en inventer, ne pas traduire ;
- ne pas relire un document déjà lu : chaque fichier se lit une seule fois ;
- un relevé d'échéances se termine par rapport_ecrire, puis alerte_emettre, puis "final" ;
- quand le livrable est écrit et vérifié, terminer par "final"."""


def _post_json(url: str, payload: dict[str, Any], api_key: str | None, timeout: int) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, method="POST")
    request.add_header("Content-Type", "application/json")
    if api_key:
        request.add_header("Authorization", f"Bearer {api_key}")
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - endpoint local choisi par l'utilisateur
        return json.loads(response.read().decode("utf-8"))


def normalize_base(base_url: str) -> str:
    """Tolère les deux erreurs les plus fréquentes : /v1 manquant, slash final."""
    base = (base_url or "").strip().rstrip("/")
    if not base:
        raise ValueError("base_url vide")
    if not re.match(r"^https?://", base):
        base = "http://" + base
    if not base.endswith("/v1"):
        base += "/v1"
    return base


def chat_endpoint(base_url: str) -> str:
    base = normalize_base(base_url)
    return base + "/chat/completions" if not base.endswith("/chat/completions") else base


def list_models(base_url: str, timeout: int = 15) -> dict[str, Any]:
    base = normalize_base(base_url)
    with urllib.request.urlopen(base + "/models", timeout=timeout) as response:  # noqa: S310
        payload = json.loads(response.read().decode("utf-8"))
    models = [m.get("id") for m in payload.get("data", []) if m.get("id")]
    return {"base_url": base, "models": models}


class PlanificateurEnregistre:
    def __init__(self, steps: list[dict[str, Any]]) -> None:
        self.steps = list(steps)
        self.index = 0

    def next_step(self, objective: str, history: list[dict[str, Any]]) -> dict[str, Any]:
        if self.index >= len(self.steps):
            return {"thought": "conducteur épuisée", "final": "(conducteur épuisée avant conclusion)"}
        step = self.steps[self.index]
        self.index += 1
        return step


class PlanificateurModele:
    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: str | None = None,
        timeout: int = 180,
        temperature: float = 0.1,
        max_history: int = 8,
    ) -> None:
        self.url = chat_endpoint(base_url)
        self.model = model
        self.api_key = api_key
        self.timeout = timeout
        self.temperature = temperature
        self.max_history = max_history
        self.outils: list[dict[str, Any]] = []
        self.last_usage: dict[str, Any] = {}

    def attach_tools(self, tools: list[dict[str, Any]]) -> None:
        self.outils = tools

    def system_prompt(self) -> str:
        table = "\n".join(f"- {t['signature']} — {t['doc']}" for t in self.outils)
        return (
            "Tu es Archiviste, un agent local qui gère le archiviste administratif d'un foyer.\n"
            "Ton domaine : documents personnels (assurances, contrôle technique, garanties, abonnements, taxes).\n"
            "Tu travailles uniquement sur les fichiers du atelier du run, tu n'as aucun accès réseau.\n\n"
            f"Outils disponibles :\n{table}\n\n{CONTRAT_JSON}"
        )

    def documents_lus(self, history: list[dict[str, Any]], budget_chars: int = 4200) -> str:
        """Texte des documents déjà lus, gardé hors de la fenêtre courte de l'historique.

        Sans ça, un petit modèle relit le même PDF à l'étape suivante : le texte lu
        sort de l'historique après huit étapes et il n'a plus les dates sous les yeux.
        """
        vus: dict[str, str] = {}
        for record in history:
            if record.get("tool") != "document_lire":
                continue
            observation = record.get("observation") or {}
            resultat = observation.get("result") or {}
            chemin = str(resultat.get("path") or record.get("args", {}).get("path") or "?")
            texte = str(resultat.get("text") or "")
            if texte and chemin not in vus:
                vus[chemin] = texte[:900]
        if not vus:
            return ""
        blocs, reste = [], budget_chars
        for chemin, texte in vus.items():
            if reste <= 0:
                break
            extrait = texte[: reste]
            reste -= len(extrait)
            blocs.append(f"--- {chemin} ---\n{extrait}")
        return "\n".join(blocs)

    def user_prompt(self, objective: str, history: list[dict[str, Any]]) -> str:
        lines = [f"Objectif : {objective}", ""]
        lus = self.documents_lus(history)
        if lus:
            lines.append("Documents déjà lus (texte extrait, ne pas les relire) :")
            lines.append(lus)
            lines.append("")
        if history:
            lines.append("Historique (dernières étapes) :")
            for record in history[-self.max_history :]:
                observation = json.dumps(record.get("observation", {}), ensure_ascii=False)
                lines.append(f"- {record['tool']}({json.dumps(record.get('args', {}), ensure_ascii=False)}) -> {observation[:700]}")
        lines.append("")
        lines.append("Rappel : chaque date d'échéance trouvée doit être enregistrée par echeance_ajouter "
                     "(kind, label, due en AAAA-MM-JJ, source = nom du fichier). Ne relis pas un fichier déjà lu.")
        lines.append("Quelle est la prochaine étape ? JSON uniquement.")
        return "\n".join(lines)

    def next_step(self, objective: str, history: list[dict[str, Any]]) -> dict[str, Any]:
        payload = {
            "model": self.model,
            "temperature": self.temperature,
            "messages": [
                {"role": "system", "content": self.system_prompt()},
                {"role": "user", "content": self.user_prompt(objective, history)},
            ],
        }
        try:
            response = _post_json(self.url, payload, self.api_key, self.timeout)
        except urllib.error.URLError as exc:
            return {"thought": "backend injoignable", "final": f"Backend local injoignable ({exc}). Vérifier l'URL /v1 et que le serveur écoute."}
        except (TimeoutError, json.JSONDecodeError) as exc:
            return {"thought": "backend en échec", "final": f"Réponse du backend illisible ou trop lente : {exc}"}
        try:
            content = response["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            return {"thought": "réponse inattendue", "final": f"Réponse non conforme du backend : {str(response)[:300]}"}
        self.last_usage = response.get("usage") or {}
        return parse_step(content)


def parse_step(content: str) -> dict[str, Any]:
    text = (content or "").strip()
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.MULTILINE).strip()
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        return {"thought": "sortie non structurée", "tool": "__unparsable__", "args": {}}
    try:
        step = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return {"thought": "sortie non structurée", "tool": "__unparsable__", "args": {}}
    if not isinstance(step, dict):
        return {"thought": "sortie non structurée", "tool": "__unparsable__", "args": {}}
    step.setdefault("thought", "")
    if "final" not in step and "tool" not in step:
        return {"thought": step.get("thought", ""), "tool": "__unparsable__", "args": {}}
    if "args" in step and not isinstance(step["args"], dict):
        step["args"] = {}
    return step
