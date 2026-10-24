"""Vocabulaire kabyle attesté (formes écrites par des humains) et restauration des
lettres kabyles abîmées par la reconnaissance de texte (OCR) : ɛ lu « e », « € » ou « t »,
ɣ lu « y », « $ » ou « 4 », points souscrits perdus (ḍ → d, ṭ → t…).

  from kab_vocab import Vocab
  v = Vocab.load(Path("../data"))
  v.restore("xedmey")  →  ("xedmeɣ", True)
"""
import gzip
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

WORD = re.compile(r"[^\W\d_]+(?:-[^\W\d_]+)*")


def fold(s: str) -> str:
    s = s.lower().replace("ɛ", "e").replace("ε", "e").replace("ɣ", "g").replace("γ", "g")
    s = unicodedata.normalize("NFD", s)
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def loose(s: str) -> str:
    """Clé très tolérante aux erreurs d'OCR : e/ɛ/€, g/ɣ/y/$/4, c/ç, lettres doublées gardées."""
    s = s.lower()
    s = s.translate(str.maketrans({"€": "e", "$": "g", "4": "g", "ç": "c", "ğ": "j", "ţ": "t", "ʷ": "", "°": "",
                                   '"': "", "*": "", "’": "", "'": ""}))
    s = fold(s).replace("y", "g")
    return re.sub(r"[^a-z\-]", "", s)


class Vocab:
    def __init__(self, counts: Counter):
        self.counts = counts
        best: dict[str, tuple[int, str]] = {}
        for w, n in counts.items():
            k = loose(w)
            if n > best.get(k, (0, ""))[0]:
                best[k] = (n, w)
        self.by_loose = {k: w for k, (n, w) in best.items()}

    @classmethod
    def load(cls, data: Path) -> "Vocab":
        c: Counter = Counter()

        def add_text(t: str, weight: int = 1):
            for w in WORD.findall((t or "").lower()):
                c[w] += weight

        wf = data / "word_freq.tsv"
        if wf.exists():
            for line in wf.read_text(encoding="utf-8").splitlines():
                w, _, n = line.partition("\t")
                if n.isdigit():
                    c[w.lower()] += int(n)
        for name in ("tatoeba_kab_tout.jsonl.gz", "tatoeba_fr.jsonl", "bouamara_niveaux.jsonl",
                     "parallel_petit_prince.jsonl", "parallel_feraoun.jsonl", "parallel_camus.jsonl"):
            p = data / name
            if not p.exists():
                continue
            op = gzip.open if p.suffix == ".gz" else open
            with op(p, "rt", encoding="utf-8") as f:
                for line in f:
                    try:
                        add_text(json.loads(line).get("kab", ""))
                    except ValueError:
                        pass
        for p in sorted(data.glob("lexicon*.jsonl")) + [data / "hunspell_kab.jsonl", data / "glossaries.jsonl"]:
            if not p.exists():
                continue
            with open(p, encoding="utf-8") as f:
                for line in f:
                    try:
                        add_text(json.loads(line).get("kab", ""), 3)
                    except ValueError:
                        pass
        return cls(c)

    def restore(self, ocr_word: str) -> tuple[str, bool]:
        """(forme corrigée, trouvée dans le kabyle attesté ?)"""
        w = ocr_word.strip(".,;:!?()[]«»\"' ").lower()
        if not w:
            return w, False
        if self.counts.get(w, 0) >= 2:
            return w, True
        for cand in (w, w[1:] if w.startswith("e") and len(w) > 3 else None):  # Dallet : « efren » = fren
            if not cand:
                continue
            hit = self.by_loose.get(loose(cand))
            if hit and self.counts[hit] >= 2:
                return hit, True
        return w.replace("€", "ɛ").replace("$", "ɣ"), False
