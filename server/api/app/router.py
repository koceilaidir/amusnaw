"""Aiguilleur : répond sans le modèle quand la réponse doit être exacte.

Le petit modèle invente du kabyle. Pour les questions dont la réponse est
dans la base (« comment dit-on … ? », « que veut dire … ? », « conjugue … »)
c'est le serveur qui écrit la réponse, avec le kabyle recopié de la base.
Le modèle ne sert que pour la conversation libre.
"""
from __future__ import annotations

import random
import re

from . import conjugation
from .config import get_settings
from .content import _clean_fr, _rank, capsules
from .knowledge import Item, fold, kb

ARTICLES = r"^(?:(?:le|la|les|un|une|des|du|de\s+la|de|mon|ma|mes|ton|ta|tes|son|sa|ses)\s+|(?:l|d)['’]\s*)+"
KAB_CHARS = "a-zA-ZɛɣḍṭẓṛṣḥčǧƐƔḌṬẒṚṢḤČǦεγ"

# « Comment on dit X (en kabyle) ? », « Comment dire X », « Comment dit-on X »
_HOW_SAY = re.compile(
    r"^(?:et\s+)?comment\s+(?:est-ce qu[’']on\s+dit|on\s+dit|dit[- ]on|dire|se\s+dit|tu\s+dis|dis-tu|je\s+dis)"
    r"\s+(?P<x>.+?)(?:\s+en\s+(?:kabyle|taqbaylit|tamazight|berbère))?\s*\??\s*$", re.I)
_TRANSLATE = re.compile(r"^(?:traduis|traduire|traduction(?: de)?)\s*(?:en kabyle)?\s*[:\-]?\s*(?P<x>.+?)\s*$", re.I)
# « Que veut dire X ? », « Ça veut dire quoi X ? », « Que signifie X ? », « C'est quoi X ? »
_MEANING = re.compile(
    r"^(?:que\s+veut\s+dire|qu[’']est-ce\s+que\s+veut\s+dire|ça\s+veut\s+dire\s+quoi|ca\s+veut\s+dire\s+quoi|"
    r"que\s+signifie|c[’']est\s+quoi|ça\s+signifie\s+quoi|le\s+sens\s+de|traduis-moi)\s+(?P<x>.+?)\s*\??\s*$",
    re.I)
_CONJ = re.compile(r"conjug\w*\s+(?:(?:le\s+)?verbe\s+)?[«\"“']?\s*(?P<x>[\w’'-]+(?:\s[\w’'-]+)?)", re.I)

# Hors sujet évident (en plus du code, déjà filtré par tutor.py)
_OFF_TOPIC = re.compile(
    r"\b(m[ée]dicament|ordonnance|posologie|antibiotique|quel\s+traitement|soigner|"
    r"devoirs?\s+de\s+(?:maths?|math[ée]matiques|physique|chimie|anglais|svt|philo)|"
    r"(?:mon|ce|un)\s+devoir\s+de\s+(?:maths?|math[ée]matiques|physique|chimie)|"
    r"[ée]quation|d[ée]riv[ée]e|int[ée]grale|"
    r"crypto|bitcoin|bourse|investir|placement|imp[ôo]ts?|avocat|proc[èe]s|"
    r"m[ée]t[ée]o|recette\s+de\s+(?!.*kabyle)|r[ée]sultat\s+du\s+match)\b", re.I)


def _strip(x: str) -> str:
    x = x.strip().strip("«»\"“”'’ ").strip()
    x = re.sub(r"\s*[?!.]+$", "", x)
    return x


def _fr_keys(fr: str) -> list[str]:
    """« main, bras » → ['main', 'bras'] ; enlève articles et parenthèses."""
    out = []
    for part in re.split(r"[,;/]| ou ", re.sub(r"\([^)]*\)", "", fr)):
        p = fold(part).strip(" .:!?")
        p = re.sub(ARTICLES, "", p).strip()
        if p:
            out.append(p)
    return out


MORPH = None  # morph.Lemmatizer chargé au démarrage (main.py)

PERS_FR = {"1sg": "je", "2sg": "tu", "3sgm": "il", "3sgf": "elle", "1pl": "nous", "2plm": "vous (hommes)",
           "2plf": "vous (femmes)", "3plm": "ils", "3plf": "elles"}
ASP_FR = {"pret": "au passé (prétérit)", "neg": "au passé négatif (avec ur … ara)", "aor": "à l'aoriste (futur avec ad)",
          "int": "à l'aoriste intensif (habitude, action en cours)"}
