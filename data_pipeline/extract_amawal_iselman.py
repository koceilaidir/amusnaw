"""Extraction du livre « Amawal n yiɣersiwen n yilel »
(M. Djeghali & S. Sellah, HCA 2010) — lexique kabyle des animaux marins.

Produit, dans data/ :
  - book2_text.txt           texte complet converti en Unicode
  - lexicon.jsonl            mots kabyle ↔ français (fiches, index, glossaire)
  - sentences.jsonl          phrases kabyles authentiques (descriptions)

Usage : python extract_amawal_iselman.py livre_2.pdf ../data
Toutes les lignes sortent avec needs_review=true : un linguiste valide.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

from legacy_kabyle import convert_line, convert_text

SOURCE = "Djeghali & Sellah, Amawal n yiɣersiwen n yilel, HCA 2010"

HEADER = re.compile(r"^\s*(\d{1,3})\.\s+\S")
DEF_LINE = re.compile(r"^\s*(?P<name>[^:]{2,60}?)\d*\s*:\s*(sm|ml|nt)\.")
PAGE_NO = re.compile(r"^\s*-\s*\d+\s*-\s*$")
FOOTNOTE_NUM = re.compile(r"^\s*\d\s*$")
FOOTNOTE_TXT = re.compile(r"^\s*-\s*(.+)$")
INDEX_LINE = re.compile(r"^\s*(?P<kab>[^:]{2,60}?)\s*:\s*d isem (?P<gram>[^:]+?)\s*:\s*(?P<fr>[^:]+?)\.?\s*$")
GLOSS_LINE = re.compile(r"^(?P<kab>\S.*?\S)\s{3,}(?P<fr>\S.*\S)\s*$")


def pdf_text(pdf: Path) -> str:
    return subprocess.run(["pdftotext", "-layout", str(pdf), "-"],
                          check=True, capture_output=True, text=True).stdout


def clean(s: str) -> str:
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"(\w)(\d)\s*:", r"\1 :", s)  # appel de note collé au mot
    return s


def split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+(?=[A-ZƐƔḌḤṚṢṬẒČǦ])", text)
    out = []
    for p in parts:
        p = p.strip()
        if len(p.split()) >= 4 and not re.search(r"Dallet|sb\.|\(uṭ \d+\)$", p):
            out.append(p)
    return out


def parse(raw: str):
    lines = raw.splitlines()
    lexicon, sentences = [], []

    # ---------- 1. Fiches numérotées ----------
    # Les fiches vont de la 1re à la page « Amawal » finale.
    end_all = next((i for i, l in enumerate(lines) if l.strip() == "Amawal" and i > 3000), len(lines))
    headers = [i for i, l in enumerate(lines[:end_all]) if HEADER.match(l)]
    page = None
    for n, start in enumerate(headers):
        stop = headers[n + 1] if n + 1 < len(headers) else end_all
        block = lines[start:stop]
        num = int(HEADER.match(block[0]).group(1))
        french = next((b.strip() for b in block[1:] if b.strip()), "")
        if not french or len(french) > 60 or DEF_LINE.match(french):
            continue

        kab_name, desc_lines, regions, in_note = None, [], [], False
        for b in block[2:]:
            if PAGE_NO.match(b):
                page = int(re.sub(r"\D", "", b))
                continue
            if FOOTNOTE_NUM.match(b):
                in_note = True
                continue
            if in_note:
                m = FOOTNOTE_TXT.match(b)
                if m:
                    regions.append(convert_line(m.group(1)).strip(" ."))
                    continue
                if b.strip():
                    in_note = False
                else:
                    continue
            m = DEF_LINE.match(b)
            if kab_name is None and m:
                kab_name = clean(convert_line(m.group("name")))
            if b.strip() == french:
                continue
            desc_lines.append(b)

        if not kab_name:
            continue
        description = clean(convert_text("\n".join(desc_lines)))
        lexicon.append({
            "kab": kab_name, "fr": french, "kind": "entry", "domain": "animaux marins",
            "entry_no": num, "page": page, "regions": regions,
            "description_kab": description, "source": SOURCE, "needs_review": True,
        })
        for s in split_sentences(description):
            sentences.append({"kab": s, "about": kab_name, "fr_topic": french,
                              "page": page, "source": SOURCE, "needs_review": True})

    # ---------- 2. Index « Nom : d isem … : Français » ----------
    for l in lines[:end_all]:
        m = INDEX_LINE.match(l)
        if m and "sm." not in l:
            lexicon.append({
                "kab": clean(convert_line(m.group("kab"))),
                "fr": m.group("fr").strip(),
                "grammar": clean(convert_line(m.group("gram"))),
                "kind": "index", "domain": "animaux marins",
                "source": SOURCE, "needs_review": True,
            })

    # ---------- 3. Glossaire final kabyle → français ----------
    try:
        g0 = next(i for i, l in enumerate(lines) if "Isem-is s Tafransist" in l)
        g1 = next(i for i, l in enumerate(lines) if i > g0 and re.search(r"Tagrayt|Tiɣbula|Bibliographie|^\s*01-", l))
    except StopIteration:
        g0 = g1 = 0
    for l in lines[g0 + 1:g1]:
        m = GLOSS_LINE.match(l)
        if m and not PAGE_NO.match(l):
            lexicon.append({
                "kab": clean(convert_line(m.group("kab"))), "fr": m.group("fr").strip(),
                "kind": "glossary", "domain": "général",
                "source": SOURCE, "needs_review": True,
            })
    return lexicon, sentences


def main(pdf: str, out_dir: str) -> None:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    raw = pdf_text(Path(pdf))
    (out / "book2_text.txt").write_text(convert_text(raw), encoding="utf-8")
    lexicon, sentences = parse(raw)
    with open(out / "lexicon.jsonl", "a", encoding="utf-8") as f:
        for e in lexicon:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    with open(out / "sentences.jsonl", "a", encoding="utf-8") as f:
        for s in sentences:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")
    kinds = {}
    for e in lexicon:
        kinds[e["kind"]] = kinds.get(e["kind"], 0) + 1
    print(f"lexique: {len(lexicon)} {kinds} · phrases: {len(sentences)}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
