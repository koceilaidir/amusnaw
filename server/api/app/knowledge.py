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


# Mots-outils kabyles et mots communs au français qui ne doivent pas compter
# comme « mots appris » (normalisés).
KAB_FUNCTION_WORDS = {
    "deg", "seg", "gef", "gur", "akked", "yid", "acu", "anwa", "ayen", "ara", "maca", "acku",
    "imi", "ula", "ala", "kan", "aya", "agi", "nni", "ihi", "dga", "daga", "dayen", "tura",
    "yella", "llan", "yiwen", "yiwet", "nek", "nekk", "kecc", "kemm", "netta", "nettat",
    "nekni", "kunwi", "nutni", "inu", "iw", "ines", "nnes", "nneg", "nsen", "nwen", "mass",
    "les", "des", "pour", "que", "qui", "une", "est", "pas", "par", "sur", "avec", "dans",
}


# Priorité des sources : le programme d'abord, les lexiques spécialisés ensuite.
DOMAIN_WEIGHT = {"programme": 2.0, "droit": 0.6, "prénoms": 0.25, "langue et didactique": 0.8}


def fold(s: str) -> str:
    """Minuscules, sans accents ni points souscrits : « Ṛemdan » → « remdan ».
    Tolère les saisies au clavier ordinaire : « aghrum » = « aɣrum », « ε » = « ɛ »."""
    s = s.lower()
    s = s.replace("ɛ", "e").replace("ε", "e").replace("ɣ", "g").replace("γ", "g").replace("gh", "g")
    s = unicodedata.normalize("NFD", s)
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
    domain: str = ""
    tokens: list[str] = field(default_factory=list)


