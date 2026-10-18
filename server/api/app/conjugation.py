"""Conjugaison kabyle par règles (le modèle n'a pas le droit de conjuguer).

Règles de K. Bouamara, « Modélisation des types morphologiques et de la
conjugaison du verbe kabyle. Première partie : formes de base », HAL
hal-05647626, 2026 (CC BY-NC-SA 4.0) :
  - règle 2 : les affixes de personne sont les mêmes pour tous les verbes ;
  - règle 3 : 3e masc. sing. y- devant voyelle, i- devant consonne ;
  - règles 14 à 16 : chute et insertion de la voyelle d'appui « e » ;
  - règle 9 : verbes d'état au prétérit (-eɣ, -eḍ, ∅, -et, -it) ;
  - tableaux II : les 4 thèmes de chaque type de verbe.

Chaque verbe est décrit par ses 4 thèmes (prétérit, prétérit négatif,
aoriste, aoriste intensif) dans server/content/verbs.json. Les formes sont
ensuite vérifiées contre le corpus HCA (forme attestée ou non).
"""
from __future__ import annotations

import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

VOWELS = set("aeiu")
PERSONS = ["1sg", "2sg", "3sgm", "3sgf", "1pl", "2plm", "2plf", "3plm", "3plf"]
PERSON_LABEL = {
    "1sg": "nekk", "2sg": "kečč / kemm", "3sgm": "netta", "3sgf": "nettat", "1pl": "nekkni",
    "2plm": "kunwi", "2plf": "kunemti", "3plm": "nutni", "3plf": "nutenti",
}
PREFIX = {"2sg": "t", "3sgf": "t", "1pl": "n", "2plm": "t", "2plf": "t"}
SUFFIX = {"1sg": "eɣ", "2sg": "eḍ", "2plm": "em", "2plf": "emt", "3plm": "en", "3plf": "ent"}
ASPECTS = {
    "pret": "Prétérit (action accomplie)",
    "neg": "Prétérit négatif (ur … ara)",
    "aor": "Aoriste (futur avec ad)",
    "int": "Aoriste intensif (habitude, action en cours)",
}

_vowel = lambda c: c in VOWELS  # noqa: E731


def _cluster(s: str) -> bool:
    """Le mot commence par deux consonnes (ou une géminée) : il faut un « e » après t-/n-."""
    return len(s) >= 2 and not _vowel(s[0]) and not _vowel(s[1])


def _form(theme: str, person: str, aspect: str, state: bool = False) -> str:
    th = theme
    if state and aspect in ("pret", "neg"):  # règle 9 : pas de préfixe
        suf = {"1sg": "eɣ", "2sg": "eḍ", "3sgm": "", "3sgf": "et"}.get(person, "it")
        if th[-1] in VOWELS and suf:
            suf = suf[1:]
        return th + suf
    suf = SUFFIX.get(person, "")
    pre = PREFIX.get(person, "")
    if suf:
        if th[-1] in VOWELS:
            # thème à finale vocalique : le suffixe perd son « e » ;
            # au prétérit, -a devient -i aux 1re et 2e du singulier (ura → uriɣ).
            if aspect in ("pret", "neg") and th[-1] == "a" and person in ("1sg", "2sg"):
                th = th[:-1] + "i"
            suf = suf[1:]
        elif th[0] == "e" and len(th) >= 3 and not _vowel(th[1]) and not _vowel(th[2]):
            # els, ečč, efk : le « e » initial tombe sans préfixe (lseɣ), reste avec (telseḍ)
            if not pre:
                th = th[1:]
        elif len(th) >= 3 and th[-2] == "e" and not _vowel(th[-1]):
            # règle 14.2 : le « e » avant la dernière consonne s'efface (gennez → gennz-)
            th = th[:-2] + th[-1]
            # trois consonnes libres au début → « e » après la 1re (bdr → bedr), sauf géminée (ssn)
            if (len(th) >= 3 and not any(_vowel(c) for c in th[:3]) and th[0] != th[1]):
                th = th[0] + "e" + th[1:]
    if person == "3sgm":
        return ("y" if _vowel(th[0]) else "i") + th
    if pre:
        return pre + ("e" if _cluster(th) else "") + th + suf
    return th + suf


def conjugate(verb: dict, rules_only: bool = False) -> dict:
    """Une forme par personne. Table explicite (« paradigm ») si elle existe, sinon règles."""
    out = {}
    par = {} if rules_only else (verb.get("paradigm") or {})
    themes = verb.get("themes") or {}
    for aspect in ASPECTS:
        tab = par.get(aspect)
        if tab and all(tab.get(p) for p in PERSONS):
            out[aspect] = {p: tab[p][0] for p in PERSONS}
            continue
        th = themes.get(aspect)
        if th:
            out[aspect] = {p: _form(th, p, aspect, verb.get("state", False)) for p in PERSONS}
    return out


def verb_forms(verb: dict) -> dict[str, tuple[str, str]]:
    """Toutes les formes connues d'un verbe → (aspect, personne) : règles, tables, variantes,
    participes, impératif. Sert au lemmatiseur."""
    out: dict[str, tuple[str, str]] = {}
    for asp, d in conjugate(verb, rules_only=True).items():
        for p, f in d.items():
            out.setdefault(f, (asp, p))
    for src in (verb.get("paradigm") or {}, verb.get("variants") or {}):
        for asp, d in src.items():
            for p, fs in d.items():
                for f in (fs if isinstance(fs, list) else [fs]):
                    out.setdefault(f, (asp, p))
    return out


def _norm(s: str) -> str:
    return unicodedata.normalize("NFC", s).lower().strip()


@lru_cache(maxsize=1)
def _verbs(path: str) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    idx = {}
    # Priorité : nos verbes (Bouamara, courants…), puis les verbes importés les plus attestés,
    # verbes simples avant dérivés.
    verbs = sorted(data["verbs"], key=lambda v: (v.get("source") == "amyag", bool(v.get("derived")),
                                                 -int(v.get("attested_forms") or 0)))
    for v in verbs:
        idx.setdefault(_norm(v["lemma"]), v)
        for fr in re.split(r"[,;]", re.sub(r"\(.*?\)", "", v.get("fr") or "")):
            fr = fr.strip()
            if fr:
                idx.setdefault("fr:" + _norm(re.sub(r"^(s'|se |s’)", "", fr)), v)
                idx.setdefault("fr:" + _norm(fr), v)
    return idx


def find_verb(word: str, path: str) -> dict | None:
    try:
        idx = _verbs(path)
    except (OSError, ValueError):
        return None
    w = _norm(word)
    return idx.get(w) or idx.get("fr:" + w) or idx.get("fr:" + re.sub(r"^(s'|se )", "", w))


def render(verb: dict, attested: set[str] | None = None, sources: bool = False) -> str:
    """Tableau texte (markdown simple) de la conjugaison, prêt à citer tel quel."""
    table = conjugate(verb)
    lines = [f"Conjugaison de « {verb['lemma']} » ({verb['fr']}) :"]
    for aspect, forms in table.items():
        lines.append(f"\n{ASPECTS[aspect]}")
        for p in PERSONS:
            f = forms[p]
            if aspect == "neg":
                f = f"ur {f} ara"
            elif aspect == "aor":
                f = f"ad {f}"
            lines.append(f"- {PERSON_LABEL[p]} : {f}")
    if sources and verb.get("paradigm"):
        lines.append("\nSource : tables de conjugaison taqbaylit/kabyle-verbs (amyag.com), CC BY 4.0.")
    elif sources:
        lines.append("\nSource : règles de K. Bouamara (HAL, 2026).")
    return "\n".join(lines)