CLITIC_FR = {"iw": "mon, ma", "w": "mon, ma", "ik": "ton, ta (homme)", "im": "ton, ta (femme)", "is": "son, sa",
             "s": "son, sa", "nneɣ": "notre", "nwen": "votre", "nkent": "votre (femmes)", "nsen": "leur",
             "nsent": "leur (femmes)", "as": "à lui, à elle", "yas": "à lui, à elle", "asen": "à eux", "yasen": "à eux", "asent": "à elles", "iyi": "moi, me",
             "yi": "moi, me", "ak": "à toi (homme)", "am": "à toi (femme)", "aɣ": "nous", "t": "le", "tt": "la",
             "ten": "les", "tent": "les (fém.)", "d": "vers ici", "agi": "ce…-ci", "a": "ce…-ci", "nni": "ce…-là",
             "ines": "son, sa", "inu": "mon, ma"}


def explain_form(x: str) -> str | None:
    """« yeswa » → forme du verbe sew (boire) au passé, il. Seulement des analyses exactes."""
    if MORPH is None:
        return None
    an = [a for a in MORPH.analyze(x) if "approché" not in a["how"] and a["pos"] in ("verbe", "nom")]
    if not an:
        return None
    a = an[0]
    src = [MORPH.verb_fr[a["lemma"]]] if a["pos"] == "verbe" and a["lemma"] in MORPH.verb_fr \
        else sorted(MORPH.meanings.get(a["lemma"], ()), key=len)
    seen, means = set(), []
    for m in src:
        for piece in re.split(r"[,;]", re.sub(r"\(.*?\)", "", m)):
            piece = re.sub(r"\s+", " ", piece).strip(" .!")
            k = fold(re.sub(r"^(le|la|les|l'|un|une)\s*", "", piece.lower()))
            if piece and not piece.endswith("!") and k not in seen:
                seen.add(k)
                means.append(piece[0].lower() + piece[1:])
    mean = ", ".join(means[:3])
    if not mean:
        en = MORPH.meanings_en.get(a["lemma"])
        mean = f"en anglais : « {en} »" if en else "sens non encore relevé"
    if a["pos"] == "verbe" and " " in a["how"] and a["how"].split()[0] in ASP_FR:
        readings = []
        for b in an:
            if b["lemma"] == a["lemma"] and " " in b["how"] and b["how"].split()[0] in ASP_FR:
                asp, pers = b["how"].split()[:2]
                r = f"{ASP_FR[asp]}, personne « {PERS_FR.get(pers, pers)} »"
                if r not in readings:
                    readings.append(r)
        txt = (f"« {x} » est une forme du verbe « {a['lemma']} » ({mean}) : " + " ; ou ".join(readings[:3]) + ".")
    elif a["pos"] == "verbe" and a["how"].startswith("participe"):
        txt = f"« {x} » est un participe du verbe « {a['lemma']} » ({mean}) : « qui … »."
    elif a["how"].startswith("annexion"):
        txt = (f"« {x.split('-')[0]} » est la forme annexée de « {a['lemma']} » ({mean}) : elle s'emploie après "
               f"une préposition ou quand le sujet suit le verbe.")
    elif "pluriel" in a["how"]:
        txt = f"« {x.split('-')[0]} » est un pluriel de « {a['lemma']} » ({mean})."
    elif "forme" in a["how"] and a["lemma"] != x.split("-")[0]:
        txt = f"« {x.split('-')[0]} » est une forme de « {a['lemma']} » ({mean})."
    else:
        return None
    cl = [c for c in a.get("clitics", []) if c in CLITIC_FR]
    if cl:
        txt += " Collé derrière : " + ", ".join(f"-{c} ({CLITIC_FR[c]})" for c in cl) + "."
    return txt + (" Tu veux la conjugaison complète ?" if a["pos"] == "verbe" else " Tu veux un exemple avec ce mot ?")


_FR_INDEX: dict[str, list[Item]] | None = None
_KAB_INDEX: dict[str, list[Item]] | None = None


def _indexes():
    global _FR_INDEX, _KAB_INDEX
    if _FR_INDEX is None or len(kb.items) != getattr(_indexes, "_n", -1):
        fr_idx: dict[str, list[Item]] = {}
        kab_idx: dict[str, list[Item]] = {}
        for it in kb.items.values():
            if it.status == "rejected" or it.kind not in ("word", "pair"):
                continue
            if it.status == "pending" and not it.confident:
                continue  # paire mal alignée probable : jamais citée
            if it.kind == "word":
                for k in _fr_keys(it.fr):
                    fr_idx.setdefault(k, []).append(it)
            kab_idx.setdefault(_key(it.kab), []).append(it)
        _FR_INDEX, _KAB_INDEX = fr_idx, kab_idx
        _indexes._n = len(kb.items)  # type: ignore[attr-defined]
    return _FR_INDEX, _KAB_INDEX


