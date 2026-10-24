"""J.-M. Dallet, Dictionnaire français-kabyle (SELAF, 1985) → data/dallet_fk.jsonl

Le PDF contient une couche de texte issue d'une reconnaissance optique ancienne :
les lettres kabyles y sont abîmées (ɛ → e/€/t, ɣ → y/$/4, points souscrits perdus).
Chaque forme kabyle est restaurée à partir du kabyle attesté (kab_vocab.py) :
  confident=true  → toutes les formes retrouvées : utilisable tel quel ;
  confident=false → au moins une forme non retrouvée : à relire (/review).

Utilisation autorisée pour améliorer l'IA d'Amusnaw (autorisation obtenue par le HCA, oct. 2026).

  python parse_dallet_fk.py DALLET-F-K.pdf ../data
"""
import json
import re
import sys
from pathlib import Path

import pymupdf

from kab_vocab import Vocab

SRC = "J.-M. Dallet, Dictionnaire français-kabyle, SELAF, 1985"
# forme(s) kabyle(s) + racine (capitales) + numéro de page du Dallet kabyle-français
ROOTED = re.compile(r"(?P<kab>[^:|]*?)\s+(?P<root>[A-Z€$ÀÈÉÇ¥Ğ\.]{1,7}[A-Z€$])\s*(?P<num>[\dlIOt][\dlIOt ]{0,5})\s*[.,]?")
HEAD = re.compile(r"^(?P<fr>[A-ZÀ-Ý][^\s:;|]*(?:\s+[a-zà-ÿ'’\-]+){0,3}(?:\s*\([^)]*\)?)?)\s*[:;|iI'’]\s+")
SUB = re.compile(r"(?:^|\s)(?:ll|Il|II|\|\|)\s*")


def clean_page(t: str) -> list[str]:
    lines = [l.rstrip() for l in t.splitlines()]
    out = []
    for i, l in enumerate(lines):
        if i == 0 and re.fullmatch(r"[A-ZÀ-Ý' \-]{2,}", l.strip()):
            continue  # titre courant
        if re.fullmatch(r"\s*\d{1,3}\s*", l):
            continue  # numéro de page
        if l.strip():
            out.append(l.strip())
    return out


HEADWORD = re.compile(r"(?:^|(?<=[\d.,)]\s)|(?<=\.\s\s))(?P<fr>[A-ZÀ-Ý][a-zà-ÿœ'’\-]+(?:\s[a-zà-ÿœ'’\-]+){0,3}"
                      r"(?:\s?\([^)]{0,50}\)?)?)\s?[:;]\s")


def entries(lines: list[str]):
    """Le texte en un seul flux, coupé à chaque mot d'entrée français (« Arracher : … »)."""
    text = ""
    for l in lines:
        text = text[:-1] + l if text.endswith("-") and l[:1].islower() else (text + " " + l if text else l)
    starts = [m.start("fr") for m in HEADWORD.finditer(text)]
    for a, b in zip(starts, starts[1:] + [len(text)]):
        yield text[a:b].strip()


def kab_forms(seg: str) -> list[str]:
    seg = seg.strip(" .,;:")
    seg = re.sub(r"^.*?[:;|]\s+", "", seg) if re.search(r"[:;|]\s", seg) else seg
    parts = re.split(r"\s*[,/]\s*", seg)
    return [p for p in (x.strip(" .-'") for x in parts) if p and re.search(r"[a-zɛɣ€$]", p) and len(p) <= 40]


def main(pdf: str, data: str):
    data = Path(data)
    vocab = Vocab.load(data)
    doc = pymupdf.open(pdf)
    lines = []
    for p in doc:
        lines += clean_page(p.get_text())
    out, n_ok = [], 0
    for e in entries(lines):
        m = HEADWORD.match(e)
        if not m:
            continue
        head = re.sub(r"\s+", " ", m.group("fr")).strip()
        body = e[m.end():]
        # sous-sens : « ll (contexte) : … », « être - : … », « - de fusil : … »
        for chunk in SUB.split(body):
            ctx = ""
            cm = re.match(r"^\s*(\([^)]*\)|[^:;|]{1,40}?)\s*[:;|]\s+", chunk)
            if cm and not ROOTED.fullmatch(cm.group(1) + " X 1"):
                ctx = cm.group(1).strip()
                chunk = chunk[cm.end():]
            fr = head if not ctx else (head + " " + ctx if ctx.startswith("(") else ctx.replace("-", head.split(" (")[0].lower()))
            for rm in ROOTED.finditer(chunk + " "):
                forms = kab_forms(rm.group("kab"))
                if not forms:
                    continue
                restored = [vocab.restore(f) for f in forms]
                ok = all(r[1] for r in restored)
                n_ok += ok
                out.append({"fr": fr, "kab": ", ".join(r[0] for r in restored), "forms": [r[0] for r in restored],
                            "root": rm.group("root").replace("€", "Ɛ").replace("$", "Ɣ"), "ocr": rm.group("kab").strip(),
                            "confident": ok, "source": SRC})
    dst = data / "dallet_fk.jsonl"
    with dst.open("w", encoding="utf-8") as f:
        for r in out:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"{len(out)} entrées, dont {n_ok} sûres ({100 * n_ok / max(len(out), 1):.0f} %) → {dst}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "../data")
