"""Endpoint OpenAI-compatible simulé — pour la CI uniquement.

Il répond des décisions **préenregistrées** selon le marqueur ``[tache:N]``
présent dans le prompt. Aucune inférence, aucun GPU, aucune clé.

À quoi ça sert : prouver que le harness de mesure et le mode modele fonctionnent
bout en bout dans la CI. Un rapport produit contre cet endpoint ne mesure rien
et le dit explicitement.

    python mesure/serveur_simule.py --port 8099
"""

from __future__ import annotations

import argparse
import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ANSWERS: dict[str, dict] = {
    "1": {"thought": "Contrôle technique daté du 12/01/2027.", "tool": "echeance_ajouter", "args": {"kind": "controle_technique", "label": "Contrôle technique AB-123-CD", "due": "2027-01-12", "source": "controle-technique.txt"}},
    "2": {"thought": "Fin de garantie au 28/02/2027.", "tool": "echeance_ajouter", "args": {"kind": "garantie", "label": "Garantie chaudière", "due": "2027-02-28", "source": "garantie-chaudiere.docx"}},
    "3": {"thought": "La franchise est dans la section GARANTIES.", "final": "La franchise dégâts des eaux est de 250 EUR par sinistre (plafond mobilier 45 000 EUR)."},
    "4": {"thought": "3e lundi d'octobre 2027 = 2027-10-18.", "tool": "echeance_ajouter", "args": {"kind": "taxe", "label": "Taxe foncière 2027", "due": "2027-10-18", "source": "taxe-fonciere.txt"}},
    "5": {"thought": "Le registre est rempli.", "tool": "rapport_ecrire", "args": {"name": "echeances.md"}},
    "6": {"thought": "Fenêtre de 90 jours.", "tool": "alerte_emettre", "args": {"within_days": 90}},
    "7": {"thought": "Aucun relevé bancaire dans le archiviste : je refuse.", "final": "Je ne peux pas : aucun solde bancaire n'est présent dans le archiviste et je ne l'inventerai pas."},
    "8": {"thought": "Échéance au 15/04/2027.", "tool": "echeance_ajouter", "args": {"kind": "assurance", "label": "Assurance auto", "due": "2027-04-15", "source": "assurance-auto.eml"}},
    "9": {"thought": "Inventaire du archiviste.", "tool": "classeur_lister", "args": {"dir": "."}},
    "10": {"thought": "Lecture du contrat.", "tool": "document_lire", "args": {"path": "assurance-habitation.pdf"}},
}


class Handler(BaseHTTPRequestHandler):
    delay = 0.0
    server_version = "SimEndpoint/1.0"

    def log_message(self, fmt: str, *args: object) -> None:  # silence
        return

    def _send(self, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        self._send({"object": "list", "data": [{"id": "simulated-local-model", "object": "model"}]})

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length") or 0)
        payload = json.loads(self.rfile.read(length) or b"{}")
        messages = payload.get("messages", [])
        joined = " ".join(str(m.get("content", "")) for m in messages)
        marker = "0"
        for part in joined.split("[tache:"):
            candidate = part.split("]")[0].strip()
            if candidate.isdigit():
                marker = candidate
                break
        if self.delay:
            time.sleep(self.delay)
        answer = ANSWERS.get(marker, {"thought": "hors jeu de test", "final": "réponse simulée"})
        self._send(
            {
                "id": "chatcmpl-sim",
                "object": "chat.completion",
                "model": payload.get("model", "simulated-local-model"),
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": json.dumps(answer, ensure_ascii=False)},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 900, "completion_tokens": 60, "total_tokens": 960},
            }
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Endpoint OpenAI-compatible simulé (CI).")
    parser.add_argument("--port", type=int, default=8099)
    parser.add_argument("--delay", type=float, default=0.0)
    args = parser.parse_args()
    Handler.delay = args.delay
    httpd = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"endpoint simulé sur http://127.0.0.1:{args.port}/v1 (aucune mesure réelle)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