def _best(items: list[Item]) -> Item:
    # Programme d'abord, puis mots validés, puis poids du domaine ; un mot court plutôt qu'une phrase.
    return max(items, key=lambda it: (*_rank(it), it.kind == "word", -len(it.kab)))


def lookup_fr(x: str) -> Item | None:
    fr_idx, _ = _indexes()
    key = re.sub(ARTICLES, "", fold(_strip(x))).strip()
    found = fr_idx.get(key) or (fr_idx.get(key[:-1]) if key.endswith(("s", "x")) else None)
    if not found:
        return None
    # Les sens appris automatiquement ne passent qu'en dernier recours
    found = [it for it in found if it.domain != "appris"] or found
    # D'abord les entrées dont c'est le sens principal (« allen — yeux » avant « tiṭ — yeux, trou »)
    main = [it for it in found if _fr_keys(it.fr)[:1] == [key] and len(_fr_keys(it.fr)) == 1]
    return _best(main or found)


def lookup_kab(x: str) -> Item | None:
    _, kab_idx = _indexes()
    found = kab_idx.get(_key(_strip(x)))
    return _best(found) if found else None


def _kab(it: Item) -> str:
    """Forme à afficher : sans ponctuation finale, minuscule sauf nom propre ou phrase."""
    k = it.kab.strip().rstrip(" .!?")
    if it.kind == "word" and " " not in k and k[:1].isupper() and k[1:].islower() and it.domain not in ("prénoms", "lieux"):
        k = k.lower()
    return k


def _key(s: str) -> str:
    return re.sub(r"[\s.!?«»\"“”]+$", "", fold(s).strip(" «»\"“”"))


def _looks_plural(k: str) -> bool:
    return bool(re.fullmatch(r"i[^aeiu ]\w*(en|an|wen|awen)|ti\w+(in|atin)", k))


def _say(rng: random.Random, it: Item, asked: str) -> str:
    fr = _clean_fr(it.fr)
    k = _kab(it)
    if it.domain == "appris" and _looks_plural(k):
        fr += ", forme du pluriel"
    intro = rng.choice([
        f"On dit « {k} » ({fr.lower()}).",
        f"En kabyle : « {k} » ({fr.lower()}).",
        f"« {asked} » se dit « {k} ».",
    ])
    ask = rng.choice([
        "Essaie de l'employer dans une petite phrase, je te corrige.",
        "À toi : écris-le une fois pour le retenir.",
        "Tu veux un autre mot de la même famille ?",
    ])
    src = f" (Source : {it.source}.)" if _sources() and it.source and "Programme" not in it.source else ""
    return f"{intro}{src} {ask}" + (f"\n[[MOT: {it.kab}]]" if it.kind == "word" else "")


def _sources() -> bool:
    """Citer les ouvrages d'origine ? (réglage SHOW_SOURCES, désactivé sur le site public)"""
    return get_settings().show_sources


def _modern(k: str) -> str:
    """Sens moderne (traductions de logiciels / Tatoeba), en complément d'une source HCA."""
    if MORPH is None:
        return ""
    en = MORPH.meanings_en.get(k.lower())
    return f" Dans l'usage d'aujourd'hui, il désigne aussi « {en} » (en anglais)." if en else ""


def _short_src(src: str) -> str:
    s = src or ""
    if "Appris" in s:
        return "appris par Amusnaw sur des textes traduits, à valider"
    return re.split(r",| \(", s)[0].strip() or "base"


def other_senses(it: Item, n: int = 2) -> str:
    """Autres sens du même mot dans d'autres sources (homonymes, sens courant appris…)."""
    _, kab_idx = _indexes()
    seen = {fold(_clean_fr(it.fr)).rstrip(" .")}
    out = []
    for o in sorted(kab_idx.get(_key(it.kab), []), key=lambda o: _rank(o), reverse=True):
        if o is it or o.kind != "word":
            continue
        fr = _clean_fr(o.fr).rstrip(" .")
        if not fr or fold(fr) in seen or len(fr) > 60:
            continue
        seen.add(fold(fr))
        out.append(f"« {fr} » ({_short_src(o.source)})" if _sources() else
                   (f"« {fr} » (usage courant, à confirmer)" if o.domain == "appris" else f"« {fr} »"))
        if len(out) >= n:
            break
    return f" Il peut aussi vouloir dire {' ou '.join(out)}." if out else ""


