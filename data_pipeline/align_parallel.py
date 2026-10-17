"""Alignement phrase à phrase d'un texte français et de sa traduction kabyle.

Méthode : Gale & Church (1993) — on apparie les phrases selon leur longueur
(une phrase longue se traduit par une phrase longue), avec un bonus quand
les deux côtés contiennent les mêmes noms propres ou nombres, et des points
d'ancrage forcés aux débuts de chapitre.

Chaque paire reçoit un score de confiance ; seules les paires sûres sont
gardées pour l'entraînement, après relecture humaine.

Usage :
  python align_parallel.py fr.pdf ../data/feraoun_kab.txt ../data/parallel_feraoun.jsonl
"""

import json
import math

from lexsim import similarity
import re
import sys
import unicodedata

import pymupdf

# Correspondances de noms propres français → kabyle (sans signes diacritiques)
NAMES = {
    "fouroulou": "furulu", "ramdane": "remdan", "lounis": "lewnis", "dadar": "dadar",
    "helima": "hlima", "baya": "baya", "titi": "titi", "fatma": "fatma",
    "alger": "lezzayer", "france": "fransa", "tizi": "tizi", "nana": "nanna",
    "khalti": "xalti", "kamouma": "kamuma", "menrad": "menrad", "azouaou": "azwaw",
    "hocine": "hsen", "akli": "akli", "omar": "ɛmar", "mohand": "muhend",
}


def fold(s: str) -> str:
    s = unicodedata.normalize("NFD", s.lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.replace("ḍ", "d").replace("ṛ", "r").replace("ḥ", "h").replace("ṭ", "t")


def split_sentences(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s+-\s+(?=[A-ZÀ-ÖØ-ÞƐƔḌḤṚṢṬẒČǦa-zɣɛ])", "\n- ", text)  # répliques
    out = []
    for chunk in text.split("\n"):
        parts = re.split(r"(?<=[.!?…»])\s+(?=[-«\"“A-ZÀ-ÖØ-ÞƐƔḌḤṚṢṬẒČǦ])", chunk)
        out += [p.strip() for p in parts if len(p.strip()) > 1]
    return out


def french_chapters(pdf: str) -> list[list[str]]:
    doc = pymupdf.open(pdf)
    text = "\n".join(p.get_text() for p in doc)
    text = text.split("Chapitre 1", 1)[1]
    chunks = re.split(r"\n\s*Chapitre \d+\s*\n", text)
    return [split_sentences(c) for c in chunks]


def kabyle_chapters(path: str, part: int = 2, first_n: int = 3) -> list[list[str]]:
    """Renvoie les chapitres 1..first_n puis le reste de la partie en un bloc
    (le PDF français n'a de titres que pour les premiers chapitres)."""
    raw = open(path, encoding="utf-8").read()
    raw = raw.split(f"### IXF {part}", 1)[1]
    raw = raw.split("Amawal :", 1)[0]
    raw = raw.split("## 1", 1)[1]
    chapters = re.split(r"\n## \d+\n", raw)
    head, tail = chapters[:first_n], chapters[first_n:]
    return [split_sentences(c) for c in head] + [split_sentences("\n".join(tail))]


def anchors(s: str) -> set[str]:
    """Indices indépendants de la langue : noms propres, nombres et
    ponctuation (question, exclamation, réplique, citation)."""
    f = fold(s)
    found = {n for n in re.findall(r"\b\d+\b", f)}
    for fr, kab in NAMES.items():
        if fr in f or kab in f:
            found.add(fr)
    st = s.strip()
    if "?" in st:
        found.add("<?>")
    if "!" in st:
        found.add("<!>")
    if st[:1] in "-–—":
        found.add("<dash>")
    if any(q in st for q in "«“\""):
        found.add("<quote>")
    return found


def norm_cdf(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


BEADS = {(1, 1): 0.89, (1, 0): 0.005, (0, 1): 0.005, (2, 1): 0.045, (1, 2): 0.045, (2, 2): 0.011}


def align(fr: list[str], kab: list[str]):
    lf = sum(map(len, fr)) or 1
    lk = sum(map(len, kab)) or 1
    c, s2 = lk / lf, 6.8
    n, m = len(fr), len(kab)
    INF = float("inf")
    cost = [[INF] * (m + 1) for _ in range(n + 1)]
    back = [[None] * (m + 1) for _ in range(n + 1)]
    cost[0][0] = 0.0
    band = max(40, abs(n - m) + 30)
    an_fr = [anchors(s) for s in fr]
    an_kb = [anchors(s) for s in kab]
    for i in range(n + 1):
        jc = round(i * m / max(n, 1))
        for j in range(max(0, jc - band), min(m, jc + band) + 1):
            if cost[i][j] == INF:
                continue
            for (di, dj), p in BEADS.items():
                ii, jj = i + di, j + dj
                if ii > n or jj > m:
                    continue
                l1 = sum(len(x) for x in fr[i:ii])
                l2 = sum(len(x) for x in kab[j:jj])
                if di and dj:
                    delta = (l2 - l1 * c) / math.sqrt(max(l1, 1) * s2)
                    pd = max(2 * (1 - norm_cdf(abs(delta))), 1e-12)
                    d = -math.log(pd) - math.log(p)
                    a1 = set().union(*an_fr[i:ii])
                    a2 = set().union(*an_kb[j:jj])
                    d -= 1.5 * len(a1 & a2)
                    # mots du dictionnaire présents des deux côtés (base enrichie)
                    d -= 1.2 * min(similarity(' '.join(fr[i:ii]), ' '.join(kab[j:jj])), 6)
                    d += 1.0 * len(a1 ^ a2)
                else:
                    d = -math.log(p) + 0.01 * (l1 + l2)
                if cost[i][j] + d < cost[ii][jj]:
                    cost[ii][jj] = cost[i][j] + d
                    back[ii][jj] = (i, j, d)
    pairs, i, j = [], n, m
    while i > 0 or j > 0:
        pi, pj, d = back[i][j]
        pairs.append((" ".join(fr[pi:i]), " ".join(kab[pj:j]), d, (i - pi, j - pj)))
        i, j = pi, pj
    return list(reversed(pairs))


def main(fr_pdf: str, kab_txt: str, out: str) -> None:
    fr_ch = french_chapters(fr_pdf)
    kb_ch = kabyle_chapters(kab_txt, first_n=len(fr_ch) - 1)
    assert len(fr_ch) == len(kb_ch), (len(fr_ch), len(kb_ch))
    rows, kept = [], 0
    for ch, (f, k) in enumerate(zip(fr_ch, kb_ch), start=1):
        for fr_s, kb_s, d, bead in align(f, k):
            if not fr_s or not kb_s:
                continue
            ratio = len(kb_s) / max(len(fr_s), 1)
            confident = bead == (1, 1) and d < 3.0 and 0.6 < ratio < 1.8
            kept += confident
            rows.append({"fr": fr_s, "kab": kb_s, "chapter_block": ch, "bead": list(bead),
                         "cost": round(d, 2), "confident": confident,
                         "source": "Feraoun, Le fils du pauvre / trad. M. Ould Taleb, Mmis n igellil (HCA 2004)",
                         "needs_review": True})
    with open(out, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"{len(rows)} paires, dont {kept} sûres (1-1, bon score)")


if __name__ == "__main__":
    main(*sys.argv[1:4])
