"""Ressources libres ajoutées en octobre 2026 (data/externes) → fichiers de la base.

    python import_ressources_libres.py ../data

1. Tatoeba kabyle ↔ FRANÇAIS (CC0 / CC BY 2.0 FR) : tatoeba_fr_kab_tifinagh.tsv (206 000)
   + tatoeba_kab_fr_2023.tsv (110 000, presque tout inclus), joints à l'anglais par
   identifiant (tatoeba_en_kab_tifinagh.tsv) → data/tatoeba_fr.jsonl {kab, fr, en?}.
   Sert à apprendre des sens FRANÇAIS (learn_lexicon) et donne des exemples traduits.
2. Toutes les phrases kabyles de Tatoeba (765 000, tatoeba_kab_tifinagh.tsv) →
   data/tatoeba_kab_tout.jsonl : preuves d'usage seulement (verbes attestés).
3. Contes kabyles « timucuha » (association Numidya, CC BY-NC 4.0 ; anglais traduit
   par machine) → data/contes_numidya.jsonl {kab, fr, en}.
4. Toponymes OpenStreetMap (© contributeurs OpenStreetMap, ODbL) : noms de lieux dont
   le nom kabyle diffère du nom français → data/toponymes.jsonl.
5. Entités nommées kabyle-anglais (institutions, lieux…) → data/entites_nommees_en.jsonl.
6. Wikipédia en kabyle (CC BY-SA 4.0 ; WIKAB v1 + extraits du dump) : articles découpés
   en passages de quelques phrases → data/wiki_kab.jsonl (exemples d'emploi, culture,
   histoire ; preuves d'usage).
7. Corpus kabyle-corpus (data.csv, MIT, origine inconnue, bruité) : seulement les phrases
   dont TOUS les mots sont reconnus par le lemmatiseur → data/attestation_kab.jsonl
   (fréquences et preuves d'usage, jamais cité à l'élève).

8. Phrases kabyles de Common Voice (Mozilla, CC0 ; dépôt common-voice/server/data/kab)
   → data/commonvoice_kab.jsonl : preuves d'usage.

Exclus volontairement : traductions du Coran et de la Bible (sensibles ; droits des
traductions), paires « minées » NLLB (trop bruitées).
"""
from __future__ import annotations

import csv
import gzip
import json
import re
import sys
import unicodedata
import zipfile
from pathlib import Path

import pyarrow.parquet as pq

from fix_chars import fix
from lemmatize import WORD, Lemmatizer, nfc

csv.field_size_limit(10 ** 9)
TATO = "Tatoeba (tatoeba.org), CC BY 2.0 FR"
CONTES = "Contes kabyles timucuha, association Numidya (CC BY-NC 4.0)"
OSM = "Toponymes OpenStreetMap (© contributeurs OpenStreetMap, ODbL)"
WIKI = "Wikipédia en kabyle (CC BY-SA 4.0)"


def write(path: Path, rows):
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def key(s):
    return re.sub(r"\s+", " ", s.lower()).strip(" .!?…")


def clean(s):
    return unicodedata.normalize("NFC", fix(s.replace("\ufeff", ""))).strip()


def tatoeba(ext: Path, data: Path):
    en = {}
    for row in csv.reader(open(ext / "tatoeba_en_kab_tifinagh.tsv", encoding="utf-8-sig"), delimiter="\t"):
        if len(row) >= 4 and row[0] != "id":
            en[row[0].strip("﻿")] = row[3].strip()
    out, seen = [], set()
    for name, ik, ifr, iid in (("tatoeba_fr_kab_tifinagh.tsv", 2, 3, 0), ("tatoeba_kab_fr_2023.tsv", 1, 3, 0)):
        for row in csv.reader(open(ext / name, encoding="utf-8-sig"), delimiter="\t"):
            if len(row) <= max(ik, ifr) or row[0] == "id":
                continue
            kab, fr = clean(row[ik]), row[ifr].strip()
            k = (key(kab), key(fr))
            if not kab or not fr or k in seen:
                continue
            seen.add(k)
            r = {"kab": kab, "fr": fr}
            e = en.get(row[iid].strip("﻿"))
            if e:
                r["en"] = e
            out.append(r)
    write(data / "tatoeba_fr.jsonl", out)
    alls, seen = [], set()
    for row in csv.reader(open(ext / "tatoeba_kab_tifinagh.tsv", encoding="utf-8-sig"), delimiter="\t"):
        if len(row) >= 3 and row[0] != "id":
            kab = clean(row[2])
            if kab and key(kab) not in seen:
                seen.add(key(kab))
                alls.append({"kab": kab})
    write(data / "tatoeba_kab_tout.jsonl", alls)
    print(f"Tatoeba français : {len(out)} paires kabyle-français ({sum('en' in r for r in out)} avec l'anglais) ; "
          f"{len(alls)} phrases kabyles uniques en tout")


def contes(ext: Path, data: Path):
    out, seen = [], set()
    for name in ("contes_numidya_train.jsonl", "contes_numidya_val.jsonl"):
        for ln in open(ext / name, encoding="utf-8"):
            r = json.loads(ln)
            kab = clean(r.get("kabyle", "")).lstrip("-– ").strip()
            fr = (r.get("french") or "").lstrip("-– ").strip()
            if kab and fr and key(kab) not in seen:
                seen.add(key(kab))
                out.append({"kab": kab, "fr": fr, "en": (r.get("english") or "").lstrip("-– ").strip(),
                            "source": CONTES, "needs_review": True})
    write(data / "contes_numidya.jsonl", out)
    print(f"Contes Numidya : {len(out)} phrases kabyle-français")


