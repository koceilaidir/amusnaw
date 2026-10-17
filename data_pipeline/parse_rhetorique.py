"""K. Bouamara, « Amawal n tunuɣin n tesnukyest — Lexique de la rhétorique » (HCA 2007).

    python parse_rhetorique.py livre.pdf ../data/lexicon_rhetorique.jsonl ../data/corpus_rhetorique.jsonl

- p. 62-67 : « Lexèmes français et leurs équivalents amazighs » (« Litote : tasedreft. »)
- le reste : essai en kabyle → phrases ajoutées au corpus (exemples d'emploi).
"""
import json
import re
import sys
import unicodedata

import pymupdf

from build_corpus import SENT, is_kabyle
from kabyle_fonts import convert_span

SRC = "K. Bouamara, Amawal n tunuɣin n tesnukyest — Lexique de la rhétorique, HCA 2007"


def page_text(page):
    out = []
    for b in page.get_text("dict")["blocks"]:
        for ln in b.get("lines", []):
            t = "".join(convert_span(s["text"], s["font"]) for s in ln["spans"]).strip()
            if t and not re.fullmatch(r"-?\s*\d+\s*-?|Kamel Bouamara|Amawal n tesnukyest", t):
                out.append(t)
    return unicodedata.normalize("NFC", " ".join(out))


def _entries(text, kab_first):
    out = []
    text = re.sub(r"\b[A-ZƐƔḌṬẒṚṢḤČǦ] –\s", " ", text)  # lettres d'en-tête « D – »
    for m in re.finditer(r"([^:=.;]{2,70}?)\s*[:=]\s*([^.]{1,160})\.", text):
        left, right = m.group(1).strip(" –-"), m.group(2).strip()
        if kab_first:
            kab = re.sub(r"\s*\(.*?\)", "", left).replace("/", "").strip()
            fr, note = right, None
        else:
            fr = re.sub(r"\s*\((?:une?|le|la|l’|les)\)", "", left).strip()
            kab = re.split(r"\s*\[", right)[0].strip(" ;,")
            note = right[len(kab):].strip(" ;") or None
            kab = re.sub(r"^t-(\w+)-t$", r"t\1t", kab).replace("/", "")
        fr = re.split(r"\s*\[", fr)[0].strip(" ;,")
        if not re.fullmatch(r"[a-zA-ZɛɣḍṭẓṛṣḥčǧƐƔḌṬẒṚṢḤČǦ() -]+", kab) or re.search(r"[ɛɣḍṭẓṛṣḥčǧ]", fr):
            continue
        if not kab or not fr or len(kab) > 50 or len(fr) > 80 or len(kab.split()) > 4:
            continue
        out.append({"kab": kab, "fr": fr[0].lower() + fr[1:], "note": note, "kind": "entry",
                    "domain": "langue et didactique", "source": SRC, "needs_review": True})
    return out


def main(pdf, lex_out, corpus_out):
    doc = pymupdf.open(pdf)
    find = lambda key: max(i for i in range(len(doc)) if key in doc[i].get_text() and "……" not in doc[i].get_text())  # noqa: E731
    kab_start, fr_start = find("Lexèmes amazighs"), find("Lexèmes français et leurs")
    end = next((i for i in range(fr_start, len(doc)) if re.search(r"\d+- [A-Z]", doc[i].get_text())), len(doc))
    kab_text = " ".join(page_text(doc[i]) for i in range(kab_start, fr_start)).split("Lexèmes amazighs", 1)[-1]
    fr_text = " ".join(page_text(doc[i]) for i in range(fr_start, end)).split("amazighs", 1)[-1]
    entries = _entries(kab_text, True) + _entries(fr_text, False)
    with open(lex_out, "w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    sents = []
    for i in range(12, kab_start):
        for s in SENT.split(page_text(doc[i])):
            s = s.strip(" -–—")
            if is_kabyle(s):
                sents.append({"kab": s, "source": SRC, "page": i + 1})
    with open(corpus_out, "w", encoding="utf-8") as f:
        for s in sents:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")
    print(f"{len(entries)} termes, {len(sents)} phrases kabyles (pages {kab_start}-{end})")


if __name__ == "__main__":
    main(*sys.argv[1:4])
