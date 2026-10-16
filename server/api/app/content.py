"""Contenus pédagogiques servis à l'app : leçons, mot du jour, capsules
culture, et « blocs » insérés dans le chat (carte mot, exercice, capsule).

Tout vit sur le serveur : on peut ajouter des leçons ou des capsules sans
republier l'app (fichiers server/content/*.json + base kabyle de data/).
"""

import hashlib
import json
import random
import re
from datetime import date
from pathlib import Path

from .config import get_settings
from .knowledge import Item, fold, kb

# ---------- Translittération latin → tifinagh (néo-tifinagh kabyle) ----------

_TIFINAGH = {
    "a": "ⴰ", "b": "ⴱ", "c": "ⵛ", "č": "ⵞ", "d": "ⴷ", "ḍ": "ⴹ", "e": "ⴻ", "ɛ": "ⵄ",
    "f": "ⴼ", "g": "ⴳ", "ǧ": "ⴵ", "ɣ": "ⵖ", "h": "ⵀ", "ḥ": "ⵃ", "i": "ⵉ", "j": "ⵊ",
    "k": "ⴽ", "l": "ⵍ", "m": "ⵎ", "n": "ⵏ", "q": "ⵇ", "r": "ⵔ", "ṛ": "ⵕ", "s": "ⵙ",
    "ṣ": "ⵚ", "t": "ⵜ", "ṭ": "ⵟ", "u": "ⵓ", "w": "ⵡ", "x": "ⵅ", "y": "ⵢ", "z": "ⵣ",
    "ẓ": "ⵥ",
}


def to_tifinagh(text: str) -> str:
    out = []
    for ch in text.lower():
        out.append(_TIFINAGH.get(ch, ch if not ch.isalpha() else ""))
    return "".join(out)


# ---------- Chargement ----------

def _content_dir() -> Path:
    # Conteneur : /app/content ; dépôt : server/content
    for p in (Path(get_settings().content_dir), Path(__file__).resolve().parents[2] / "content"):
        if p.exists():
            return p
    return Path(get_settings().content_dir)


def _load(name: str) -> list[dict]:
    path = _content_dir() / name
    return json.loads(path.read_text("utf-8")) if path.exists() else []


def capsules() -> list[dict]:
    return _load("capsules.json")


def capsule(cid: str) -> dict | None:
    return next((c for c in capsules() if c["id"] == cid), None)


def _clean_fr(fr: str) -> str:
    fr = re.sub(r"\s+", " ", fr).strip(" .;:")
    if fr.startswith("(") and fr.endswith(")"):
        fr = fr[1:-1]
    if fr.count("(") > fr.count(")"):
        fr += ")"
    return fr[:1].upper() + fr[1:] if fr else fr


def _word_items(domain: str | None = None) -> list[Item]:
    items = [it for it in kb.items.values()
             if it.kind == "word" and it.status != "rejected"
             and 2 <= len(it.kab) <= 40 and 2 <= len(it.fr) <= 40 and not it.fr.lower().startswith("z.")]
    if domain:
        items = [it for it in items if it.domain == domain]
    return items


# ---------- Exercices générés à partir de la base ----------

def word_exercise(item: Item, pool: list[Item], rng: random.Random) -> dict:
    """« Que veut dire … ? » avec 2 distracteurs tirés du même livre."""
    answer = _clean_fr(item.fr)
    others = list({_clean_fr(o.fr) for o in pool if o.id != item.id and _clean_fr(o.fr) != answer})
    rng.shuffle(others)
    options = [answer, *others[:2]]
    rng.shuffle(options)
    return {
        "id": f"w-{item.id}", "instruction": "QUE VEUT DIRE CE MOT ?",
        "before": item.kab, "after": "", "options": options, "answer": answer,
        "translation": None,
        "explanation": f"{item.kab} — {answer}.",
        "tifinagh": to_tifinagh(item.kab),
        "source": item.source,
    }


AUTO_LESSONS = [
    # id, titre, sous-titre, domaine du lexique, capsule
    ("hca-sea", "Les animaux de la mer", "D'après le lexique marin du HCA", "animaux marins", "poterie"),
    ("hca-new-words", "Les mots d'aujourd'hui", "D'après les glossaires du HCA", "général", "officielle"),
]


def _auto_lesson(lid: str, title: str, subtitle: str, src: str, cap: str, n: int = 8) -> dict | None:
    pool = _word_items(src)
    if len(pool) < 4:
        return None
    rng = random.Random(lid)
    chosen = rng.sample(pool, min(n, len(pool)))
    return {"id": lid, "level": "A1", "order": 10 + len(lid), "title": title, "subtitle": subtitle,
            "capsule": cap, "needs_review": True,
            "exercises": [word_exercise(it, pool, rng) for it in chosen]}


