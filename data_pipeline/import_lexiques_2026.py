"""Lexiques reçus en octobre 2026 (autorisations obtenues par le HCA) → data/lexicon_*.jsonl

  python import_lexiques_2026.py DOSSIER_DES_PDF ../data

DOSSIER_DES_PDF contient :
  lexique_informatique.pdf  Amawal n tsenselkimt (français-anglais-tamaziɣt)
  electrotechnique.pdf      Dictionnaire d'électrotechnique français-tamazight (2011)
  tesnilest.pdf             Amawal n tesnilest (terminologie linguistique)
  ighsan.pdf                Iɣsan s teqbaylit, vocabulaire de l'ostéologie et de l'orthopédie (2010)
  attanen.pdf               Amawal n waṭṭanen, vocabulaire des maladies (2012)
  fr_berbere.docx           Dictionnaire français-berbère (tableau de synonymes)

Les anciennes polices kabyles sont converties (kabyle_fonts.py). Les termes techniques
proposés par les auteurs sont des néologismes : domaine marqué, needs_review=true.
Pour le dictionnaire .docx (orthographe libre, plusieurs parlers mélangés), on ne garde
que les mots retrouvés dans le kabyle attesté (kab_vocab.py).
"""
import json
import re
import sys
from pathlib import Path

import pymupdf

from kab_vocab import Vocab
from kabyle_fonts import convert_span

TAGS = r"(?:MAT|KBL|MCƔ|MC£|MW|MZB|TRG|CLH|CW|CHL|TMZ|NFS|GHD|WRG|SNS|ZNG|MZ|TZ|KB|L\.M|P\.B|\?)"


def lines(pdf: Path) -> list[str]:
    out = []
    for page in pymupdf.open(pdf):
        for b in page.get_text("dict")["blocks"]:
            for ln in b.get("lines", []):
                t = "".join(convert_span(s["text"], s["font"]) for s in ln["spans"])
                t = re.sub(r"\s+", " ", t).strip()
                if t and not re.fullmatch(r"[-–\d ]+", t):
                    out.append(t)
    return out


def flow(ls: list[str]) -> str:
    text = ""
    for t in ls:
        text = text[:-1] + t if text.endswith("-") and t[:1].islower() else (text + " " + t if text else t)
    return text


KAB_OK = re.compile(r"^[a-zA-ZɣɛḍṭẓṛṣḥčǧƔƐḌṬẒṚṢḤČǦ' \-]+$")
FR_HINT = re.compile(r"[éèêàùçôîâœ]|\b(?:le|la|les|des|du|de|un|une|et|en|à|au|aux|qui|par)\b", re.I)


def clean_kab(k: str) -> str:
    k = re.sub(r"\s+pl\.?\s.*$", "", k)
    k = re.sub(r"\s*\*+", "", k)
    k = re.sub(rf"\s+{TAGS}\b.*$", "", k)
    k = re.split(r"\s*[(\[<;|,]\s*", k)[0]
    return k.strip(" .:-–")


def ok_kab(k: str) -> bool:
    return bool(k) and 1 <= len(k.split()) <= 5 and len(k) <= 50 and bool(KAB_OK.match(k)) \
        and not re.search(rf"\b{TAGS}\b", k)


def row(kab, fr, domain, source, page=None, **extra):
    fr = re.sub(r"^.*?Tamaziɣt\s+o\s+", "", fr)  # en-tête de page collé au terme
    fr = re.sub(r"\s+", " ", re.sub(r"[\d.]+$", "", fr)).strip(" .:;-")
    return {"kab": kab, "fr": fr[:1].upper() + fr[1:], "kind": "entry", "domain": domain, "source": source,
            "needs_review": True, **({"page": page} if page else {}), **extra}


# ---------- Amawal n tsenselkimt : « - Contexte (context): Tawennaṭ (pl. …) » ----------
def informatique(pdf):
    src = "Amawal n tsenselkimt (lexique informatique français-anglais-tamaziɣt)"
    text = flow(lines(pdf))
    out = []
    for m in re.finditer(r"(?:^|\s)[-o]\s+(?P<fr>[A-ZÉÈÀ][^():]{1,60}?)\s*\((?P<en>[^)]{1,60})\)\s*:\s*(?P<kab>[^-|]{1,120})", text):
        kab = clean_kab(m.group("kab"))
        if ok_kab(kab) and not re.search(r"[éèàùç]", kab):
            out.append(row(kab, m.group("fr"), "informatique (néologisme)", src, en=m.group("en").strip()))
    return out


# ---------- Électrotechnique : « CHARGER : V.t. … Proposition(s) : 1- Zdem < … » ----------
def electrotechnique(pdf):
    src = "Dictionnaire d'électrotechnique français-tamazight, 2011"
    text = flow(lines(pdf))
    out = []
    for m in re.finditer(r"(?P<fr>[A-ZÉÈÀÂÎÔÛÇ][A-ZÉÈÀÂÎÔÛÇ' \-]{2,50}?)\s*:\s*(?:\([^)]*\)\s*:?\s*)?[^:]{0,400}?"
                         r"Proposition\(s\)\s*:\s*(?:1-\s*)?(?P<kab>[^<\[\n]{1,60})", text):
        kab = clean_kab(m.group("kab"))
        fr = m.group("fr").strip().capitalize()
        if ok_kab(kab) and not re.search(r"[éèàùç]", kab) and len(fr.split()) <= 5:
            out.append(row(kab, fr, "électrotechnique (néologisme)", src))
    return out


