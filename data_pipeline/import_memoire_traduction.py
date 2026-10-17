"""Termes modernes tirés de la mémoire de traduction des logiciels libres
(taqbaylit/kabyle-english-TM : GNOME, KDE, LibreOffice…, CC BY 4.0).

    python import_memoire_traduction.py ../data   → data/termes_modernes_en.jsonl

On ne garde que des termes courts (1 à 3 mots de chaque côté), sans variables
(%s, {0}, &), sans français resté dans la colonne kabyle, et le terme kabyle le
plus fréquent pour chaque terme anglais (les traducteurs varient). Sens en
anglais seulement : vocabulaire de l'informatique et de la vie moderne.
"""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pyarrow.parquet as pq

from fix_chars import fix

FR = re.compile(r"[éèêàâçùûôîœ]|\b(les|des|une|avec|pour|dans|fichier|paramètres)\b", re.I)
BAD = re.compile(r"[%{}<>&_\\/=|#@0-9]|\.\.\.")


def main(data_dir):
    data = Path(data_dir)
    rows = pq.read_table(data / "externes" / "memoire_traduction_en_kab.parquet").to_pylist()
    by_en = defaultdict(Counter)
    for r in rows:
        en, kab = r["source"].strip(), re.sub(r"\s*\([^)]*\)", "", fix(r["target"])).strip()
        # noms de marques / produits (Firefox, VK, Discourse…) : mot à majuscule repris tel quel en kabyle
        en_caps = {w for w in re.findall(r"\b[A-Z][\w]+", en) if not en.startswith(w)}
        if any(w in kab for w in en_caps) or re.search(r"\b[A-Z]{2,}\b", kab):
            continue
        if BAD.search(en) or BAD.search(kab) or FR.search(kab):
            continue
        if not (1 <= len(en.split()) <= 3 and 1 <= len(kab.split()) <= 3):
            continue
        if not re.search(r"[a-zɛɣḍṭẓṛṣḥčǧ]", kab.lower()) or kab.lower() == en.lower():
            continue
        by_en[en.lower().strip(" .:")][kab.strip(" .:")] += 1
    out = []
    for en, c in by_en.items():
        kab, n = c.most_common(1)[0]
        if n < 2 and sum(c.values()) > 2:  # pas de consensus entre traducteurs
            continue
        out.append({"kab": kab, "en": en, "count": n, "variants": [k for k, _ in c.most_common(4)[1:]],
                    "source": "Traductions de logiciels libres (taqbaylit/kabyle-english-TM), CC BY 4.0",
                    "needs_review": True})
    out.sort(key=lambda r: -r["count"])
    (data / "termes_modernes_en.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in out),
                                                    encoding="utf-8")
    print(f"termes modernes : {len(out)}")


if __name__ == "__main__":
    main(sys.argv[1])
