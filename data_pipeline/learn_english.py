"""Apprend le sens ANGLAIS des lemmes kabyles sur Tatoeba (242 000 paires
kabyle ↔ anglais, CC0 / CC BY 2.0 FR), avec la même méthode que learn_lexicon.py
(lemmes kabyles ↔ racines anglaises, liaison compétitive, plusieurs tours).

    python learn_english.py ../data            → data/sens_anglais_appris.jsonl
    python learn_english.py ../data --eval     → précision sur la référence de Bouamara
                                                 (mots du niveau 0, jamais utilisés pour apprendre)
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

import pyarrow.parquet as pq
import snowballstemmer

from learn_lexicon import join_prefixes, unknown_key
from lemmatize import WORD, Lemmatizer, nfc

_st = snowballstemmer.stemmer("english")
STOP_EN = set("""the a an and or of to in on at for with by from is are was were be been being am i you he she it we they
me him her us them my your his its our their this that these those there here not no do does did done have has had
will would shall should can could may might must just so as but if then than too very what who whom which when where
why how all any some one ones up down out off over into about again also only own same such more most other s t
don doesn didn isn aren wasn weren won let lets get got go going im ive youre hes shes thats theres""".split())
WORD_EN = re.compile(r"[a-z]+")


def en_words(text):
    return [w for w in WORD_EN.findall(text.lower().replace("'", " ")) if w not in STOP_EN and len(w) > 1]


def load(data: Path):
    ext = data / "externes"
    rows = pq.read_table(ext / "tatoeba_en_kab_train.parquet").to_pylist()
    rows += pq.read_table(ext / "tatoeba_en_kab_dev.parquet").to_pylist()
    return [(r["translation"]["kab"], r["translation"]["en"]) for r in rows]


def learn(pairs, lem, freq, rounds=4, min_pairs=3, min_dice=0.3):
    learned = {}
    entries = {}
    surface = defaultdict(Counter)
    # Pré-calcul : unités kabyles et racines anglaises de chaque paire
    pre = []
    for kab, en in pairs:
        toks = join_prefixes(WORD.findall(nfc(kab)), lem)
        units = set()
        for t in toks:
            an = lem.analyze(t)
            if an and an[0]["pos"] in ("outil", "nom propre"):
                continue
            lemmas = sorted({a["lemma"] for a in an})
            key = lemmas[0] if lemmas else unknown_key(t, freq)
            if len(key) >= 2:
                units.add(key)
        stems = set()
        for w in en_words(en):
            s = _st.stemWord(w)
            stems.add(s)
            surface[s][w] += 1
        if units and stems:
            pre.append((units, stems))
    for r in range(1, rounds + 1):
        cK, cF, cKF = Counter(), Counter(), Counter()
        for units, stems in pre:
            expl = {learned[u] for u in units if u in learned}
            unk = [u for u in units if u not in learned]
            st = stems - expl
            if not unk or not st:
                continue
            cK.update(unk)
            cF.update(st)
            for u in unk:
                for s in st:
                    cKF[u, s] += 1
        best_f = {}
        for (u, s), n in cKF.items():
            d = 2 * n / (cK[u] + cF[s])
            if d > best_f.get(s, (0, None))[0]:
                best_f[s] = (d, u)
        new = {}
        for (u, s), n in cKF.items():
            if n < min_pairs:
                continue
            d = 2 * n / (cK[u] + cF[s])
            if d < (max(min_dice, 0.6) if len(u) <= 3 else min_dice):
                continue
            if best_f[s][1] != u and best_f[s][0] > d * 1.2:
                continue
            if u not in new or d > new[u][1]:
                new[u] = (s, d, n)
        added = 0
        for u, (s, d, n) in new.items():
            if u in entries:
                continue
            word = surface[s].most_common(1)[0][0]
            entries[u] = {"kab": u, "en": word, "stem": s, "pairs": n, "dice": round(d, 2), "round": r}
            learned[u] = s
            added += 1
        print(f"  tour {r}: +{added} (total {len(entries)})")
        if not added:
            break
    return entries


def gold_bouamara(data: Path):
    gold = {}
    for ln in open(data / "bouamara_niveaux.jsonl", encoding="utf-8"):
        r = json.loads(ln)
        if r.get("level") == 0 and " " not in r["kab"].strip():
            gold[nfc(r["kab"]).lower()] = {_st.stemWord(w) for w in en_words(r["en"])}
    return gold


def main(data_dir, evaluate=False):
    data = Path(data_dir)
    lem = Lemmatizer.load(data, data.parent / "server" / "content", learned=False)
    freq = {}
    for line in open(data / "word_freq.tsv", encoding="utf-8"):
        w, n = line.rstrip("\n").split("\t")
        freq[w] = int(n)
    pairs = load(data)
    print(f"{len(pairs)} paires kabyle-anglais")
    entries = learn(pairs, lem, freq)
    if evaluate:
        gold = gold_bouamara(data)
        found = {k: v for k, v in entries.items() if k in gold}
        ok = [k for k, v in found.items() if v["stem"] in gold[k]]
        print(f"référence Bouamara : {len(gold)} mots, {len(found)} appris, précision {100 * len(ok) / max(len(found), 1):.0f} %")
        for k, v in list(found.items())[:40]:
            print(f"   {k:12} → {v['en']:12} {'OK' if k in ok else '≠'}  ({len(gold[k]) and ', '.join(sorted(gold[k]))})")
        return
    rows = sorted(entries.values(), key=lambda r: -r["pairs"])
    for r in rows:
        r.update({"source": "Appris par Amusnaw sur Tatoeba (kabyle-anglais), à valider", "needs_review": True})
    (data / "sens_anglais_appris.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    print(f"{len(rows)} sens anglais appris → sens_anglais_appris.jsonl")


if __name__ == "__main__":
    main(sys.argv[1], "--eval" in sys.argv)
