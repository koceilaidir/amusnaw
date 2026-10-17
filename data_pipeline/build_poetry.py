"""Poésie kabyle des recueils HCA : un vers par ligne, strophes séparées par un
écart vertical plus grand. build_corpus.py coupe aux points et perdait presque
tous les vers (pas de ponctuation finale). Ici on découpe par STROPHE.

    python build_poetry.py <dossier_pdf> ../data/corpus_poesie.jsonl
"""
import json
import re
import statistics
import sys
import unicodedata
from pathlib import Path

import pymupdf

from build_corpus import ARABIC, FR_WORDS, GREEK, KAB_WORDS, TIFINAGH, WORD, title_of
from kabyle_fonts import convert_span

BOOKS = ["2004/05", "2004/06", "2004/07", "2004/11", "2004/12", "2019/01", "2025/07"]


def kabyle_enough(text):
    if ARABIC.search(text) or TIFINAGH.search(text):
        return False
    words = [w.lower() for w in WORD.findall(text)]
    if not 3 <= len(words) <= 60:
        return False
    fr = sum(w in FR_WORDS for w in words)
    kab = sum(w in KAB_WORDS for w in words) + sum(1 for w in words if re.search(r"[ɛɣḍṭẓṛṣḥčǧ]", w))
    return kab >= 1 and fr <= 1 and kab >= fr * 2


def stanzas(page):
    lines = []
    for b in page.get_text("dict")["blocks"]:
        for ln in b.get("lines", []):
            t = "".join(convert_span(s["text"], s["font"]) for s in ln["spans"]).strip()
            t = unicodedata.normalize("NFC", t.translate(GREEK))
            if t and not re.fullmatch(r"[-–—\s\d]+|-?o0o-?", t):
                lines.append((ln["bbox"][1], t))
    lines.sort()
    if len(lines) < 2:
        return []
    gaps = [b[0] - a[0] for a, b in zip(lines, lines[1:]) if b[0] > a[0]]
    step = statistics.median(gaps) if gaps else 15
    out, cur, prev = [], [], None
    for y, t in lines:
        if prev is not None and (y - prev > step * 1.6 or len(cur) >= 6):
            out.append(cur)
            cur = []
        cur.append(t)
        prev = y
    if cur:
        out.append(cur)
    return out


def main(root, out_path):
    root = Path(root)
    rows, seen = [], set()
    for prefix in BOOKS:
        for pdf in sorted(root.glob(f"{prefix}*/livre.pdf")):
            book = pdf.parent
            src = title_of(book)
            doc = pymupdf.open(pdf)
            kept = 0
            for i, page in enumerate(doc):
                for st in stanzas(page):
                    text = " / ".join(st)
                    key = re.sub(r"\W+", "", text.lower())
                    if key in seen or len(st) < 2 or not kabyle_enough(text):
                        continue
                    seen.add(key)
                    rows.append({"kab": text, "source": src, "page": i + 1, "book": str(book.relative_to(root)),
                                 "genre": "poésie"})
                    kept += 1
            print(f"{kept:5d} strophes  {book.name[:60]}")
    with open(out_path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"total {len(rows)} strophes")


if __name__ == "__main__":
    main(*sys.argv[1:3])
