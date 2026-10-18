"""Leçon guidée : quand l'élève veut apprendre (« Apprendre », « on continue »,
« autre chose »…), le serveur fait avancer le programme A1 lui-même, deux mots
nouveaux à la fois, avec une phrase utile et un exercice. Il vérifie aussi la
réponse de l'élève (mot ou phrase attendus, fautes d'orthographe proches).
Tout vient du programme vérifié : rien n'est inventé, rien ne se répète, et la
réponse est immédiate. Le modèle ne sert qu'à la conversation libre."""
import random
import re
import unicodedata

from . import content
from .knowledge import fold

NEXT = re.compile(
    r"\b(apprendre|apprends|continu\w*|la suite|suite|suivant\w*|autre chose|change\w*|nouveau\w*|"
    r"nouvelle\w*|retenu|le[çc]on|avance\w*|encore|vas-y|go)\b", re.I)
NOT_NEXT = re.compile(r"\b(comment|que veut|veut dire|conjug|pourquoi|c'est quoi|traduis|explique)\b", re.I)

SUGGEST_STEP = ["Continuer", "Explique-moi cette phrase", "Parlons d'autre chose"]

# Dernier pas proposé à chaque élève (mémoire du serveur ; perdue au redémarrage, sans gravité)
_state: dict[str, dict] = {}


YES = re.compile(r"^\s*(oui|ouais|ok|okay|d'accord|dac|vas-y|allez|go|yes|ih|wah|on y va)\b", re.I)
_offered: set[str] = set()  # élèves à qui l'on vient de proposer la suite


def wants_next(message: str, intent: str | None, user_id: str = "") -> bool:
    if intent == "learn":
        return True
    m = message.strip()
    if user_id in _offered and len(m) <= 40 and YES.search(m):
        return True
    return len(m) <= 90 and bool(NEXT.search(m)) and not NOT_NEXT.search(m)


def _pick(rng: random.Random, options: list[str]) -> str:
    return rng.choice(options)


