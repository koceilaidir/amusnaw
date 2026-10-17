"""Corrige les restes d'anciennes polices dans les fichiers de données (champ kab).

    python fix_chars.py ../data

Remplacements sûrs : $ → ɣ, £ → Ɣ, ɤ → ɣ, є → ɛ, Ґ/Г → Ɣ, Σ → Ɛ, << >> → « »,
caractères de contrôle et zone privée supprimés. Le signe „ (tantôt u, tantôt y
selon le livre) est ambigu : la phrase est retirée plutôt que devinée.
"""
import json
import re
import sys
import unicodedata
from pathlib import Path

MAP = str.maketrans({"$": "ɣ", "£": "Ɣ", "ɤ": "ɣ", "є": "ɛ", "Ґ": "Ɣ", "Г": "Ɣ", "Σ": "Ɛ", "ε": "ɛ", "γ": "ɣ",
                     "ğ": "ǧ", "Ğ": "Ǧ", "\x08": "", "": "", "": ""})
FILES = ["corpus_hca.jsonl", "corpus_poesie.jsonl", "parallel_camus.jsonl", "parallel_feraoun.jsonl",
         "parallel_petit_prince.jsonl", "sentences.jsonl"]


def fix(s: str) -> str:
    s = s.replace("<<", "«").replace(">>", "»").translate(MAP)
    s = re.sub(r"[\x00-\x08\x0b-\x1f-]", "", s)
    return unicodedata.normalize("NFC", re.sub(r"\s+", " ", s)).strip()


def main(data):
    for name in FILES:
        p = Path(data) / name
        if not p.exists():
            continue
        rows, changed, dropped = [], 0, 0
        for line in open(p, encoding="utf-8"):
            r = json.loads(line)
            if "„" in r["kab"]:
                dropped += 1
                continue
            new = fix(r["kab"])
            changed += new != r["kab"]
            r["kab"] = new
            rows.append(r)
        p.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
        print(f"{name:30} corrigées {changed:5}  retirées {dropped}")


if __name__ == "__main__":
    main(sys.argv[1])
