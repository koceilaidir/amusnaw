"""Petits lexiques en fin de livres HCA (« Amawal / Glossaire ») → JSON Lines.

    python extract_book_glossaries.py <dossier_pdf> ../data/lexicon_glossaires_livres.jsonl

Quatre mises en page :
  colon    « Aɣella : Chef »                            (Abane Ramdane, Llawel)
  numbered « 01 | Acengu | Ennemi »                     (Inagan, Imseɣret aɣelnaw : + arabe, retiré)
  triplet  « Tasnigit | Pragmatique | Asegzawal.net »   (Akeččum ɣer tefyirmant)
  bees     « Aglaf | L'essaim <arabe> »                 (Tizizwit d tamemt : lignes coupées)
Garde-fous : le côté kabyle ne doit pas avoir d'accents français, le côté
français ne doit pas avoir de lettres kabyles (ɣ ɛ ḍ…).
"""
import json
import re
import sys
import unicodedata
from pathlib import Path

import pymupdf

from build_corpus import GREEK, title_of
from kabyle_fonts import convert_span

BOOKS = [  # (préfixe, pages (index), format)
    ("2003/01", range(37, 40), "colon"),
    ("2004/07", range(121, 124), "colon"),
    ("2004/06", range(152, 156), "numbered"),
    ("2026/01", range(247, 260), "numbered"),
    ("2025/03", range(147, 152), "triplet"),
    ("2024/09", range(198, 205), "bees"),
]
ARABIC = re.compile(r"[؀-ۿﭐ-﷿ﹰ-﻿،]+")
KAB_ONLY = re.compile(r"[ɛɣḍṭẓṛṣḥčǧƐƔḌṬẒṚṢḤČǦ]")
FR_ONLY = re.compile(r"[éèêàâçùûôîœ]|\b(le|la|les|des|du|un|une|l’|l')\b", re.I)
SOURCE = re.compile(r"Asegzawal|Amawal n |\.net|^Berkai", re.I)


def lines(doc, pages, keep_numbers=False):
    out = []
    for i in pages:
        if i >= len(doc):
            continue
        for b in doc[i].get_text("dict")["blocks"]:
            for ln in b.get("lines", []):
                t = "".join(convert_span(s["text"], s["font"]) for s in ln["spans"])
                t = unicodedata.normalize("NFC", ARABIC.sub(" ", t).translate(GREEK))
                t = re.sub(r"\s+", " ", t).strip(" |")
                if keep_numbers and re.fullmatch(r"\d{1,3}\.?", t):
                    out.append((i, t))
                    continue
                if t and not re.fullmatch(r"-?\s*\d+\s*-?|AMAWAL.*|Amawal.*|Glossaire|Lexique|N°|Uṭ+un|un|Tam\w*|azi\w*|"
                                          r"Tafransist|Taɛrabt|rabt|Ta|Tamaziɣt|Français", t):
                    out.append((i, t))
    return out


def ok(kab, fr):
    kab, fr = kab.strip(" .;:-–"), fr.strip(" .;:-–")
    if not kab or not fr or len(kab) > 60 or len(fr) > 80:
        return None
    if re.search(r"[éèêàâçùûôîœ]", kab) or KAB_ONLY.search(fr):
        return None
    return kab, fr


def parse(fmt, ls):
    pairs = []
    if fmt == "colon":
        for pg, t in ls:
            m = re.match(r"^(.+?)\s*:\s*(.+)$", t)
            if m and (p := ok(re.sub(r"\s*\(.*?\)", "", m.group(1)), m.group(2))):
                pairs.append((pg, *p))
    elif fmt == "numbered":
        cur = None
        for pg, t in ls:
            m = re.match(r"^(\d{1,3})\.?\s*(.*)$", t)
            if m:
                if cur and len(cur[1]) >= 2 and (p := ok(cur[1][0], " ".join(cur[1][1:]))):
                    pairs.append((cur[0], *p))
                cur = (pg, [m.group(2)] if m.group(2) else [])
            elif cur is not None:
                cur[1].append(t)
        if cur and len(cur[1]) >= 2 and (p := ok(cur[1][0], " ".join(cur[1][1:]))):
            pairs.append((cur[0], *p))
    elif fmt == "triplet":
        seg = []
        for pg, t in ls:
            if SOURCE.search(t):
                if len(seg) >= 2 and (p := ok(seg[-2], seg[-1])):
                    pairs.append((pg, *p))
                seg = []
            else:
                seg.append(t)
    elif fmt == "bees":
        kab = []
        for pg, t in ls:
            looks_fr = bool(FR_ONLY.search(t)) and not KAB_ONLY.search(t)
            if looks_fr and kab:
                if p := ok(" ".join(kab), t):
                    pairs.append((pg, *p))
                kab = []
            elif not looks_fr:
                kab.append(t)
                kab = kab[-2:]
    return pairs


def main(root, out):
    rows = []
    for prefix, pages, fmt in BOOKS:
        for pdf in sorted(Path(root).glob(f"{prefix}*/livre.pdf")):
            src = title_of(pdf.parent)
            pairs = parse(fmt, lines(pymupdf.open(pdf), pages, fmt == "numbered"))
            seen = set()
            pairs = [(pg, k, re.sub(r"[^\w\s’',;:()\-–.!?/éèêàâçùûôîœ]", "", fr).strip())
                     for pg, k, fr in pairs if not (k.lower() in seen or seen.add(k.lower()))]
            for pg, kab, fr in pairs:
                rows.append({"kab": kab, "fr": fr[0].lower() + fr[1:] if not fr[:2].isupper() else fr,
                             "kind": "entry", "domain": "glossaires de livres", "page": pg + 1,
                             "source": f"{src}, glossaire", "needs_review": True})
            print(f"{len(pairs):4d}  {fmt:9} {pdf.parent.name[:60]}")
    with open(out, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print("total", len(rows))


if __name__ == "__main__":
    main(*sys.argv[1:3])
