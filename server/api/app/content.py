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
from .knowledge import DOMAIN_WEIGHT, Item, fold, kb

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
    # (pas de nom d'ouvrage ni d'institution dans ce qui s'affiche : les ids restent pour la progression)
    ("hca-sea", "Les animaux de la mer", "Poissons, coquillages et autres animaux marins", "animaux marins", "poterie"),
    ("hca-new-words", "Les mots d'aujourd'hui", "Des mots utiles pour la vie de tous les jours", "général", "officielle"),
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


# ---------- Programme A1 (server/content/curriculum_a1.json) ----------
# Chaque unité : 5 mots au plus + quelques blocs de langue + une capsule.
# Les exercices sont générés ici, dans cet ordre (voir docs/PEDAGOGIE.md) :
#   1. reconnaissance (kabyle → sens)          — prétest + feedback immédiat
#   2. blocs de langue à compléter (cloze)       — approche lexicale
#   3. rappel (sens → kabyle), ordre mélangé     — effet de test, difficulté désirable
#   4. révision de mots des unités précédentes   — répétition espacée, entrelacement


def _curriculum() -> dict:
    path = _content_dir() / "curriculum_a1.json"
    return json.loads(path.read_text("utf-8")) if path.exists() else {"units": []}


def _mcq(eid: str, instruction: str, before: str, answer: str, pool: list[str], rng: random.Random,
         *, after: str = "", translation: str | None = None, explanation: str = "",
         tifinagh: str | None = None) -> dict:
    others = [o for o in dict.fromkeys(pool) if o != answer]
    rng.shuffle(others)
    options = [answer, *others[:2]]
    rng.shuffle(options)
    return {"id": eid, "instruction": instruction, "before": before, "after": after,
            "options": options, "answer": answer, "translation": translation,
            "explanation": explanation, "tifinagh": tifinagh}


def curriculum_lessons() -> list[dict]:
    cur = _curriculum()
    units = cur.get("units", [])
    all_words = [w for u in units for w in u["words"]]
    out = []
    for idx, u in enumerate(units):
        rng = random.Random(u["id"])
        words = u["words"]
        unit_fr = [w["fr"] for w in words]
        unit_kab = [w["kab"] for w in words]
        global_fr = [w["fr"] for w in all_words]
        ex = []
        for w in words:  # 1. reconnaissance
            ex.append(_mcq(f"{u['id']}-r-{w['kab']}", "QUE VEUT DIRE CE MOT ?", w["kab"], w["fr"],
                           unit_fr + global_fr, rng, explanation=f"{w['kab']} — {w['fr']}.",
                           tifinagh=to_tifinagh(w["kab"])))
        blanks = [c["blank"] for c in u.get("chunks", []) if c.get("blank")]
        for c in u.get("chunks", []):  # 2. blocs de langue
            b = c.get("blank")
            if b and b in c["kab"]:
                before, after = c["kab"].split(b, 1)
                ex.append(_mcq(f"{u['id']}-c-{b}", "COMPLÈTE", before, b, blanks + unit_kab, rng,
                               after=after or " ", translation=c["fr"],
                               explanation=f"{c['kab']} — {c['fr']}"))
            else:
                others = [x["fr"] for x in u.get("chunks", []) if x is not c]
                ex.append(_mcq(f"{u['id']}-m-{len(ex)}", "QUE VEUT DIRE ?", c["kab"], c["fr"],
                               others + unit_fr, rng, explanation=f"{c['kab']} — {c['fr']}"))
        recall = list(words)
        rng.shuffle(recall)
        for w in recall:  # 3. rappel
            ex.append(_mcq(f"{u['id']}-p-{w['kab']}", "COMMENT DIT-ON…", f"« {w['fr']} »", w["kab"],
                           unit_kab, rng, after="", explanation=f"« {w['fr']} » se dit {w['kab']}."))
        previous = [w for pu in units[:idx] for w in pu["words"]]
        for w in rng.sample(previous, min(3, len(previous))):  # 4. révision entrelacée
            ex.append(_mcq(f"{u['id']}-v-{w['kab']}", "RÉVISION", w["kab"], w["fr"],
                           [x["fr"] for x in previous], rng, explanation=f"{w['kab']} — {w['fr']}.",
                           tifinagh=to_tifinagh(w["kab"])))
        for e in ex:
            if e["instruction"] == "COMMENT DIT-ON…":
                e["tifinagh"] = None
        out.append({
            "id": u["id"], "level": cur.get("level", "A1"), "order": u.get("order", idx + 1),
            "title": u["title"], "subtitle": u.get("subtitle", ""), "can_do": u.get("can_do", ""),
            "capsule": u.get("capsule"), "needs_review": True, "exercises": ex,
            "words": words, "chunks": u.get("chunks", []), "tutor_focus": u.get("tutor_focus", ""),
        })
    return out


def current_unit(introduced: set[str]) -> dict | None:
    """Première unité dont l'élève n'a pas encore rencontré tous les mots."""
    units = curriculum_lessons()
    for u in units:
        keys = {fold(w["kab"]) for w in u["words"]}
        if not keys <= introduced:
            return u
    return units[-1] if units else None


def session_plan(unit: dict | None) -> str:
    if not unit:
        return "Faire connaissance : niveau, objectifs, vécu de l'élève."
    words = ", ".join(f"{w['kab']} ({w['fr']})" for w in unit["words"])
    chunks = " ; ".join(f"{c['kab']} = {c['fr']}" for c in unit.get("chunks", []))
    return (f"Unité « {unit['title']} » ({unit['level']}). Objectif : {unit.get('can_do', '')}\n"
            f"Mots de l'unité : {words}\nBlocs de langue : {chunks}\n"
            f"Ce que tu dois faire travailler (consigne pour toi seul, ne la recopie pas) : {unit.get('tutor_focus', '')}\n"
            "Ne présente pas plus de 2 ou 3 mots nouveaux par réponse.")


