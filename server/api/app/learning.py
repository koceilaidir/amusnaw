"""Suivi des mots appris.

Règle pédagogique (rappel actif espacé) :
  1. Un mot est « découvert » quand le prof l'emploie dans une réponse, ou
     quand l'élève le travaille dans un exercice.
  2. Il devient « appris » quand l'élève l'emploie LUI-MÊME dans une
     conversation, un AUTRE JOUR que celui de sa découverte. Le répéter juste
     après l'avoir vu ne compte pas : c'est la mémoire à plus long terme qu'on
     récompense.
  3. À ce moment, l'app félicite l'élève et affiche le nouveau total.

Le « jour » est celui de l'élève (décalage horaire envoyé par l'app).
"""

import re
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .db import LearnedWord, now
from .knowledge import KAB_FUNCTION_WORDS, STOP, fold, kb


def local_day(dt: datetime, tz_offset_minutes: int) -> date:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (dt.astimezone(timezone.utc) + timedelta(minutes=tz_offset_minutes)).date()


def tokens_of(text: str) -> dict[str, str]:
    """Tous les mots d'un texte (hors mots-outils) : clé normalisée → forme écrite."""
    out = {}
    for w in re.findall(r"[^\W\d_]+", text):
        k = fold(w)
        if len(k) >= 3 and k not in STOP and k not in KAB_FUNCTION_WORDS:
            out[k] = w.lower()
    return out


def check_reused(db: Session, user_id: str, message: str, tz_offset_minutes: int) -> list[str]:
    """Mots découverts un jour précédent et que l'élève vient d'employer → appris."""
    words = tokens_of(message)
    if not words:
        return []
    today = local_day(now(), tz_offset_minutes)
    rows = db.scalars(select(LearnedWord).where(
        LearnedWord.user_id == user_id,
        LearnedWord.word_key.in_(list(words)),
        LearnedWord.mastered_at.is_(None),
    )).all()
    newly = []
    for row in rows:
        if local_day(row.introduced_at, tz_offset_minutes) < today:
            row.mastered_at = now()
            newly.append(row.display)
    return newly


def introduce(db: Session, user_id: str, words: dict[str, str], source: str = "tutor") -> None:
    """Enregistre les mots nouveaux pour l'élève (ceux déjà connus sont ignorés)."""
    if not words:
        return
    known = set(db.scalars(select(LearnedWord.word_key).where(
        LearnedWord.user_id == user_id, LearnedWord.word_key.in_(list(words)))))
    for key, display in words.items():
        if key not in known:
            db.add(LearnedWord(user_id=user_id, word_key=key, display=display, source=source))


def total_learned(db: Session, user_id: str) -> int:
    return db.scalar(select(func.count()).select_from(LearnedWord).where(
        LearnedWord.user_id == user_id, LearnedWord.mastered_at.is_not(None))) or 0


def words_to_reuse(db: Session, user_id: str, tz_offset_minutes: int, limit: int = 8) -> list[str]:
    """Mots découverts avant aujourd'hui et pas encore réemployés : le prof
    crée des occasions de les utiliser."""
    today = local_day(now(), tz_offset_minutes)
    rows = db.scalars(select(LearnedWord).where(
        LearnedWord.user_id == user_id, LearnedWord.mastered_at.is_(None),
    ).order_by(LearnedWord.introduced_at).limit(50)).all()
    return [r.display for r in rows if local_day(r.introduced_at, tz_offset_minutes) < today][:limit]