def toponymes(ext: Path, data: Path):
    out, seen = [], set()
    for r in pq.read_table(ext / "toponymes_osm.parquet").to_pylist():
        kab, fr = clean(r.get("kabyle") or ""), (r.get("french") or "").strip()
        cat = (r.get("category") or "").split(":")[0]
        if cat not in ("village", "admin", "town", "hamlet", "natural", "city", "waterway", "tourism"):
            continue  # rues, commerces, équipements : pas du vocabulaire
        if not kab or not fr or key(kab) == key(fr) or (kab, fr) in seen:
            continue
        seen.add((kab, fr))
        out.append({"kab": kab, "fr": f"{fr} (nom de lieu)", "kind": "entry", "domain": "lieux",
                    "category": "nom propre", "place": r.get("category"), "source": OSM, "needs_review": True})
    write(data / "toponymes.jsonl", out)
    print(f"Toponymes : {len(out)} noms de lieux kabyles ≠ français")


def entites(ext: Path, data: Path):
    out = []
    for row in csv.DictReader(open(ext / "kabyle_named_entities.tsv", encoding="utf-8-sig"), delimiter="\t"):
        kab, en = clean(row.get("kabyle_standardized", "")), (row.get("english_translation") or "").strip()
        if kab and en:
            out.append({"kab": kab, "en": en, "category": row.get("entity_category", ""),
                        "source": "Entités nommées kabyle-anglais (kabyle_named_entities)", "needs_review": True})
    write(data / "entites_nommees_en.jsonl", out)
    print(f"Entités nommées : {len(out)}")


SKIP_TITLE = re.compile(r"^(MediaWiki|Wikipedia|Asebter agejdan|Taggayt|Talɣa|Amedya|Template|Module|Ticket)", re.I)


def wiki_articles(ext: Path):
    """(titre, texte) depuis WIKAB v1 (un fichier par article) et les extraits du dump."""
    arts = {}
    z = zipfile.ZipFile(ext / "wikab_v1.zip")
    for n in z.namelist():
        if not n.endswith(".txt"):
            continue
        title = re.sub(r"#U([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), Path(n).stem).replace("_", " ")
        arts.setdefault(title, z.read(n).decode("utf-8", "replace"))
    for p in sorted((ext / "kabwiki").glob("*.txt.gz")):
        blocks = gzip.open(p, "rt", encoding="utf-8", errors="replace").read().split("\n\n")
        for b in blocks:
            lines = b.strip().split("\n", 1)
            if len(lines) == 2:
                arts.setdefault(lines[0].strip(), lines[1])
    return arts


def wiki(ext: Path, data: Path, lem):
    out = []
    n_art = 0
    for title, text in wiki_articles(ext).items():
        if SKIP_TITLE.match(title) or len(text) < 120:
            continue
        text = re.sub(r"\{\|.*?\|\}", " ", text, flags=re.S)
        text = re.sub(r"==+[^=]+==+|\[\[|\]\]|'''?|<[^>]+>|\{\{.*?\}\}", " ", text)
        text = re.sub(r"Taggayt:.*", " ", text)
        sents = re.split(r"(?<=[.!?])\s+(?=[A-ZƐƔḌṬẒṚṢḤČǦ])", re.sub(r"\s+", " ", text))
        chunk, used = [], 0
        for s in sents:
            s = clean(s)
            toks = WORD.findall(s)
            if len(toks) < 4 or len(s) > 600:
                continue
            # passage gardé seulement s'il est bien en kabyle (≥ 70 % de mots reconnus)
            if sum(1 for t in toks if lem.analyze(t)) < 0.7 * len(toks):
                continue
            chunk.append(s)
            if sum(map(len, chunk)) > 280:
                out.append({"kab": " ".join(chunk), "title": title, "source": f"{WIKI}, article « {title} »"})
                chunk, used = [], used + 1
        if chunk:
            out.append({"kab": " ".join(chunk), "title": title, "source": f"{WIKI}, article « {title} »"})
            used += 1
        n_art += bool(used)
    write(data / "wiki_kab.jsonl", out)
    print(f"Wikipédia : {n_art} articles, {len(out)} passages en kabyle")


def attestation(ext: Path, data: Path, lem):
    out, seen = [], set()
    with open(ext / "corpus_kabyle_data.csv", encoding="utf-8", errors="replace") as f:
        next(f)
        for ln in f:
            s = clean(ln.strip().strip('"'))
            toks = WORD.findall(s)
            if len(toks) < 3 or key(s) in seen:
                continue
            if all(lem.analyze(t) for t in toks):
                seen.add(key(s))
                out.append({"kab": s})
    write(data / "attestation_kab.jsonl", out)
    print(f"kabyle-corpus : {len(out)} phrases entièrement reconnues gardées comme preuves d'usage")


def commonvoice(ext: Path, data: Path):
    out, seen = [], set()
    for p in sorted((ext / "commonvoice_kab").glob("*.txt")):
        for ln in open(p, encoding="utf-8", errors="replace"):
            s = clean(ln)
            if len(WORD.findall(s)) >= 2 and key(s) not in seen:
                seen.add(key(s))
                out.append({"kab": s})
    write(data / "commonvoice_kab.jsonl", out)
    print(f"Common Voice : {len(out)} phrases kabyles (CC0)")


def main(data_dir):
    data = Path(data_dir)
    ext = data / "externes"
    tatoeba(ext, data)
    contes(ext, data)
    toponymes(ext, data)
    entites(ext, data)
    commonvoice(ext, data)
    lem = Lemmatizer.load(data, data.parent / "server" / "content")
    wiki(ext, data, lem)
    attestation(ext, data, lem)


if __name__ == "__main__":
    main(sys.argv[1])
