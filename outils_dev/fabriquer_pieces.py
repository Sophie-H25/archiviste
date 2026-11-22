#!/usr/bin/env python3
"""Génère les documents de démonstration — tous synthétiques.

Aucun document réel n'est embarqué : les identités, adresses, contrats et
montants sont inventés, les domaines sont en ``.invalid`` et l'immatriculation
``AB-123-CD`` est le format d'exemple réglementaire français.

    python outils_dev/fabriquer_documents.py

Les fichiers binaires (PDF, DOCX) sont versionnés pour que la démo fonctionne
sans lancer ce script ; il existe pour que le jury puisse vérifier qu'ils sont
bien générés, et pas récupérés.
"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLASSEUR = ROOT / "documents" / "classeur"
TAXE = ROOT / "documents" / "taxe"


# --------------------------------------------------------------------------- #
# PDF minimal (une page, texte non compressé, police Helvetica standard)
# --------------------------------------------------------------------------- #
def build_pdf(lines: list[str]) -> bytes:
    def escape(text: str) -> str:
        return text.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")

    stream = ["BT", "/F1 10 Tf", "56 800 Td", "14 TL"]
    for line in lines:
        stream.append(f"({escape(line)}) Tj")
        stream.append("T*")
    stream.append("ET")
    content = ("\n".join(stream) + "\n").encode("cp1252", "replace")

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"endstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
    ]

    out = io.BytesIO()
    out.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = []
    for index, body in enumerate(objects, start=1):
        offsets.append(out.tell())
        out.write(f"{index} 0 obj\n".encode() + body + b"\nendobj\n")
    xref = out.tell()
    out.write(f"xref\n0 {len(objects) + 1}\n".encode())
    out.write(b"0000000000 65535 f \n")
    for offset in offsets:
        out.write(f"{offset:010d} 00000 n \n".encode())
    out.write(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    )
    return out.getvalue()


# --------------------------------------------------------------------------- #
# DOCX minimal (un paragraphe par ligne)
# --------------------------------------------------------------------------- #
def build_docx(lines: list[str]) -> bytes:
    def paragraph(text: str) -> str:
        safe = (
            text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
        )
        return f"<w:p><w:r><w:t xml:space=\"preserve\">{safe}</w:t></w:r></w:p>"

    body = "".join(paragraph(line) for line in lines)
    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{body}</w:body></w:document>"
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-'
        'officedocument.wordprocessingml.document.main+xml"/></Types>'
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/'
        'relationships/officeDocument" Target="word/document.xml"/></Relationships>'
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", rels)
        archive.writestr("word/document.xml", document)
    return buffer.getvalue()


# --------------------------------------------------------------------------- #
# Contenus
# --------------------------------------------------------------------------- #
ASSURANCE_HABITATION = [
    "AXELLA ASSURANCES - document de demonstration",
    "ATTESTATION D'ASSURANCE HABITATION",
    "Contrat numero HAB-2024-88421",
    "Assure : Camille Martin",
    "Bien assure : 14 rue des Tilleuls, 31000 Toulouse",
    "",
    "Cotisation : 462,00 EUR par an, soit 38,50 EUR par mois.",
    "Renouvellement automatique le 30 juin 2027.",
    "Preavis de resiliation : deux mois avant l'echeance.",
    "",
    "GARANTIES",
    "- Degats des eaux : dommages immobiliers et mobiliers pris en charge.",
    "- Franchise degats des eaux : 250 EUR par sinistre.",
    "- Plafond mobilier : 45 000 EUR.",
    "- Vol et vandalisme : franchise de 300 EUR.",
    "",
    "Ce document est fictif et sert uniquement a la demonstration.",
]

ASSURANCE_AUTO = """From: Camille Martin <camille.martin@example.invalid>
To: contact@axella.invalid
Subject: Attestation annuelle - contrat auto AUT-2025-31774
Date: Mon, 02 Nov 2026 09:12:00 +0100
MIME-Version: 1.0
Content-Type: text/plain; charset=utf-8

Bonjour,

Votre contrat auto AUT-2025-31774 arrive a echeance le 15/04/2027.
La cotisation annuelle s'eleve a 612,00 EUR, prelevable en une fois.
Vehicule assure : Renault Clio, immatriculation AB-123-CD.

Merci de nous signaler tout changement de situation avant le 15/03/2027.

Bien cordialement,
Service client AXELLA (adresse de demonstration, ne pas repondre)
"""

CONTROLE_TECHNIQUE = """CENTRE DE CONTROLE TECHNIQUE DES TILLEULS - document de demonstration
Proces-verbal de controle technique periodique

Vehicule : AB-123-CD
Date du controle : 12 janvier 2027
Resultat : conforme, aucun defaut a corriger

Prochain controle technique a effectuer avant le 12/01/2027 :
presenter le vehicule muni de la carte grise et du present proces-verbal.

Document fictif, genere pour la demonstration Classeur.
"""

GARANTIE_CHAUDIERE = [
    "GARANTIE - CHAUDIERE MURALE",
    "Appareil : Thermorane T-24, numero de serie 4471-AA",
    "Installation realisee le 28 fevrier 2022 par Chauffage Durand (Toulouse).",
    "Garantie fabricant : 5 ans, pieces et main d'oeuvre.",
    "Fin de garantie : 28 fevrier 2027.",
    "L'entretien annuel est obligatoire pour conserver la garantie.",
    "Document fictif de demonstration.",
]

ABONNEMENT = """service,formule,montant_mensuel,engagement,reconduction,echeance
Salle Forme Plus (Toulouse),annuel,29.90,12 mois,reconduction tacite,2027-05-01
"""

TAXE_FONCIERE = """AVIS DE TAXE FONCIERE - document de demonstration
Exercice 2027
Commune de Toulouse
Montant a payer : 1 342,00 EUR
Le reglement doit intervenir avant le 3e lundi d'octobre 2027.
Paiement en ligne ou par prelevement mensuel.
Document fictif, genere pour la demonstration Classeur.
"""


def main() -> int:
    CLASSEUR.mkdir(parents=True, exist_ok=True)
    TAXE.mkdir(parents=True, exist_ok=True)

    (CLASSEUR / "assurance-habitation.pdf").write_bytes(build_pdf(ASSURANCE_HABITATION))
    (CLASSEUR / "assurance-auto.eml").write_text(ASSURANCE_AUTO, encoding="utf-8")
    (CLASSEUR / "controle-technique.txt").write_text(CONTROLE_TECHNIQUE, encoding="utf-8")
    (CLASSEUR / "garantie-chaudiere.docx").write_bytes(build_docx(GARANTIE_CHAUDIERE))
    (CLASSEUR / "abonnement-salle.csv").write_text(ABONNEMENT, encoding="utf-8")
    (TAXE / "taxe-fonciere.txt").write_text(TAXE_FONCIERE, encoding="utf-8")

    for path in sorted(list(CLASSEUR.iterdir()) + list(TAXE.iterdir())):
        print(f"{path.relative_to(ROOT)}  {path.stat().st_size} o")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
