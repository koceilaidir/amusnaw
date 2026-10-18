"""Leçon guidée : quand l'élève veut apprendre (« Apprendre », « on continue »,
« autre chose »…), le serveur fait avancer le programme A1 lui-même, deux mots
nouveaux à la fois, avec une phrase utile et un exercice. Tout vient du programme
vérifié : rien n'est inventé, rien ne se répète, et la réponse est immédiate.
Le modèle ne sert qu'à la conversation libre."""
import re

from . import content
from .knowledge import fold

NEXT = re.compile(
    r"\b(apprendre|apprends|continue|continuer|continuons|la suite|suivant|suivante|autre chose|"
    r"change|changer|nouveau|nouveaux|nouvelle|retenu|leçon|lecon|on avance|avancer|encore)\b", re.I)
NOT_NEXT = re.compile(r"\b(comment|que veut|veut dire|conjug|pourquoi|c'est quoi|traduis)\b", re.I)


def wants_next(message: str, intent: str | None) -> bool:
    if intent == "learn":
        return True
    m = message.strip()
    return len(m) <= 90 and bool(NEXT.search(m)) and not NOT_NEXT.search(m)


def step(seen: set[str], name: str = "") -> tuple[str, dict[str, str]]:
    """Réponse du prochain pas de la leçon + clés des mots présentés."""
    unit = content.current_unit(seen)
    if not unit:
        return "", {}
    words = unit["words"]
    new = [w for w in words if fold(w["kab"]) not in seen][:2]
    chunks = unit.get("chunks", [])
    done_before = sum(1 for w in words if fold(w["kab"]) in seen)
    lines = []
    if done_before == 0:
        lines.append(f"On commence l'unité **{unit['title']}**. {unit.get('can_do', '')}".strip())
    if new:
        lines.append("Deux mots nouveaux :" if len(new) > 1 else "Un mot nouveau :")
        lines += [f"- « {w['kab']} » : {w['fr']}" for w in new]
    else:  # tous les mots vus : révision de l'unité avant la suivante
        lines.append(f"Tu as vu tous les mots de l'unité **{unit['title']}**. Petite révision :")
        lines += [f"- « {w['kab']} » : {w['fr']}" for w in words]
    if chunks:
        c = chunks[(done_before // 2) % len(chunks)]
        lines.append(f"\nUne phrase à retenir : « {c['kab']} » — {c['fr']}")
    target = new[-1]["kab"] if new else words[0]["kab"]
    lines.append(f"\nÀ toi : écris une petite phrase avec « {target} », ou réponds à l'exercice ci-dessous. "
                 "Quand tu veux la suite, dis « continue ».")
    lines.append(f"[[MOT: {new[0]['kab'] if new else words[0]['kab']}]]")
    lines.append("[[EXERCICE]]")
    return "\n".join(lines), {fold(w["kab"]): w["kab"] for w in new}
