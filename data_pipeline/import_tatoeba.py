"""Tatoeba kabyle-anglais (taqbaylit/tatoeba-en-kab, Hugging Face ; phrases Tatoeba,
CC0 / CC BY 2.0 FR) → fichiers de la base.

    python import_tatoeba.py ../data

- data/tatoeba_kab.jsonl : toutes les phrases kabyles uniques (+ anglais) — preuves
  d'usage pour les verbes (expand / discover / import), fréquence des mots.
- data/tatoeba_exemples.jsonl : une sélection de phrases d'exemple citables par le prof
  (3 à 14 mots, tous les mots kabyles reconnus par le lemmatiseur, sans doublon),
  avec leur traduction française (Tatoeba kabyle-français) ou, à défaut, anglaise.
"""
import json
import sys
from pathlib import Path

import pyarrow.parquet as pq

from fix_chars import fix
from lemmatize import WORD, Lemmatizer, nfc

SRC = "Tatoeba (tatoeba.org), corpus kabyle-anglais taqbaylit/tatoeba-en-kab"


def main(data_dir, cap=60000):
    data = Path(data_dir)
    ext = data / "externes"
    rows = pq.read_table(ext / "tatoeba_en_kab_train.parquet").to_pylist()
    rows += pq.read_table(ext / "tatoeba_en_kab_dev.parquet").to_pylist()
    seen, alls = set(), []
    for r in rows:
        kab, en = fix(r["translation"]["kab"]), r["translation"]["en"].strip()
        key = kab.lower().strip(" .!?")
        if key in seen or not kab:
            continue
        seen.add(key)
        alls.append({"kab": kab, "en": en})
    (data / "tatoeba_kab.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in alls),
                                            encoding="utf-8")
    lem = Lemmatizer.load(data, data.parent / "server" / "content")
    good, seen_ex = [], set()
    # d'abord les paires kabyle-FRANÇAIS (import_ressources_libres.py), puis l'anglais seul
    fr_rows = [json.loads(ln) for ln in open(data / "tatoeba_fr.jsonl", encoding="utf-8")] \
        if (data / "tatoeba_fr.jsonl").exists() else []
    for r in fr_rows + alls:
        k = r["kab"].lower().strip(" .!?")
        if k in seen_ex:
            continue
        seen_ex.add(k)
        toks = WORD.findall(nfc(r["kab"]))
        if 3 <= len(toks) <= 14 and all(lem.analyze(t) for t in toks):
            good.append({**r, "source": SRC, "kind": "exemple"})
    good.sort(key=lambda r: ("fr" not in r, len(r["kab"])))  # le français d'abord, puis les phrases courtes
    good = good[:cap]
    (data / "tatoeba_exemples.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in good),
                                                 encoding="utf-8")
    print(f"Tatoeba : {len(alls)} phrases uniques ; {len(good)} exemples citables")


if __name__ == "__main__":
    main(sys.argv[1])
