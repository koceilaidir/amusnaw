"""Vérifications sûres d'une phrase kabyle, sans modèle : négation « ur … ara » et lettres
spéciales (ɣ, ɛ, ḍ, č…). Le vocabulaire vient du kabyle écrit par des humains (corpus des
livres, Tatoeba, livres bilingues). Quand une règle trouve une faute, le serveur répond
lui-même : la correction est alors toujours juste.
"""
import re
import sqlite3
import threading
from collections import Counter
from pathlib import Path

from .config import get_settings
from .knowledge import fold

_lock = threading.Lock()
_vocab: Counter | None = None
_by_fold: dict[str, str] = {}

# compléments qui remplacent « ara » dans une négation
_NEG_DONE = {"ara", "acemma", "kra", "yiwen", "yiwet", "ula", "walu", "ḥedd", "werǧin", "abaden", "abada",
             "ulac", "lḥedd", "ḥtta"}
_SPECIAL = {"ɣ": "ɣ (et non g ou gh)", "ɛ": "ɛ (et non e)", "ḍ": "ḍ", "ṭ": "ṭ", "ẓ": "ẓ", "ṛ": "ṛ", "ṣ": "ṣ",
            "ḥ": "ḥ", "č": "č", "ǧ": "ǧ"}
_PREFIX = re.compile(r"^\s*(?:corrige[rz]?(?:-moi)?|correction|v[ée]rifie|est-ce (?:que )?(?:c['’]est )?juste)"
                     r"\s*(?:(?:ma|cette|la)\s+phrase|ça|ceci|stp|s'il te plaît)?\s*[:\-–]?\s*", re.I)


def _words(s: str) -> list[str]:
    return re.findall(r"[^\W\d_]+", s.lower())


def _load() -> None:
    global _vocab
    with _lock:
        if _vocab is not None:
            return
        c: Counter = Counter()
        d = Path(get_settings().data_dir)
        wf = d / "word_freq.tsv"
        if wf.exists():
            for line in wf.read_text(encoding="utf-8").splitlines():
                w, _, n = line.partition("\t")
                if w and n.isdigit():
                    c[w.lower()] += int(n)
        tm = Path("/tmp/amusnaw_tm.sqlite")
        if tm.exists():
            try:
                con = sqlite3.connect(tm)
                for (kab,) in con.execute("SELECT kab FROM tm"):
                    c.update(_words(kab))
                con.close()
            except sqlite3.Error:
                pass
        best: dict[str, tuple[int, str]] = {}
        for w, n in c.items():
            f = fold(w)
            if n > best.get(f, (0, ""))[0]:
                best[f] = (n, w)
        _by_fold.clear()
        _by_fold.update({f: w for f, (n, w) in best.items()})
        _vocab = c


def text_to_check(message: str) -> str:
    """« Corrige : ur ččiɣ » → « ur ččiɣ »."""
    t = _PREFIX.sub("", message, count=1).strip()
    return t.strip("«»\"“” ")


def _letters_note(wrong: str, right: str) -> str:
    missing = [_SPECIAL[ch] for ch in dict.fromkeys(right) if ch in _SPECIAL and ch not in wrong]
    if missing:
        return f"on écrit « {right} », avec {', '.join(missing)}."
    return f"on écrit « {right} »."


def check(text: str) -> tuple[str, list[str]]:
    """Renvoie (phrase corrigée, explications). Aucune explication = rien trouvé par les règles."""
    _load()
    notes: list[str] = []
    out = text

    # 1. Lettres spéciales : mot inconnu dont la forme sans accents correspond à un mot fréquent
    for w in dict.fromkeys(re.findall(r"[^\W\d_]+", text)):
        lw = w.lower()
        if len(lw) < 3:
            continue
        right = _by_fold.get(fold(lw))
        # forme bien plus fréquente que celle écrite (les fautes existent aussi dans le corpus)
        if not right or right == lw or _vocab.get(right, 0) < max(20, 20 * _vocab.get(lw, 0)):
            continue
        fixed = right if w.islower() else right[:1].upper() + right[1:]
        out = re.sub(rf"(?<![^\W\d_]){re.escape(w)}(?![^\W\d_])", fixed, out)
        notes.append(f"**{w} → {fixed}** : {_letters_note(lw, right)}")

    # 2. Négation : « ur » sans « ara » (ni un autre complément : acemma, yiwen, walu…)
    toks = _words(out)
    if "ur" in toks and not any(t in _NEG_DONE for t in toks[toks.index("ur") + 1:]):
        m = re.search(r"(?<![^\W\d_])([Uu]r\s+[^\s.,!?;:]+)", out)
        if m:
            out = out[:m.end()] + " ara" + out[m.end():]
            notes.append("**ur … ara** : la négation kabyle a deux parties. « ur » se place avant le verbe "
                         f"et « ara » juste après : « {m.group(1).lower()} ara ».")
    return out, notes


def reply(message: str) -> str | None:
    """Réponse du serveur quand une règle sûre trouve une faute, sinon None (le modèle répond)."""
    text = text_to_check(message)
    if not text or len(text) > 300:
        return None
    fixed, notes = check(text)
    if not notes:
        return None
    lines = [f"Presque ! La bonne forme : **{fixed}**", ""]
    lines += [f"- {n}" for n in notes[:3]]
    lines += ["", "Réécris la phrase corrigée pour la fixer dans ta mémoire."]
    return "\n".join(lines)