def _mean(rng: random.Random, it: Item) -> str:
    fr = _clean_fr(it.fr).rstrip(" .")
    k = _kab(it)
    src = f" (Source : {it.source}.)" if _sources() and it.source and "Programme" not in it.source else ""
    if it.kind == "pair" or " " in k:
        return f"« {k} » veut dire : « {fr} ».{src} Tu veux qu'on regarde les mots un par un ?"
    ask = rng.choice(["Tu veux l'employer dans une phrase ?", "Tu veux un exercice avec ce mot ?"])
    # néologismes des glossaires littéraires : le sens a parfois évolué (aselkim : certificat → ordinateur)
    modern = _modern(k) if "glossaire" in (it.source or "").lower() else ""
    shown = fr if it.domain == "lieux" else fr.lower()
    return f"« {k} » veut dire « {shown} ».{src}{other_senses(it)}{modern} {ask}\n[[MOT: {it.kab}]]"


MISSING_FR = ("Je n'ai pas encore « {x} » dans ma base vérifiée, et je préfère ne pas l'inventer. "
              "Tu peux me demander un autre mot, ou on continue la leçon ?")
MISSING_KAB = ("Je ne trouve pas « {x} » dans ma base vérifiée, donc je ne vais pas deviner son sens. "
               "Vérifie l'orthographe (ɣ, ɛ, ḍ…) ou donne-moi la phrase où tu l'as vu.")
OFF_TOPIC = ("Je ne peux pas t'aider pour ça : je suis là uniquement pour le kabyle, sa culture et son "
             "histoire. On reprend ta leçon ?")
MEDICAL = ("Pour ta santé, demande plutôt à un médecin ou à un pharmacien : je ne donne pas de conseil "
           "médical. Par contre, je peux t'apprendre à dire les parties du corps en kabyle. On essaie ?")


def is_off_topic(message: str) -> str | None:
    """Renvoie la réponse fixe si la demande sort clairement du cadre."""
    m = _OFF_TOPIC.search(message)
    if not m:
        return None
    if re.search(r"(?:comment\s+(?:on\s+)?dit|en\s+kabyle|traduis|veut\s+dire)", message, re.I):
        return None  # « comment dit-on médicament ? » reste une question de langue
    word = fold(m.group(0))
    return MEDICAL if word.startswith(("medicament", "ordonnance", "posologie", "antibio", "quel traitement",
                                       "soigner")) else OFF_TOPIC


# Culture : les fiches vérifiées répondent elles-mêmes (le modèle inventait des faits sur Yennayer…)
_CULTURE = re.compile(r"\b(parle[- ]moi|raconte|c['’]est quoi|qu['’]est[- ]ce que|qui (?:était|est|étaient)|"
                      r"explique|histoire d|que sais[- ]tu|connais[- ]tu|dis[- ]moi)", re.I)
_GENERIC_TAGS = {"histoire", "village", "littérature", "langue", "artisanat", "société", "écriture", "identité",
                 "femmes", "poésie", "fête", "calendrier", "argent", "bijoux", "motifs", "olives", "résistance", "tizi",
                 "hca", "entraide", "alphabet"}


def capsule_reply(message: str) -> str | None:
    """« Parle-moi de Yennayer » : réponse tirée de la fiche culturelle vérifiée."""
    if not _CULTURE.search(message):
        return None
    m = f" {fold(message)} "
    for c in capsules():
        title = re.sub(r"^(?:le |la |les |l'|l’|une |un )", "", c["title"], flags=re.I)
        names = [title] + [t for t in c.get("tags", []) if t not in _GENERIC_TAGS and len(t) >= 4]
        if any(f" {fold(n)}" in m for n in names):
            t = c["title"]
            t = t[0].lower() + t[1:] if re.match(r"(?:Le|La|Les|L'|L’|Une|Un)\b", t) else t
            return (f"Avec plaisir, voici l'essentiel sur {t}. "
                    "Tu veux apprendre les mots kabyles qui vont avec ?\n[[CAPSULE: " + c["id"] + "]]")
    return None


