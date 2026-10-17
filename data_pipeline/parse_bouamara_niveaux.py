"""K. Bouamara, « Lmed taqbaylit s yiswiren – Apprendre le kabyle par niveaux »
(HAL hal-05580987, 2026, CC BY-NC-ND 4.0) → JSON Lines kabyle/français/anglais.

    python parse_bouamara_niveaux.py document_2.pdf ../data/bouamara_niveaux.jsonl

Licence ND (pas de modification) : les phrases sont gardées telles quelles,
avec attribution ; usage non commercial ; elles servent de références citées
par le prof, pas de données d'entraînement.
Le tableau a 3 colonnes (x < 210 kabyle, < 385 français, sinon anglais) ;
une ligne « Litt. » sous le français donne la traduction littérale.
"""
import json
import re
import sys
import unicodedata

import pymupdf

LEVELS = {0: "Mots isolés", 1: "Débutant (A1)", 2: "Élémentaire (A2)", 3: "Intermédiaire (B1)",
          4: "Avancé (B2)", 5: "Expert (C1)"}
SRC = "K. Bouamara, Lmed taqbaylit s yiswiren – Apprendre le kabyle par niveaux, HAL hal-05580987, 2026 (CC BY-NC-ND 4.0)"


def main(pdf, out):
    doc = pymupdf.open(pdf)
    rows, level = [], None
    for pno, page in enumerate(doc):
        lines = []
        for b in page.get_text("dict")["blocks"]:
            for ln in b.get("lines", []):
                t = "".join(s["text"] for s in ln["spans"]).strip()
                y0, y1, x = ln["bbox"][1], ln["bbox"][3], ln["bbox"][0]
                if t and 55 < y0 < 770:
                    lines.append((y0, y1, x, t))
        lines.sort()
        # 1. regrouper en rangées du tableau : nouvelle rangée si écart vertical > 3 pt
        groups, bottom = [], -99
        for y0, y1, x, t in lines:
            m = re.match(r"Niveau (\d)\b", t)
            if m:
                groups.append(("LEVEL", int(m.group(1))))
                bottom = -99
                continue
            if t.startswith(("Table des matières", "Bibliographie")):
                groups.append(("END", None))
                break
            if re.match(r"^\d+ entrées$", t) or t in ("Kabyle (Taqbaylit)", "Français", "English"):
                continue
            if not groups or groups[-1][0] != "ROW" or y0 > bottom + 3:
                groups.append(("ROW", []))
            groups[-1][1].append((y0, x, t))
            bottom = max(bottom, y1) if groups[-1][1][:-1] else y1
        # 2. chaque rangée → kab / fr / en (ou « Litt. » rattaché à la rangée précédente)
        for kind, val in groups:
            if kind == "LEVEL":
                level = val
                continue
            if kind == "END":
                level = None
                continue
            if level is None:
                continue
            cell = {"kab": [], "fr": [], "en": []}
            for y0, x, t in sorted(val):
                cell["kab" if x < 210 else ("fr" if x < 385 else "en")].append(t)
            fr = " ".join(cell["fr"])
            if not cell["kab"] and fr.startswith("Litt.") and rows:
                rows[-1]["lit"] = fr[5:].strip()
                continue
            if not cell["kab"] and rows:  # suite d'une rangée coupée
                for k in ("fr", "en"):
                    rows[-1][k] += " " + " ".join(cell[k])
                continue
            rows.append({"kab": " ".join(cell["kab"]), "fr": fr, "en": " ".join(cell["en"]),
                         "level": level, "page": pno})
    # 3. Recoller les entrées coupées par un saut de page (le tableau n'est pas « en miroir »
    #    d'une page à l'autre) : suite sans numéro qui commence en minuscule, ou cellule orpheline.
    END = re.compile(r"[.!?»…;)\]”\"]\s*$")
    LABEL = re.compile(r"^(?:\d+\.)?(?:\d+[a-z]?|[a-z])\.\s")
    merged = []
    for r in rows:
        prev = merged[-1] if merged else None
        orphan = prev and (not r["fr"] or not r["kab"]) and r["level"] == prev["level"]
        page_cut = (prev and r["page"] != prev["page"] and r["level"] == prev["level"] and prev["level"] > 0
                    and (not END.search(prev["fr"]) or not END.search(prev["kab"]))
                    and not LABEL.match(r["kab"])
                    and (r["fr"][:1].islower() or r["kab"][:1].islower()))
        if orphan or page_cut:
            for k in ("kab", "fr", "en"):
                if r[k]:
                    prev[k] = (prev[k] + " " + r[k]).strip()
            if r.get("lit"):
                prev["lit"] = r["lit"]
            prev.setdefault("merged_pages", []).append(r["page"])
            continue
        merged.append(r)
    rows = merged
    out_rows = []
    for r in rows:
        for k in ("kab", "fr", "en", "lit"):
            if k in r:
                r[k] = unicodedata.normalize("NFC", re.sub(r"\s+", " ", re.sub(r"(\w)- (\w)", r"\1-\2", r[k]))).strip()
        if r["kab"] and r["fr"]:
            r.update({"level_name": LEVELS[r["level"]], "source": SRC, "license": "CC BY-NC-ND 4.0",
                      "kind": "word" if r["level"] == 0 else "sentence", "needs_review": False})
            out_rows.append(r)
    with open(out, "w", encoding="utf-8") as f:
        for r in out_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    from collections import Counter
    print(len(out_rows), dict(sorted(Counter(r["level"] for r in out_rows).items())))


if __name__ == "__main__":
    main(*sys.argv[1:3])
