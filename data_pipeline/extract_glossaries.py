"""Glossaires kabyle → français placés à la fin des romans traduits
(néologismes et mots rares expliqués par le traducteur).

Usage :
  python extract_glossaries.py <feraoun_kab.pdf> <petit_prince_kab.txt> ../data/glossaries.jsonl
"""

import json
import re
import sys

import pymupdf

from kabyle_fonts import convert_span


def feraoun_glossary(pdf: str):
    """Deux colonnes : kabyle à gauche, français à droite, sur la même ligne."""
    doc = pymupdf.open(pdf)
    start = next(i for i, p in enumerate(doc) if "Amawal :" in "".join(
        s["text"] for b in p.get_text("dict")["blocks"] for l in b.get("lines", []) for s in l["spans"]))
    rows = []
    for page in doc[start:]:
        lines = {}
        for b in page.get_text("dict")["blocks"]:
            for l in b.get("lines", []):
                for s in l["spans"]:
                    t = convert_span(s["text"], s["font"]).strip()
                    if not t or s["font"].startswith("TimesNewRoman"):
                        continue
                    y = round(l["bbox"][1])
                    side = "fr" if s["bbox"][0] >= 200 else "kab"
                    lines.setdefault(y, {"kab": "", "fr": ""})[side] += " " + t
        for y in sorted(lines):
            kab, fr = lines[y]["kab"].strip(), lines[y]["fr"].strip()
            if kab and not fr:  # « Akerdis, pl. ikerdisen  Triangle » dans un seul morceau
                m = re.match(r"^(.+?\S)\s{2,}(\S.*)$", kab)
                if m:
                    kab, fr = m.group(1), m.group(2)
            if kab.startswith("Amawal") or "ilul ass" in kab:
                continue
            if kab and fr:
                rows.append((kab, fr))
            if "Mouloud Feraoun ilul" in kab:
                break
    return rows


def petit_prince_glossary(txt: str):
    """Entrées « - Mot (pluriel) : sens. » après la ligne d'étoiles finale."""
    text = open(txt, encoding="utf-8").read()
    text = re.split(r"\n\* \* \*[ *]*\n", text, maxsplit=1)[1]
    text = re.sub(r"\n(## \d+|[A-ZƐƔḌṬẒṚṢḤČǦ])\n", "\n", text)  # lettres-titres
    flat = re.sub(r"\s+", " ", text)
    rows = []
    for entry in re.split(r"(?:^| )- ", flat):
        m = re.match(r"^(.+?)\s*:\s*(.+?)\.?\s*$", entry.strip())
        if m:
            rows.append((m.group(1).strip(), m.group(2).strip()))
    return rows


def main(feraoun_pdf: str, pp_txt: str, out: str) -> None:
    n = 0
    with open(out, "w", encoding="utf-8") as f:
        for src, rows in [
            ("Mmis n igellil (trad. M. Ould Taleb, HCA 2004), glossaire", feraoun_glossary(feraoun_pdf)),
            ("Ageldun amecṭuḥ (trad. H.-A. Mansouri, HCA 2004), glossaire", petit_prince_glossary(pp_txt)),
        ]:
            for kab, fr in rows:
                # « z. Tamtiwegt » = renvoi au singulier : on le garde comme note
                f.write(json.dumps({"kab": kab, "fr": fr, "kind": "glossary", "domain": "général",
                                    "source": src, "needs_review": True}, ensure_ascii=False) + "\n")
                n += 1
    print(f"{n} entrées de glossaire")


if __name__ == "__main__":
    main(*sys.argv[1:4])