def lessons() -> list[dict]:
    out = curriculum_lessons() or [dict(l) for l in _load("lessons.json")]
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
    # Mot du jour : un mot du programme A1 (vocabulaire courant), sinon du lexique général.
    prog = [w for u in _curriculum().get("units", []) for w in u["words"]]
    if prog:
        pw = prog[_day_index(day, len(prog), "word")]
        w = Item(id="prog", kind="word", kab=pw["kab"], fr=pw["fr"], source="Programme Amusnaw A1")
    else:
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


def _rank(it: Item) -> tuple:
    return (it.status in ("ok", "fixed"), DOMAIN_WEIGHT.get(it.domain, 1.0))


def _find_word(term: str) -> Item | None:
    key = fold(term).strip(" !?.")
    found = [it for it in kb.items.values()
             if it.kind == "word" and it.status != "rejected" and fold(it.kab).split(" (")[0].strip(" !?.") == key]
    return max(found, key=_rank) if found else None


# Vocabulaire courant pour les exercices du chat (pas de termes juridiques
# ni de néologismes savants).
EVERYDAY = ("programme", "vocabulaire de base", "corps humain", "général", "animaux marins", "animaux", "sciences de la terre")


def _everyday_items() -> list[Item]:
    return [it for it in _word_items() if it.domain in EVERYDAY and " " not in it.kab.strip()]


def _programme_exercise(words: list[str], rng: random.Random) -> dict | None:
    """Exercice sur un mot du programme A1, avec des réponses possibles tirées de
    la même unité et des unités précédentes (des mots que l'élève a croisés)."""
    units = _curriculum().get("units", [])
    for w in words:
        key = fold(w).strip(" !?.")
        for i, u in enumerate(units):
            hit = next((x for x in u["words"] if fold(x["kab"]) == key), None)
            if not hit:
                continue
            near = [x for x in u["words"] if x is not hit]
            before = [x for v in units[:i] for x in v["words"]]
            rng.shuffle(before)
            pool = [Item(id=f"prog-{x['kab']}", kind="word", kab=x["kab"], fr=x["fr"], source="Programme")
                    for x in [hit, *near, *before]]
            if len(pool) < 3:
                pool += [Item(id=f"prog-{x['kab']}", kind="word", kab=x["kab"], fr=x["fr"], source="Programme")
                         for v in units[i + 1:i + 2] for x in v["words"]]
            if len(pool) >= 3:
                # distracteurs pris en priorité dans la même unité
                target = pool[0]
                return word_exercise(target, pool[1:4] + [target], rng)
    return None


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
            # 1. Un mot du programme (désigné, ou cité dans la réponse) : l'exercice reste
            #    dans ce que l'élève a déjà vu — mêmes unités, rien qui tombe du ciel.
            ex = _programme_exercise([arg] if arg else list(kb.kabyle_words(reply).values()) +
                                     re.findall(r"«\s?([^»]+?)\s?»", reply), rng)
            if ex:
                blocks.append({"type": "exercise", **ex})
                continue
            # 2. Sinon : mot de la réponse présent dans le lexique, sinon un mot au hasard
            pool = _everyday_items()
            prog = [it for it in pool if it.domain == "programme"] or pool
            mentioned = [it for k in kb.kabyle_words(reply) if (it := _find_word(k)) and it.domain in EVERYDAY]
            target = mentioned[0] if mentioned else (rng.choice(prog) if prog else None)
            pool = [it for it in pool if it.domain == target.domain] if target else pool
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


# ---------- Contrôle du kabyle cité par le prof ----------

_QUOTED = re.compile(r"«\s*([^»]{1,80}?)\s*»|\*\*([^*]{1,80}?)\*\*")


def unverified_kabyle(reply: str, context: str) -> list[str]:
    """Segments kabyles cités par le prof (« … » ou **…**) qui ne figurent ni
    dans le contexte fourni (références, leçon) ni dans le vocabulaire attesté.
    Sert au contrôle qualité et à la relecture, pas à bloquer la réponse."""
    ctx = fold(context)
    out = []
    for m in _QUOTED.finditer(reply):
        seg = (m.group(1) or m.group(2)).strip(" .,!?;:")
        if not seg or not re.search(r"[a-zA-Zɣɛḍṭẓṛṣḥčǧ]", seg):
            continue
        key = fold(seg)
        if key in ctx:
            continue
        words = [fold(w) for w in re.findall(r"[^\W\d_]+", seg)]
        # Une citation en français (traduction) n'est pas du kabyle : on l'ignore.
        from . import router as _r
        def _known(w):  # w : forme écrite (avec ɣ, ḍ…), pas la forme repliée
            return fold(w) in kb.kab_vocab or (_r.MORPH is not None and any(
                "approché" not in a["how"] for a in _r.MORPH.analyze(w)))
        raw = re.findall(r"[^\W\d_]+(?:-[^\W\d_]+)*", seg.lower())
        if all(_known(w) for w in raw if len(w) >= 3):
            continue
        if not any(re.search(r"[ɣɛḍṭẓṛṣḥčǧ]", w) or w in kb.kab_vocab for w in re.findall(r"[^\W\d_]+", seg.lower())):
            continue  # aucun indice de kabyle : probablement du français
        out.append(seg)
    return out
