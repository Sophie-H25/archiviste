"""Suite de tests — unittest seul, aucun service externe requis.

Couvre : validation des cassettes, exécution de tous les scénarios, existence et
contenu des artefacts, refus de sortie du atelier du run, budget d'étapes, outil
inconnu, arguments invalides, extraction PDF/DOCX, API HTTP et charset.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

# Isolements : les runs et les procédures apprises vont dans des répertoires jetables.
_TMP = Path(tempfile.mkdtemp(prefix="classeur-tests-"))
os.environ.setdefault("CLASSEUR_RUNS", str(_TMP / "runs"))
os.environ.setdefault("CLASSEUR_DONNEES", str(_TMP / "data"))

from classeur import commande
from classeur.interface import serveur
from classeur.moteur import boucle as noyau  # noqa: E402
from classeur.moteur.lecture import extraire_texte  # noqa: E402
from classeur.moteur.boucle import Contexte, Registre, Atelier, MemoireProcedures  # noqa: E402
from classeur.moteur.outils import construire_registre  # noqa: E402

RUNS = Path(os.environ["CLASSEUR_RUNS"])


def make_registry(tmp: Path | None = None) -> tuple[Registre, Contexte]:
    root = Path(tmp or tempfile.mkdtemp(prefix="classeur-ctx-", dir=_TMP))
    ctx = Contexte(atelier=Atelier(root / "atelier"), as_of=__import__("datetime").date(2026, 11, 20), skills=MemoireProcedures(root / "skills"), scenario="_test")
    registre = Registre()
    construire_registre(registre, ctx)
    ctx.registre = registre
    return registre, ctx


class TestCassettes(unittest.TestCase):
    def test_validate_is_green(self) -> None:
        problems = commande.valider_scenarios()
        self.assertEqual(problems, [], f"cassettes invalides : {problems}")

    def test_scenario_creation_scaffold(self) -> None:
        existing = {s["slug"] for s in noyau.lister_scenarios()}
        self.assertIn("echeances", existing)
        self.assertGreaterEqual(len(existing), 4)


class TestScenarios(unittest.TestCase):
    def test_every_scenario_completes_without_error(self) -> None:
        for scen in noyau.lister_scenarios():
            with self.subTest(scenario=scen["slug"]):
                result = noyau.executer_scenario(scen["slug"], runs_dir=RUNS)
                self.assertEqual(result["status"], "done", f"{scen['slug']} n'a pas conclu")
                if scen["learning"]:
                    first, second = result["passes"]
                    self.assertEqual(first["errors"], 1, "la passe 1 doit rencontrer l'erreur formatée")
                    self.assertEqual(second["errors"], 0, "la passe 2 doit réutiliser la procédure")
                    self.assertLessEqual(second["steps"], first["steps"])
                else:
                    self.assertEqual(result["errors"], 0)

    def test_echeances_artifacts(self) -> None:
        result = noyau.executer_scenario("echeances", runs_dir=RUNS)
        names = {a["name"] for a in result["artifacts"]}
        self.assertIn("livrables/echeances.md", names)
        self.assertIn("alertes/alertes-90j.md", names)
        report = noyau.lire_artefact(result["run_id"], "livrables/echeances.md", RUNS).read_text(encoding="utf-8")
        self.assertIn("2027-01-12", report)
        self.assertIn("controle_technique", report)
        self.assertIn("53 j", report)
        registre = json.loads(noyau.lire_artefact(result["run_id"], "registre.json", RUNS).read_text(encoding="utf-8"))
        self.assertEqual(len(registre["items"]), 5)
        self.assertEqual(registre["items"][0]["days_left"], 53)

    def test_learning_writes_procedure_to_disk(self) -> None:
        noyau.executer_scenario("apprentissage", runs_dir=RUNS)
        skills = (noyau.DATA_DIR / "skills" / "apprentissage").glob("*.md")
        self.assertTrue(list(skills), "aucune procédure écrite sur disque")

    def test_budget_is_enforced(self) -> None:
        result = noyau.executer_scenario("echeances", max_steps=3, runs_dir=RUNS)
        self.assertEqual(result["status"], "budget")
        self.assertEqual(len(result["steps"]), 3)

    def test_garde_fous_refuses(self) -> None:
        result = noyau.executer_scenario("garde-fous", runs_dir=RUNS)
        self.assertIn("ne peux pas", result["final"])
        self.assertEqual(result["artifacts"], [])


class TestAtelier(unittest.TestCase):
    def setUp(self) -> None:
        self.registre, self.ctx = make_registry()

    def test_relative_escape_refused(self) -> None:
        out = self.registre.call("document_lire", {"path": "../../etc/passwd"})
        self.assertFalse(out["ok"])
        self.assertIn("atelier du run", out["error"])

    def test_absolute_path_refused(self) -> None:
        out = self.registre.call("document_lire", {"path": "/etc/passwd"})
        self.assertFalse(out["ok"])
        self.assertIn("absolu", out["error"])

    def test_unknown_tool_is_an_observation(self) -> None:
        out = self.registre.call("rm_rf", {"path": "/"})
        self.assertFalse(out["ok"])
        self.assertIn("outil inconnu", out["error"])
        self.assertIn("hint", out)

    def test_missing_argument(self) -> None:
        out = self.registre.call("document_lire", {})
        self.assertFalse(out["ok"])
        self.assertIn("manquants", out["error"])

    def test_extra_argument(self) -> None:
        out = self.registre.call("document_lire", {"path": "a.txt", "verbose": True})
        self.assertFalse(out["ok"])
        self.assertIn("inconnus", out["error"])

    def test_invalid_date_rejected(self) -> None:
        out = self.registre.call(
            "echeance_ajouter",
            {"kind": "taxe", "label": "x", "due": "3e lundi d'octobre 2027", "source": "a.txt"},
        )
        self.assertFalse(out["ok"])
        self.assertIn("AAAA-MM-JJ", out["error"])

    def test_impossible_date_rejected(self) -> None:
        out = self.registre.call("echeance_ajouter", {"kind": "taxe", "label": "x", "due": "2027-02-31", "source": "a.txt"})
        self.assertFalse(out["ok"])
        self.assertIn("inexistante", out["error"])


class TestExtraction(unittest.TestCase):
    def test_pdf_text_layer(self) -> None:
        text = extraire_texte(BASE / "documents" / "classeur" / "assurance-habitation.pdf")
        self.assertIn("Franchise degats des eaux : 250 EUR", text)
        self.assertIn("Renouvellement automatique le 30 juin 2027", text)

    def test_docx(self) -> None:
        text = extraire_texte(BASE / "documents" / "classeur" / "garantie-chaudiere.docx")
        self.assertIn("Fin de garantie : 28 fevrier 2027", text)

    def test_unsupported_format(self) -> None:
        path = _TMP / "sample.bin"
        path.write_bytes(b"\x00\x01")
        with self.assertRaises(Exception):
            extraire_texte(path)


class TestHttpApi(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.httpd = serveur.make_server("127.0.0.1", 0)
        cls.port = cls.httpd.server_address[1]
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def _get(self, path: str) -> tuple[int, dict[str, str], bytes]:
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}{path}", timeout=10) as response:
            return response.status, dict(response.headers), response.read()

    def test_healthz(self) -> None:
        status, _, body = self._get("/healthz")
        self.assertEqual(status, 200)
        self.assertTrue(json.loads(body)["ok"])

    def test_index_is_html(self) -> None:
        status, headers, body = self._get("/")
        self.assertEqual(status, 200)
        self.assertIn("text/html", headers["Content-Type"])
        self.assertIn("Classeur".encode(), body)

    def test_run_then_artifact_has_charset(self) -> None:
        request = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/api/run",
            data=json.dumps({"scenario": "echeances", "mode": "cassette"}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            result = json.loads(response.read().decode())
        self.assertEqual(result["status"], "done")
        status, headers, body = self._get(f"/api/artifact?run={result['run_id']}&name=livrables/echeances.md")
        self.assertEqual(status, 200)
        self.assertIn("charset=utf-8", headers["Content-Type"])
        self.assertIn("Échéances".encode("utf-8"), body)

    def test_artifact_escape_refused(self) -> None:
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._get("/api/artifact?run=../../etc&name=passwd")
        self.assertIn(ctx.exception.code, (403, 404))


if __name__ == "__main__":
    unittest.main(verbosity=2)