def lessons() -> list[dict]:
    out = [dict(l) for l in _load("lessons.json")]
    for args in AUTO_LESSONS:
        l = _auto_lesson(*args)
        if l:
            out.append(l)
    for l in out:
        for ex in l["exercises"]:
            ex.setdefault("tifinagh", to_tifinagh(ex["before"]) if not ex.get("after") else None)
        if l.get("capsule"):
            l["capsule_data"] = capsule(l["capsule"])
    return sorted(out, key=lambda l: l.get("order", 99))


def lesson(lid: str) -> dict | None:
    return next((l for l in lessons() if l["id"] == lid), None)


def lesson_summaries() -> list[dict]:
    return [{"id": l["id"], "level": l["level"], "title": l["title"], "subtitle": l["subtitle"],
             "count": len(l["exercises"])} for l in lessons()]


# ---------- Aujourd'hui ----------

def _day_index(day: date, n: int, salt: str) -> int:
    h = hashlib.sha1(f"{salt}{day.isoformat()}".encode()).hexdigest()
    return int(h, 16) % max(n, 1)


def today(day: date) -> dict:
    words = [it for it in _word_items() if " " not in it.kab.strip()] or _word_items()
    w = words[_day_index(day, len(words), "word")] if words else None
    caps = capsules()
    c = caps[_day_index(day, len(caps), "capsule")] if caps else None
    ls = lessons()
    return {
        "date": day.isoformat(),
        "word": {"kab": w.kab, "fr": _clean_fr(w.fr), "tifinagh": to_tifinagh(w.kab),
                 "source": w.source} if w else None,
        "capsule": c,
        "lesson": {"id": ls[0]["id"], "title": ls[0]["title"], "subtitle": ls[0]["subtitle"],
                   "count": len(ls[0]["exercises"])} if ls else None,
    }


# ---------- Blocs dans le chat ----------
# Le prof peut terminer sa réponse par UNE balise : [[MOT: aman]], [[EXERCICE]],
# [[CAPSULE: yennayer]]. Le serveur retire la balise du texte et ajoute un bloc
# construit à partir de la base vérifiée (le contenu ne vient pas du modèle).

MARKER = re.compile(r"\[\[\s*(MOT|WORD|EXERCICE|EXERCISE|CAPSULE)\s*(?::\s*([^\]]*))?\]\]", re.I)


def strip_markers(reply: str) -> tuple[str, list[tuple[str, str]]]:
    found = [(m.group(1).upper(), (m.group(2) or "").strip()) for m in MARKER.finditer(reply)]
    text = MARKER.sub("", reply).rstrip()
    return text, found


def _find_word(term: str) -> Item | None:
    key = fold(term)
    best = None
    for it in kb.items.values():
        if it.kind == "word" and it.status != "rejected" and fold(it.kab).split(" (")[0] == key:
            if best is None or it.status in ("ok", "fixed"):
                best = it
    return best


def build_blocks(reply: str, markers: list[tuple[str, str]], seed: str) -> list[dict]:
    blocks: list[dict] = []
    rng = random.Random(seed)
    for kind, arg in markers[:2]:
        if kind in ("MOT", "WORD") and arg:
            it = _find_word(arg)
            if it:
                blocks.append({"type": "word", "kab": it.kab, "fr": _clean_fr(it.fr),
                               "tifinagh": to_tifinagh(it.kab), "source": it.source})
        elif kind in ("EXERCICE", "EXERCISE"):
            # Mot de la réponse présent dans le lexique, sinon un mot au hasard
            pool = _word_items()
            mentioned = [it for k in kb.kabyle_words(reply) if (it := _find_word(k))]
            target = mentioned[0] if mentioned else (rng.choice(pool) if pool else None)
            if target and len(pool) >= 3:
                blocks.append({"type": "exercise", **word_exercise(target, pool, rng)})
        elif kind == "CAPSULE":
            c = capsule(arg) if arg else None
            if not c:
                caps = capsules()
                words = set(kb.kabyle_words(reply)) | {fold(w) for w in re.findall(r"\w+", reply)}
                c = next((x for x in caps if any(fold(t) in words for t in x["tags"])), None) \
                    or (rng.choice(caps) if caps else None)
            if c:
                blocks.append({"type": "capsule", **c})
    return blocks