class KnowledgeBase:
    def __init__(self) -> None:
        self.items: dict[str, Item] = {}
        # Vocabulaire kabyle attesté dans les livres : forme normalisée → forme écrite
        self.kab_vocab: dict[str, str] = {}
        self._postings: dict[str, list[tuple[str, int]]] = defaultdict(list)
        self._len: dict[str, int] = {}
        self._avg = 1.0

    # ---------- chargement ----------
    def load(self, data_dir: str | Path, content_dir: str | Path | None = None) -> "KnowledgeBase":
        d = Path(data_dir)
        content = Path(content_dir) if content_dir else d.parent / "content"
        if not d.exists():
            return self
        lexicons = [d / "lexicon.jsonl", d / "glossaries.jsonl", *sorted(d.glob("lexicon_*.jsonl"))]
        for path in lexicons:
            for row in _read_jsonl(path):
                # Les longues phrases du lexique juridique (« Corrompre les
                # fonctionnaires du ministère de… ») n'apportent pas de vocabulaire.
                if row.get("kind") == "phrase" or row.get("no_meaning"):
                    continue
                self._add("word", row["kab"], row["fr"], row.get("source", ""), True,
                          row.get("domain", ""))
        # Programme A1 d'Amusnaw : mots et blocs de chaque unité (prioritaires).
        for path in sorted(content.glob("curriculum_*.json")):
            try:
                cur = json.loads(path.read_text("utf-8"))
            except (OSError, ValueError):
                continue
            for unit in cur.get("units", []):
                src = f"Programme Amusnaw {cur.get('level', '')} — {unit.get('title', '')}"
                for w in unit.get("words", []) + unit.get("chunks", []):
                    self._add("word", w["kab"], w["fr"], src, True, "programme")
        # Textes kabyles authentiques (romans, contes, essais HCA), sans traduction :
        # exemples d'emploi réel des mots.
        for row in _read_jsonl(d / "corpus_hca.jsonl"):
            self._add("text", row["kab"], "", f"{row.get('source', '')}, p. {row.get('page', '?')}", True)
        # Chansons sous licence : un vers par ligne (voir data/songs/README.md)
        for row in _read_jsonl(d / "songs" / "songs.jsonl"):
            fr = row.get("fr", "")
            if row.get("hidden_meaning"):
                fr += f" — Sens caché : {row['hidden_meaning']}"
            self._add("song", row["kab"], fr,
                      f"{row.get('artist', '')} — {row.get('title', '')}", True)
        for path in sorted(d.glob("parallel_*.jsonl")):
            for row in _read_jsonl(path):
                self._add("pair", row["kab"], row["fr"], row.get("source", ""),
                          bool(row.get("confident", True)))
        self._build()
        return self

    def _add(self, kind, kab, fr, source, confident, domain=""):
        kab, fr = kab.strip(), fr.strip()
        if not kab or (not fr and kind != "text"):
            return
        iid = item_id(kind, kab, fr)
        self.items[iid] = Item(iid, kind, kab, fr, source, confident, domain=domain)

    def _build(self):
        self._postings.clear()
        for it in self.items.values():
            it.tokens = tokenize(f"{it.kab} {it.fr}")
            self._len[it.id] = len(it.tokens) or 1
            for tok, n in Counter(it.tokens).items():
                self._postings[tok].append((it.id, n))
        self._avg = sum(self._len.values()) / max(len(self._len), 1)
        # Mots kabyles attestés au moins 2 fois (écarte les coquilles et les mots
        # français isolés), forme écrite la plus fréquente.
        forms: dict[str, Counter] = defaultdict(Counter)
        french: set[str] = set()
        for it in self.items.values():
            french.update(fold(w) for w in re.findall(r"[^\W\d_]+", it.fr))
            for w in re.findall(r"[^\W\d_]+", it.kab):
                if len(w) >= 3:
                    forms[fold(w)][w.lower()] += 1
        special = re.compile(r"[ɣɛḍṭẓṛṣḥčǧ]")

        def keep(k: str, c: Counter) -> bool:
            if sum(c.values()) < 2 or k in STOP or k in KAB_FUNCTION_WORDS:
                return False
            # Mot qui existe aussi en français (« leçon », « table ») : seulement
            # s'il porte une lettre propre au kabyle.
            return k not in french or bool(special.search(c.most_common(1)[0][0]))

        self.kab_vocab = {k: c.most_common(1)[0][0] for k, c in forms.items() if keep(k, c)}

    def kabyle_words(self, text: str) -> dict[str, str]:
        """Mots kabyles attestés présents dans un texte : clé normalisée → forme écrite."""
        out = {}
        for w in re.findall(r"[^\W\d_]+", text):
            k = fold(w)
            if len(k) >= 3 and k in self.kab_vocab:
                out[k] = self.kab_vocab[k]
        return out

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
            bonus *= DOMAIN_WEIGHT.get(it.domain, 1.0)
            if it.domain == "prénoms" and ("prenom" in q or "prenoms" in q):
                bonus = 2.0
            ranked.append((sc * bonus, it))
        ranked.sort(key=lambda x: -x[0])
        return [it for _, it in ranked[:k]]

    def references_for(self, message: str) -> str:
        """Bloc de texte injecté dans le prompt du prof."""
        words = self.search(message, "word", 8)
        pairs = self.search(message, "pair", 4)
        songs = self.search(message, "song", 4)
        # Exemples tirés des livres kabyles, seulement si l'élève cite un mot kabyle.
        texts = self.search(message, "text", 2) if self.kabyle_words(message) else []
        if not words and not pairs and not songs and not texts:
            return ""
        lines = []
        if songs:
            lines.append("Chansons (vers sous licence, avec traduction et annotation) :")
            lines += [f"- [{s.source}] KAB : {s.kab}\n  FR : {s.fr}" for s in songs]
        if words:
            lines.append("Vocabulaire :")
            lines += [f"- {w.kab} — {w.fr}" for w in words]
        if pairs:
            lines.append("Phrases authentiques (tirées de livres traduits) :")
            lines += [f"- KAB : {p.kab}\n  FR : {p.fr}" for p in pairs]
        if texts:
            lines.append("Exemples d'emploi dans des livres kabyles (sans traduction, à citer avec prudence) :")
            lines += [f"- {t.kab} ({t.source})" for t in texts]
        return "\n".join(lines)


def _read_jsonl(path: Path):
    """Lit un fichier JSONL. Un fichier absent, illisible (droits) ou une
    ligne abîmée est ignoré avec un avertissement : l'API démarre quand même."""
    try:
        if not path.exists():
            return
        f = open(path, encoding="utf-8")
    except OSError as e:
        print(f"[knowledge] fichier ignoré ({e})", flush=True)
        return
    with f:
        for n, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                print(f"[knowledge] {path.name}:{n} ligne ignorée (JSON invalide)", flush=True)


kb = KnowledgeBase()
