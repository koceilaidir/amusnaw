"""Le prof « plus IA », sans risque pour le kabyle.

Le serveur fournit toujours le kabyle vérifié (mots, phrase, exercice de la leçon).
Le modèle n'écrit qu'une ou deux phrases EN FRANÇAIS autour : il réagit à ce que
l'élève vient de dire, fait le lien avec sa vie et ses objectifs, l'encourage.

Avant d'être montrée, cette phrase est contrôlée : aucun mot kabyle, aucune lettre
kabyle, pas de citation, longueur limitée. Au moindre doute (ou si le modèle est
lent), on garde simplement le texte écrit par le serveur.
"""
import re

import httpx

from . import tutor
from .config import get_settings
from .knowledge import fold, kb

TIMEOUT = 15  # secondes : au-delà, la leçon part sans la phrase du modèle

SYSTEM = (
    "Tu es Amusnaw, un professeur de kabyle chaleureux. Tu écris UNE ou DEUX phrases courtes, en français "
    "uniquement, pour accompagner l'étape de leçon qui va suivre (le serveur l'affichera juste après toi).\n"
    "Règles strictes :\n"
    "- Aucun mot kabyle, aucune traduction, aucune lettre comme ɣ, ɛ, ḍ.\n"
    "- Ne présente pas les mots de la leçon (le serveur s'en charge) et ne pose pas d'exercice.\n"
    "- Réagis d'abord à ce que l'élève vient d'écrire, si c'est autre chose qu'une simple demande de suite.\n"
    "- Tu peux faire le lien avec son objectif ou sa vie s'il les a donnés. Sinon, reste simple.\n"
    "- Tutoie l'élève. Pas d'emoji. Pas plus de 40 mots."
)

_KAB_LETTERS = re.compile(r"[ɣɛḍṭẓṛṣḥčǧƔƐḌṬẒṚṢḤČǦγε]")
# mots français très courants qui existent aussi en kabyle (ne pas les prendre pour du kabyle)
_FR_OK = {"a", "d", "i", "n", "s", "ad", "ma", "ur", "la", "le", "les", "de", "des", "et", "tu", "te", "ta", "ton",
          "tes", "un", "une", "en", "on", "au", "aux", "ce", "se", "sa", "son", "ses", "ne", "pas", "plus", "bien",
          "mais", "que", "qui", "dans", "pour", "avec", "sur", "par", "est", "es", "va", "vas", "il", "elle", "nous",
          "vous", "ils", "elles", "toi", "moi", "lui", "si", "ou", "tout", "tous", "fait", "faire", "dire", "mot",
          "mots", "leçon", "allez", "bravo", "super", "parfait", "aujourd'hui", "demain", "maison", "famille",
          "village", "ami", "amie", "temps", "jour", "soir", "matin", "envie", "chez", "comme", "très", "encore"}


def safe(text: str, lesson_kab: list[str]) -> str | None:
    """La phrase du modèle si elle est sûre, sinon None."""
    t = (text or "").strip().strip('"').strip()
    t = re.sub(r"\s+", " ", t)
    if not t or len(t) > 260 or len(t.split()) > 45:
        return None
    if _KAB_LETTERS.search(t) or re.search(r"[«»*\[\]#]", t) or "\n" in t:
        return None
    words = re.findall(r"[^\W\d_]+(?:[-'’][^\W\d_]+)*", t.lower())
    lesson = {fold(w) for k in lesson_kab for w in re.findall(r"[^\W\d_]+", k.lower())}
    for w in words:
        if w in _FR_OK:
            continue
        if fold(w) in lesson:  # un mot de la leçon : le serveur le présente lui-même
            return None
        # mot kabyle attesté qui n'a pas l'air français (pas d'accent français, pas de terminaison française)
        if len(w) >= 4 and fold(w) in kb.kab_vocab and not re.search(r"[éèêàùçôîâœ]|(?:tion|ment|eux|ais|ait|er|ez)$", w):
            return None
    if not re.search(r"[.!?…]$", t):
        t += "."
    return t


async def lesson_intro(*, name: str, message: str, history: list[dict], unit: dict | None,
                       new_words_fr: list[str], goals: list, background: str, days_away: int,
                       lesson_kab: list[str]) -> str | None:
    """Une ou deux phrases en français avant l'étape de leçon, ou None (on garde le texte du serveur)."""
    url = tutor._ollama_url()  # noqa: SLF001
    if not url:
        return None
    ctx = [
        f"Prénom de l'élève : {name or 'inconnu'}",
        f"Objectifs : {', '.join(goals) if goals else 'pas encore dits'}",
        f"Ce qu'on sait de lui : {background or 'rien de plus'}",
        f"Jours depuis la dernière séance : {days_away}",
        f"Unité en cours : {unit['title'] if unit else 'programme A1'}"
        + (f" (but : {unit.get('can_do')})" if unit and unit.get("can_do") else ""),
        f"Thème des mots qui vont être présentés (en français) : {', '.join(new_words_fr) or 'révision'}",
    ]
    recent = [f"{'Élève' if m['role'] == 'user' else 'Prof'} : {m['content'][:200]}" for m in history[-4:]]
    prompt = ("CONTEXTE\n" + "\n".join(ctx) + "\n\nDERNIERS ÉCHANGES\n" + ("\n".join(recent) or "(début)")
              + f"\n\nL'élève vient d'écrire : {message[:300]}\n\nÉcris ta phrase d'accompagnement.")
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(TIMEOUT, connect=5)) as client:
            r = await client.post(f"{url}/api/chat", json={
                "model": get_settings().llm_model, "stream": False, "keep_alive": -1,
                "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}],
                # même contexte que les vraies réponses (sinon Ollama recharge le modèle)
                "options": {**tutor.OLLAMA_OPTIONS, "num_predict": 80, "temperature": 0.7},
            })
            r.raise_for_status()
            text = r.json().get("message", {}).get("content", "")
    except Exception as e:  # noqa: BLE001 — lent ou indisponible : la leçon part sans
        print(f"[flavor] ignoré : {type(e).__name__}", flush=True)
        return None
    out = safe(text, lesson_kab)
    if out is None:
        print(f"[flavor] refusé : {text[:120]!r}", flush=True)
    return out