# ---------- Amawal n tesnilest : « Défectif : amasar [ … » ----------
def tesnilest(pdf):
    src = "Amawal n tesnilest (terminologie linguistique)"
    out = []
    for t in lines(pdf):
        m = re.match(r"^(?P<fr>[A-ZÉÈÀ][\w’'\- ]{1,50}?(?:\s*\([^)]*\))?)\s*:\s*(?P<kab>[a-zɣɛḍṭẓṛṣḥčǧ][^\[:(]{0,50}?)\s*[\[:(]", t)
        if m:
            kab = clean_kab(m.group("kab"))
            if ok_kab(kab):
                out.append(row(kab, m.group("fr"), "linguistique (néologisme)", src))
    return out


# ---------- Iɣsan s teqbaylit, Amawal n waṭṭanen : « Kabyle: Français. » (et index français → kabyle) ----------
def kab_first(pdf, src, domain, vocab):
    def kab_score(x):
        ws = re.findall(r"[^\W\d_]+", x.lower())
        if not ws:
            return 0
        hits = sum(vocab.counts.get(w, 0) >= 2 for w in ws) + 2 * len(re.findall(r"[ɣɛḍṭẓṛṣḥčǧ]", x.lower()))
        return hits / len(ws) - (1 if FR_HINT.search(x) else 0)
    out = []
    for t in lines(pdf):
        t = re.sub(r"^\d{1,3}\s+", "", t)
        m = re.match(r"^(?P<a>[A-ZÉÈÀƐƔḌṬẒṚṢḤČǦ][^:]{1,60}?)\s*:\s*(?P<b>[^:]{2,160})$", t)
        if not m:
            continue
        a, b2 = m.group("a"), m.group("b")
        kab, fr = (a, b2) if kab_score(a) >= kab_score(b2) else (b2, a)
        if FR_HINT.search(kab) or re.search(r"[ɣɛḍṭẓṛṣḥčǧ]", fr):
            continue
        k = clean_kab(re.split(r"\s*;\s*", kab)[0])
        if ok_kab(k) and len(fr.split()) <= 12:
            k = k[:1].lower() + k[1:] if not k[1:2].isupper() else k
            out.append(row(k, fr.split(":")[0], domain, src))
    return out


# ---------- Dictionnaire français-berbère (.docx) : seulement les mots kabyles attestés ----------
def fr_berbere(docx_path, vocab):
    import docx  # noqa: PLC0415
    src = "Dictionnaire français-berbère (tableau de synonymes)"
    out = []
    for table in docx.Document(docx_path).tables:
        for r in table.rows:
            cells = [c.text.strip() for c in r.cells]
            if len(cells) < 2 or not cells[0]:
                continue
            fr = cells[0]
            for raw in dict.fromkeys(c for c in cells[1:] if c and c != "\xa0"):
                k = raw.replace("dj", "ǧ").replace("tc", "č") if not vocab.restore(raw)[1] else raw
                fixed, good = vocab.restore(k)
                if good and 1 <= len(fixed.split()) <= 3:
                    out.append(row(fixed, fr, "général", src))
                    break
    return out


def main(folder: str, data: str):
    f, d = Path(folder), Path(data)
    vocab = Vocab.load(d)
    jobs = {
        "lexicon_informatique.jsonl": lambda: informatique(f / "lexique_informatique.pdf"),
        "lexicon_electrotechnique.jsonl": lambda: electrotechnique(f / "electrotechnique.pdf"),
        "lexicon_linguistique.jsonl": lambda: tesnilest(f / "tesnilest.pdf"),
        "lexicon_osteologie.jsonl": lambda: kab_first(f / "ighsan.pdf",
                                                      "Iɣsan s teqbaylit, vocabulaire kabyle de l'ostéologie, 2010", "santé", vocab),
        "lexicon_maladies.jsonl": lambda: kab_first(f / "attanen.pdf",
                                                    "Amawal n waṭṭanen, vocabulaire kabyle des maladies, 2012", "santé", vocab),
        "lexicon_fr_berbere.jsonl": lambda: fr_berbere(f / "fr_berbere.docx", vocab),
    }
    for name, job in jobs.items():
        rows, seen = [], set()
        for r in job():
            # bibliographies, sigles, noms propres : pas des entrées de dictionnaire
            if re.search(r"\d|\bp\b|[«»\[\]]|\b(?:in|vol|éd|dir)\b\.?", r["fr"]) or r["kab"].isupper() \
                    or r["kab"].lower() in {"paris", "alger", "inalco"} or len(r["fr"]) > 80:
                continue
            key = (r["kab"].lower(), r["fr"].lower())
            if key not in seen:
                seen.add(key)
                rows.append(r)
        with (d / name).open("w", encoding="utf-8") as fh:
            for r in rows:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"{name:34s} {len(rows):6d} entrées")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "../data")
