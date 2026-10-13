"""Base de connaissances kabyle (RAG).

Charge les fichiers de data/ (lexique, glossaires, paires parallèles issues
des livres), construit un index de recherche plein texte (BM25, sans
dépendance externe) et renvoie, pour chaque message de l'élève, les mots et
phrases kabyles authentiques à fournir au prof.

Les décisions du linguiste (page /review) s'appliquent immédiatement :
une entrée rejetée n'est plus proposée, une entrée corrigée l'est sous sa
forme corrigée.
"""

import hashlib
import json
import math
import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

STOP = {
    # français
    "le", "la", "les", "de", "des", "du", "un", "une", "et", "ou", "en", "a", "au", "aux",
    "dans", "pour", "par", "sur", "que", "qui", "il", "elle", "je", "tu", "on", "nous", "vous",
    "ils", "ne", "pas", "se", "sa", "son", "ses", "est", "ce", "cette", "mon", "ma", "mes",
    "dit", "comment", "quoi", "kabyle", "dire", "dit-on", "veut",
    # anglais
    "the", "is", "of", "to", "and", "in", "how", "do", "you", "say", "what", "my", "me", "it",
    "kabyle", "word", "for",
    # kabyle (mots-outils très fréquents)
    "d", "n", "s", "i", "di", "deg", "ad", "ur", "ara", "yid", "akked", "ɣef", "gef", "am",
    "ma", "neɣ", "neg", "akken", "yiwen", "yiwet", "nni", "agi", "is", "as", "id",
}


def fold(s: str) -> str:
    """Minuscules, sans accents ni points souscrits : « Ṛemdan » → « remdan »."""
    s = s.replace("ɛ", "e").replace("Ɛ", "e").replace("ɣ", "g").replace("Ɣ", "g")
    s = unicodedata.normalize("NFD", s.lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def tokenize(s: str) -> list[str]:
    return [t for t in re.findall(r"\w+", fold(s)) if len(t) > 1 and t not in STOP]


def item_id(kind: str, kab: str, fr: str) -> str:
    return hashlib.sha1(f"{kind}|{kab}|{fr}".encode()).hexdigest()[:16]


@dataclass
class Item:
    id: str
    kind: str  # word | pair
    kab: str
    fr: str
    source: str
    confident: bool = True
    status: str = "pending"  # pending | ok | fixed | rejected
    tokens: list[str] = field(default_factory=list)


class KnowledgeBase:
    def __init__(self) -> None:
        self.items: dict[str, Item] = {}
        self._postings: dict[str, list[tuple[str, int]]] = defaultdict(list)
        self._len: dict[str, int] = {}
        self._avg = 1.0

    # ---------- chargement ----------
    def load(self, data_dir: str | Path) -> "KnowledgeBase":
        d = Path(data_dir)
        if not d.exists():
            return self
        for name in ("lexicon.jsonl", "glossaries.jsonl"):
            for row in _read_jsonl(d / name):
                self._add("word", row["kab"], row["fr"], row.get("source", ""), True)
        for path in sorted(d.glob("parallel_*.jsonl")):
            for row in _read_jsonl(path):
                self._add("pair", row["kab"], row["fr"], row.get("source", ""),
                          bool(row.get("confident", True)))
        self._build()
        return self

    def _add(self, kind, kab, fr, source, confident):
        kab, fr = kab.strip(), fr.strip()
        if not kab or not fr:
            return
        iid = item_id(kind, kab, fr)
        self.items[iid] = Item(iid, kind, kab, fr, source, confident)

    def _build(self):
        self._postings.clear()
        for it in self.items.values():
            it.tokens = tokenize(f"{it.kab} {it.fr}")
            self._len[it.id] = len(it.tokens) or 1
            for tok, n in Counter(it.tokens).items():
                self._postings[tok].append((it.id, n))
        self._avg = sum(self._len.values()) / max(len(self._len), 1)

    # ---------- relecture ----------
    def apply_review(self, iid: str, status: str, kab: str | None = None, fr: str | None = None):
        it = self.items.get(iid)
        if not it:
            return
        it.status = status
        if status == "fixed":
            it.kab = kab or it.kab
            it.fr = fr or it.fr

    # ---------- recherche (BM25) ----------
    def search(self, query: str, kind: str | None = None, k: int = 5) -> list[Item]:
        q = tokenize(query)
        if not q:
            return []
        n = len(self.items)
        scores: dict[str, float] = defaultdict(float)
        for tok in set(q):
            plist = self._postings.get(tok)
            if not plist:
                continue
            idf = math.log(1 + (n - len(plist) + 0.5) / (len(plist) + 0.5))
            for iid, tf in plist:
                dl = self._len[iid]
                scores[iid] += idf * tf * 2.2 / (tf + 1.2 * (0.25 + 0.75 * dl / self._avg))
        ranked = []
        for iid, sc in sorted(scores.items(), key=lambda x: -x[1]):
            it = self.items[iid]
            if it.status == "rejected" or (kind and it.kind != kind):
                continue
            if it.status == "pending" and not it.confident:
                continue  # paire douteuse non relue : on ne la montre pas au prof
            bonus = 1.3 if it.status in ("ok", "fixed") else 1.0
            ranked.append((sc * bonus, it))
        ranked.sort(key=lambda x: -x[0])
        return [it for _, it in ranked[:k]]

    def references_for(self, message: str) -> str:
        """Bloc de texte injecté dans le prompt du prof."""
        words = self.search(message, "word", 6)
        pairs = self.search(message, "pair", 4)
        if not words and not pairs:
            return ""
        lines = []
        if words:
            lines.append("Vocabulaire :")
            lines += [f"- {w.kab} — {w.fr}" for w in words]
        if pairs:
            lines.append("Phrases authentiques (tirées de livres traduits) :")
            lines += [f"- KAB : {p.kab}\n  FR : {p.fr}" for p in pairs]
        return "\n".join(lines)


def _read_jsonl(path: Path):
    if not path.exists():
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


kb = KnowledgeBase()
