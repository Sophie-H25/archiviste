"""Serveur HTTP local : UI de démonstration + API JSON. Bibliothèque standard.

Endpoints :
  GET  /                     interface
  GET  /healthz              sonde de vie (utilisée par la CI et Docker)
  GET  /api/scenarios        catalogue
  GET  /api/skills           procédures apprises (toutes survivantes aux runs)
  GET  /api/runs             runs récents
  GET  /api/runs/<id>        résultat complet d'un run
  GET  /api/artifact?run=&name=  artefact (markdown, json, csv...)
  POST /api/run              {scenario, mode, base_url, model, api_key}
  POST /api/probe            {base_url} -> modèles exposés
"""

from __future__ import annotations

import json
import mimetypes
import threading
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from ..moteur import boucle as noyau
from ..moteur.boucle import RUNS_DIR, MemoireProcedures, DATA_DIR
from ..moteur.decisions import list_models
from .page import INDEX_HTML

CHARSET_TYPES = {
    ".md": "text/markdown",
    ".txt": "text/plain",
    ".csv": "text/csv",
    ".json": "application/json",
    ".html": "text/html",
    ".svg": "image/svg+xml",
}
_RUN_LOCK = threading.Lock()


def _json_bytes(payload: Any) -> bytes:
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


def _guess_type(name: str) -> str:
    suffix = Path(name).suffix.lower()
    base = CHARSET_TYPES.get(suffix) or (mimetypes.guess_type(name)[0] or "application/octet-stream")
    # Un type texte sans charset fait deviner latin-1 au navigateur : « é » devient « Ã© ».
    if base.startswith("text/") or base in {"application/json", "image/svg+xml"}:
        return f"{base}; charset=utf-8"
    return base


class Handler(BaseHTTPRequestHandler):
    server_version = "Classeur/1.0"

    def log_message(self, fmt: str, *args: Any) -> None:  # silence par défaut
        if self.server.verbose:  # type: ignore[attr-defined]
            super().log_message(fmt, *args)

    # -- helpers ---------------------------------------------------------- #
    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, payload: Any, status: int = 200) -> None:
        self._send(status, _json_bytes(payload), "application/json; charset=utf-8")

    def _body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length") or 0)
        if not length:
            return {}
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {}

    # -- routes ----------------------------------------------------------- #
    def do_GET(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path == "/":
            self._send(200, INDEX_HTML.encode("utf-8"), "text/html; charset=utf-8")
        elif path == "/healthz":
            self._send_json({"ok": True, "version": noyau.__dict__.get("__version__", "1.0.0")})
        elif path == "/api/scenarios":
            self._send_json({"dossiers": noyau.lister_scenarios(), "skills": _all_skills()})
        elif path == "/api/skills":
            self._send_json({"skills": _all_skills()})
        elif path == "/api/runs":
            self._send_json({"runs": _recent_runs()})
        elif path.startswith("/api/runs/"):
            run_id = path.rsplit("/", 1)[-1]
            result = Path(RUNS_DIR) / run_id / "result.json"
            if not result.is_file():
                self._send_json({"error": "run inconnu"}, 404)
            else:
                self._send_json(json.loads(result.read_text(encoding="utf-8")))
        elif path == "/api/artifact":
            run_id = (query.get("run") or [""])[0]
            name = (query.get("name") or [""])[0]
            try:
                target = noyau.lire_artefact(run_id, name)
            except FileNotFoundError:
                self._send(404, b"artifact not found", "text/plain; charset=utf-8")
            except noyau.ErreurAtelier as exc:
                self._send(403, str(exc).encode("utf-8"), "text/plain; charset=utf-8")
            else:
                self._send(200, target.read_bytes(), _guess_type(name))
        else:
            self._send(404, b"not found", "text/plain; charset=utf-8")

    def do_POST(self) -> None:  # noqa: N802
        path = urllib.parse.urlparse(self.path).path
        payload = self._body()

        if path == "/api/run":
            slug = str(payload.get("scenario") or "")
            mode = "modele" if payload.get("mode") == "modele" else "cassette"
            modele = {
                "base_url": payload.get("base_url") or "http://127.0.0.1:11434",
                "model": payload.get("model") or "qwen2.5-coder:7b",
                "api_key": payload.get("api_key") or None,
                "timeout": int(payload.get("timeout") or 180),
            }
            if not slug:
                self._send_json({"error": "scenario requis"}, 400)
                return
            try:
                with _RUN_LOCK:
                    result = noyau.executer_scenario(slug, mode=mode, modele=modele if mode == "modele" else None, as_of=payload.get("as_of") or None)
            except FileNotFoundError as exc:
                self._send_json({"error": str(exc)}, 404)
                return
            except Exception as exc:  # noqa: BLE001 - l'UI doit afficher l'erreur, pas mourir
                self._send_json({"error": f"{type(exc).__name__}: {exc}"}, 500)
                return
            self._send_json(result)
        elif path == "/api/probe":
            try:
                self._send_json(list_models(str(payload.get("base_url") or "http://127.0.0.1:11434")))
            except Exception as exc:  # noqa: BLE001
                self._send_json({"error": f"{type(exc).__name__}: {exc}", "hint": "vérifier l'hôte, le port et le suffixe /v1"}, 502)
        else:
            self._send_json({"error": "unknown endpoint"}, 404)


def _all_skills() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    root = Path(DATA_DIR) / "skills"
    if not root.is_dir():
        return rows
    for scenario_dir in sorted(root.iterdir()):
        if scenario_dir.is_dir():
            for entry in MemoireProcedures(scenario_dir).listing():
                rows.append({"scenario": scenario_dir.name, **entry})
    return rows


def _recent_runs(limit: int = 20) -> list[dict[str, Any]]:
    root = Path(RUNS_DIR)
    if not root.is_dir():
        return []
    rows = []
    for path in sorted(root.iterdir(), reverse=True):
        result = path / "result.json"
        if not result.is_file():
            continue
        try:
            data = json.loads(result.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        rows.append(
            {
                "run_id": data.get("run_id"),
                "scenario": data.get("scenario"),
                "mode": data.get("mode"),
                "status": data.get("status"),
                "steps": sum(p.get("steps", 0) for p in data.get("passes", [])),
                "errors": data.get("errors", 0),
            }
        )
        if len(rows) >= limit:
            break
    return rows


def make_server(host: str = "127.0.0.1", port: int = 8080) -> ThreadingHTTPServer:
    httpd = ThreadingHTTPServer((host, port), Handler)
    httpd.verbose = False  # type: ignore[attr-defined]
    return httpd


def serve(host: str = "127.0.0.1", port: int = 8080, open_browser: bool = False) -> int:
    httpd = make_server(host, port)
    url = f"http://{host if host != '0.0.0.0' else '127.0.0.1'}:{port}/"
    print(f"Classeur — interface sur {url}")
    print("Ctrl+C pour arrêter.")
    if open_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\narrêt.")
    finally:
        httpd.server_close()
    return 0