def direct_reply(message: str, language: str = "fr") -> str | None:
    """Réponse exacte écrite par le serveur, ou None pour laisser parler le modèle."""
    msg = message.strip()
    if language != "fr":
        return None  # modèles de réponse en français seulement pour l'instant
    rng = random.Random(msg)
    off = is_off_topic(msg)
    if off:
        return off
    cap = capsule_reply(msg)
    if cap:
        return cap
    m = _CONJ.search(msg)
    if m:
        x = _strip(m.group("x"))
        x = re.sub(r"^(?:le\s+verbe|au\s+\w+)\s+", "", x, flags=re.I)
        verb = conjugation.find_verb(x, _verbs_path()) or conjugation.find_verb(x.split()[0], _verbs_path())
        if verb:
            return conjugation.render(verb, sources=_sources()) + "\n\nÀ toi : écris une phrase avec « ad " + \
                conjugation.conjugate(verb)["aor"]["1sg"] + " » (je vais …)."
        return (f"Je n'ai pas encore le verbe « {x} » dans mes tableaux vérifiés. Je peux te conjuguer par "
                "exemple : aru (écrire), ečč (manger), ini (dire), issin (savoir), ɣer (lire), ruḥ (aller). "
                "Lequel veux-tu ?")
    mm = _MEANING.match(msg)
    if mm:  # « Que veut dire X ? » : le dictionnaire d'abord, la fiche de grammaire ensuite
        x = _strip(mm.group("x"))
        it = lookup_kab(x)
        if it:
            return _mean(rng, it) if _key(it.kab) == _key(x) or it.kind == "pair" else _say(rng, it, x)
        if len(x.split()) == 1 and (ex := explain_form(x)):
            return ex
        en = MORPH.meanings_en.get(_strip(x).lower()) if MORPH is not None else None
        if en:
            return (f"Je n'ai pas encore le sens de « {_strip(x)} » vérifié en français. "
                    f"En anglais, il correspond à « {en} ». Tu veux un autre mot ?")
    if _QUESTION.search(msg) and not _HOW_SAY.match(msg):
        n = grammar_note(msg)
        if n:
            return f"{n['title']}\n\n{n['text']}\n\n{n['question']}"
    for rx, kind in ((_HOW_SAY, "fr"), (_TRANSLATE, "fr"), (_MEANING, "kab")):
        m = rx.match(msg)
        if not m:
            continue
        x = _strip(m.group("x"))
        if not x or len(x.split()) > 6:
            return None
        if kind == "fr":
            it = lookup_fr(x)
            if it:
                return _say(rng, it, x)
            # « Traduis : Je m'appelle Koceila » → phrase : laisser le modèle (références en contexte)
            if len(x.split()) > 3 or rx is _TRANSLATE:
                return None
            return MISSING_FR.format(x=x)
        it = lookup_kab(x)
        if it:
            return _mean(rng, it) if _key(it.kab) == _key(x) or it.kind == "pair" else _say(rng, it, x)
        if len(x.split()) == 1 and (ex := explain_form(x)):
            return ex
        it = lookup_fr(x)
        if it:
            return _say(rng, it, x)
        if len(x.split()) > 3:
            return None
        return MISSING_KAB.format(x=x)
    return None


_QUESTION = re.compile(r"\b(pourquoi|comment|explique|expliquer|règle|regle|c['’]est quoi|quelle? différence|"
                       r"ça sert|sert à quoi|veut dire quoi|on met|on écrit|on ecrit)\b|\?", re.I)


def _notes() -> list[dict]:
    try:
        import json
        from pathlib import Path
        return json.loads(Path(str(get_settings().content_dir) + "/grammar_notes.json").read_text("utf-8"))["notes"]
    except (OSError, ValueError, KeyError):
        return []


def grammar_note(message: str) -> dict | None:
    for n in _notes():
        if any(re.search(t, message, re.I) for t in n["triggers"]):
            return n
    return None


def _verbs_path() -> str:
    return str(get_settings().content_dir) + "/verbs.json"


def verb_hints(message: str) -> str:
    """Formes exactes des verbes cités dans le message (pour que le prof ne conjugue pas lui-même)."""
    path = _verbs_path()
    words = set(re.findall(r"[\w’'-]+", message.lower()))
    lines = []
    for w in words:
        v = conjugation.find_verb(w, path)
        if v and len(w) > 1 and v["lemma"] not in {ln.split("«")[1].split("»")[0].strip() for ln in lines}:
            t = conjugation.conjugate(v)
            lines.append(f"- « {v['lemma']} » ({v['fr']}) : ad {t['aor']['1sg']} (je vais …), "
                         f"{t['pret']['1sg']} (j'ai …), {t['int']['1sg'] if 'int' in t else ''} (je … d'habitude), "
                         f"ur {t['neg']['1sg']} ara (je n'ai pas …)")
        if len(lines) >= 2:
            break
    return ("Formes verbales exactes (à recopier, ne conjugue rien d'autre) :\n" + "\n".join(lines)) if lines else ""