def step(seen: set[str], user_id: str = "", name: str = "") -> tuple[str, dict[str, str]]:
    """Réponse du prochain pas de la leçon + mots présentés {clé: forme}."""
    unit = content.current_unit(seen)
    if not unit:
        return "", {}
    rng = random.Random(f"{user_id}{len(seen)}")
    words = unit["words"]
    new = [w for w in words if fold(w["kab"]) not in seen][:2]
    chunks = unit.get("chunks", [])
    done_before = sum(1 for w in words if fold(w["kab"]) in seen)
    hi = f", {name}" if name else ""
    parts = []
    if done_before == 0:
        parts.append(_pick(rng, [
            f"Allez{hi}, on attaque **{unit['title']}** !",
            f"Nouvelle étape{hi} : **{unit['title']}**.",
            f"C'est parti pour **{unit['title']}**{hi} !",
        ]) + (f" À la fin, {unit['can_do'][0].lower()}{unit['can_do'][1:]}" if unit.get("can_do") else ""))
    if new:
        intro = _pick(rng, ["Voici", "Retiens", "Deux mots à garder en tête :" if len(new) > 1 else "Un mot à garder :"])
        if intro.endswith(":"):
            parts.append(intro)
        else:
            parts.append(f"{intro} {'ces deux mots' if len(new) > 1 else 'ce mot'} :")
        parts += [f"- « {w['kab']} » : {w['fr']}" for w in new]
    else:
        parts.append(f"Tu as vu tous les mots de **{unit['title']}**. On révise avant de passer à la suite :")
        parts += [f"- « {w['kab']} » : {w['fr']}" for w in words]
    chunk = chunks[(done_before // 2) % len(chunks)] if chunks else None
    if chunk:
        parts.append("")
        parts.append(_pick(rng, [
            f"Et une phrase qu'on entend tout le temps : « {chunk['kab']} » — {chunk['fr']}",
            f"Dans la vraie vie, ça donne : « {chunk['kab']} » — {chunk['fr']}",
            f"Une phrase toute faite : « {chunk['kab']} » — {chunk['fr']}",
        ]))
        parts.append("")
        parts.append(_pick(rng, [
            f"À toi : écris « {chunk['kab']} », comme si tu le disais à quelqu'un.",
            "Essaie de l'écrire de mémoire, je te dis si c'est juste.",
            f"Ton tour : écris-moi « {chunk['kab'].rstrip(' !?.')} », ou tente l'exercice juste en dessous.",
        ]))
    parts.append(f"[[MOT: {new[0]['kab'] if new else words[0]['kab']}]]")
    parts.append("[[EXERCICE]]")
    keys = {fold(w["kab"]): w["kab"] for w in new}
    _offered.discard(user_id)
    if user_id:
        _state[user_id] = {"chunk": chunk["kab"] if chunk else "", "words": [w["kab"] for w in new],
                           "fr": chunk["fr"] if chunk else "", "all_chunks": [c["kab"] for c in chunks],
                           "vocab": [w["kab"] for w in words] + [t for c in chunks
                                                                 for t in re.split(r"[\s\-]+", c["kab"].strip(" !?.,")) if t]}
    return "\n".join(parts), keys


# ---------- Vérifier la réponse de l'élève ----------

def _plain(s: str) -> str:
    """Comparaison tolérante : minuscules, sans points souscrits ni ponctuation (ɣ = g, ḍ = d…)."""
    return " ".join(re.sub(r"[^\w ]+", " ", fold(s).replace("-", " ")).split())


def _dist(a: str, b: str) -> int:
    """Distance d'édition (petits mots)."""
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def _near_miss(said: str, vocab: list[str]) -> str | None:
    """Mot de l'élève à une ou deux lettres d'un mot de l'unité → bonne orthographe."""
    known = {_plain(v): v for v in vocab if len(_plain(v)) >= 4}
    for w in said.split():
        if w in known:
            continue
        for good, orig in known.items():
            if _dist(w, good) <= (1 if len(good) < 7 else 2):
                return orig
    return None


def check_answer(user_id: str, message: str) -> str | None:
    """Si l'élève répond au dernier pas de la leçon : bravo, ou correction douce.
    Renvoie None si le message n'est pas une réponse (le modèle prend le relais)."""
    st = _state.get(user_id)
    if not st or "?" in message or len(message) > 120:
        return None
    said = _plain(message)
    if not said:
        return None
    rng = random.Random(message)
    flat = said.replace(" ", "")
    bravo = ["Parfait, « {t} » est juste !", "Bravo, c'est exactement ça : « {t} ».", "Oui ! « {t} », bien écrit."]
    more = ["On continue ?", "Tu veux la suite, ou tu préfères t'entraîner encore ?", "Prêt pour les mots suivants ?"]
    # 1. une phrase de l'unité, bien écrite (fell-ak ou fell-am : les deux sont justes)
    fix = _near_miss(said, st.get("vocab") or [])
    for c in st.get("all_chunks") or ([st["chunk"]] if st["chunk"] else []):
        if _plain(c).replace(" ", "") and _plain(c).replace(" ", "") in flat:
            _state.pop(user_id, None)
            _offered.add(user_id)
            return _pick(rng, bravo).format(t=c) + " " + _pick(rng, more)
    # 2. la phrase attendue, à une ou deux lettres près
    if st["chunk"]:
        want = _plain(st["chunk"]).replace(" ", "")
        if abs(len(want) - len(flat)) <= 3 and _dist(flat, want) <= 2:
            return f"Presque ! On écrit « {st['chunk']} ». " + _pick(rng, ["Réessaie une fois, pour le fixer.",
                                                                          "Écris-le encore une fois ?"])
    targets = st["words"]
    for t in targets:
        if _plain(t) and _plain(t) in said:
            if fix:  # une partie juste, une petite faute ailleurs
                return f"« {t} », c'est bien ça ! Petite correction : on écrit « {fix} ». " + \
                    _pick(rng, ["Tu le réécris ?", "Essaie la phrase en entier ?"])
            _state.pop(user_id, None)
            _offered.add(user_id)
            return _pick(rng, bravo).format(t=t) + " " + _pick(rng, more)
    # presque : une ou deux lettres de différence (tanemirt → tanemmirt)
    for t in targets:
        originals = [x for x in re.split(r"[\s\-]+", t.strip(" !?.,")) if x]
        for w in said.split():
            for orig in originals:
                good = _plain(orig)
                if len(good) >= 4 and w != good and _dist(w, good) <= (1 if len(good) < 7 else 2):
                    good = orig  # on montre la bonne orthographe, avec ɣ, ḍ, ɛ…
                    return (f"Presque ! On écrit « {good} »" +
                            (f", dans « {t} »" if t != good else "") +
                            ". " + _pick(rng, ["Réessaie une fois, pour le fixer.", "Écris-le encore une fois ?"]))
    return None
