"""Concordance kabyle ↔ français entre deux phrases, au niveau des LEMMES :
chaque mot kabyle est ramené à son lemme (lemmatize.py : conjugaison, état
d'annexion, pluriels, pronoms collés), chaque mot français à sa racine
(snowball). On compte les mots kabyles dont un sens connu se retrouve dans la
phrase française. Sert à aligner les livres traduits (build_parallel) et à
apprendre de nouvelles traductions (learn_lexicon).
"""
from __future__ import annotations

import re
import unicodedata
from functools import lru_cache

import snowballstemmer

_stem = snowballstemmer.stemmer("french")
STOPFR = set("""le la les l de des du d un une et en est sont était être a ai as avait ont avoir que qui quoi
pour par dans sur au aux ce cet cette ces c il elle ils elles on se s sa son ses ne n pas plus avec mais ou nous
vous je j tu me m te t lui leur leurs y qu mon ma mes ton ta tes notre nos votre vos dont où si tout tous toute
toutes même aussi comme bien très fait faire dit très là ça cela ceci celui celle ceux""".split())
WORD_FR = re.compile(r"[a-zàâäçéèêëîïôöùûüœæ]+", re.I)


@lru_cache(maxsize=100_000)
def _stem_word(w: str) -> str:
    return _stem.stemWord(w)


@lru_cache(maxsize=200_000)
def fr_stems(text: str) -> frozenset:
    words = [w.lower() for w in WORD_FR.findall(text.replace("’", "'"))]
    return frozenset(_stem_word(w) for w in words if w not in STOPFR and len(w) > 2)


@lru_cache(maxsize=200_000)
def _kab_set(kab: str) -> frozenset:
    return frozenset(kab_tokens(kab))


@lru_cache(maxsize=1)
def lemmatizer():
    from lemmatize import Lemmatizer
    return Lemmatizer.load()


@lru_cache(maxsize=200_000)
def _lemma_stems(token: str) -> frozenset:
    """Racines françaises des sens connus d'un mot kabyle (vide si inconnu ou mot-outil)."""
    out = set()
    for a in lemmatizer().analyze(token):
        if a["pos"] in ("outil", "nom propre"):
            continue
        for fr in lemmatizer().meanings.get(a["lemma"], ()):
            out |= fr_stems(re.sub(r"\(.*?\)", "", fr))
    return frozenset(out)


def kab_tokens(text: str) -> list[str]:
    from lemmatize import WORD, nfc
    return WORD.findall(nfc(text))


def similarity(fr: str, kab: str) -> int:
    frs = fr_stems(fr)
    names = {unicodedata.normalize("NFC", n.lower()) for n in re.findall(r"\b[A-ZÉ][a-zéèë]{3,}", fr)}
    hits = 0
    for t in _kab_set(kab):
        base = t.split("-")[0]
        if base in names:
            hits += 1
        elif _lemma_stems(t) & frs:
            hits += 1
    return hits
