"""Réponses apprises : les questions des élèves relues sur /review.

- Une question déjà relue (réponse validée ou corrigée) reçoit directement la bonne
  réponse, sans passer par le modèle : le prof « apprend » dès la relecture.
- Quand le modèle invente du kabyle ou dit qu'il ne sait pas, l'élève reçoit un
  « je ne sais pas encore » honnête et la question part en relecture.
"""
import re
import threading

from sqlalchemy import select

from .db import QaReview, SessionLocal
from .knowledge import fold

SORRY = ("Désolé, je ne connais pas encore la réponse, et je préfère ne pas l'inventer. "
         "J'ai noté ta question : un kabylophone va la vérifier, et je saurai te répondre la prochaine fois.")

# Le modèle lui-même dit qu'il ne sait pas
_DONT_KNOW = re.compile(r"je ne (?:connais|sais) pas|je n'ai pas (?:encore )?(?:ce mot|cette information|la réponse)|"
                        r"pas (?:encore )?dans ma base|je préfère ne pas (?:l')?inventer|je ne suis pas sûr", re.I)
_FILLER = {"stp", "svp", "s'il", "te", "plait", "plaît", "merci", "dis", "moi", "est", "ce", "que", "qu", "donc", "alors"}

_lock = threading.Lock()
_cache: list[tuple[set[str], str, str]] | None = None  # (mots de la question, question repliée, réponse)


def _key(q: str) -> str:
    return " ".join(w for w in re.findall(r"[^\W_]+", fold(q).replace("’", "'")) if w not in _FILLER)


def invalidate() -> None:
    global _cache
    with _lock:
        _cache = None


def _load() -> list[tuple[set[str], str, str]]:
    global _cache
    with _lock:
        if _cache is None:
            with SessionLocal() as db:
                rows = db.scalars(select(QaReview).where(QaReview.status.in_(("ok", "fixed")))).all()
                _cache = []
                for r in rows:
                    ans = (r.fixed or r.answer).strip()
                    k = _key(r.question)
                    if ans and k and ans != SORRY:
                        _cache.append((set(k.split()), k, ans))
        return _cache


def learned(question: str) -> str | None:
    """Réponse relue pour cette question (ou une question presque identique), sinon None."""
    k = _key(question)
    if not k:
        return None
    words = set(k.split())
    best, score = None, 0.0
    for ws, qk, ans in _load():
        if qk == k:
            return ans
        if len(ws) >= 3 and len(words) >= 3:
            j = len(ws & words) / len(ws | words)
            if j > score:
                best, score = ans, j
    return best if score >= 0.85 else None


# Réponses du serveur qui disent « je n'ai pas ça » (mot absent de la base, verbe inconnu…)
_MISSING = re.compile(r"pas encore « .+? » dans ma base|je ne trouve pas « .+? » dans ma base|"
                      r"pas encore le verbe|pas encore le sens", re.I)


def server_missing(reply: str) -> bool:
    return bool(_MISSING.search(reply))


def doubtful(reply: str, unverified: list[str]) -> bool:
    """Réponse à ne pas montrer : kabyle introuvable dans nos données, ou le modèle dit ne pas savoir."""
    return bool(unverified) or bool(_DONT_KNOW.search(reply))
