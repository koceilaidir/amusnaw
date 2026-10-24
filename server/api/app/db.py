import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, UniqueConstraint, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from .config import get_settings

_settings = get_settings()
# Garde-fous : une requête n'attend jamais un verrou plus de 10 s, et une transaction
# oubliée est fermée au bout de 5 min (sinon tout le serveur peut rester bloqué).
_pg = {"options": "-c lock_timeout=10000 -c idle_in_transaction_session_timeout=300000"}
engine = create_engine(_settings.database_url, pool_pre_ping=True,
                       connect_args=_pg if _settings.database_url.startswith("postgresql") else {})
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("provider", "provider_sub"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    provider: Mapped[str] = mapped_column(String(16))  # google | apple | email
    provider_sub: Mapped[str] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    interface_language: Mapped[str] = mapped_column(String(8), default="en")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class LearnerProfile(Base):
    """Ce que le prof sait de l'apprenant (niveau, objectifs, vécu, erreurs)."""

    __tablename__ = "learner_profiles"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    level: Mapped[str] = mapped_column(String(4), default="a1")
    goals: Mapped[list] = mapped_column(JSON, default=list)
    background: Mapped[str] = mapped_column(Text, default="")
    frequent_errors: Mapped[dict] = mapped_column(JSON, default=dict)
    last_session_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ChatMessage(Base):
    """Historique des échanges : sert au suivi et, après relecture par un
    linguiste, aux futurs entraînements de nos propres modèles."""

    __tablename__ = "chat_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(12))  # user | assistant
    content: Mapped[str] = mapped_column(Text)
    off_topic: Mapped[bool] = mapped_column(default=False)
    model: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class LearnedWord(Base):
    """Un mot kabyle rencontré par l'élève.

    introduced_at : premier jour où le prof (ou un exercice) le lui a montré.
    mastered_at   : premier jour où l'élève l'a employé LUI-MÊME, un autre jour
                    que celui où il l'a découvert → il compte comme « appris ».
    """

    __tablename__ = "learned_words"
    __table_args__ = (UniqueConstraint("user_id", "word_key"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    word_key: Mapped[str] = mapped_column(String(80))  # forme normalisée (sans points, ɣ→g…)
    display: Mapped[str] = mapped_column(String(80))   # forme écrite à montrer
    source: Mapped[str] = mapped_column(String(12), default="tutor")  # tutor | exercise
    introduced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    mastered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SavedConversation(Base):
    """Discussion enregistrée (telle que l'app l'affiche), pour la retrouver sur
    un autre appareil. client_id = identifiant donné par l'app."""

    __tablename__ = "conversations"
    __table_args__ = (UniqueConstraint("user_id", "client_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    client_id: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(200), default="")
    messages: Mapped[list] = mapped_column(JSON, default=list)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class QaReview(Base):
    """Question libre d'un élève et réponse du modèle, SANS lien avec le compte
    (anonyme) : relues sur /review, les réponses corrigées servent à entraîner le prof."""

    __tablename__ = "qa_reviews"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text)
    model: Mapped[str] = mapped_column(String(80), default="")
    status: Mapped[str] = mapped_column(String(10), default="pending")  # pending | ok | fixed | rejected
    fixed: Mapped[str] = mapped_column(Text, default="")
    # le prof n'a pas su répondre (réponse retenue, l'élève a reçu « je ne sais pas encore »)
    unknown: Mapped[bool] = mapped_column(default=False)
    reviewer: Mapped[str] = mapped_column(String(80), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Review(Base):
    """Décision du linguiste sur une entrée de la base (mot ou paire)."""

    __tablename__ = "reviews"

    item_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    status: Mapped[str] = mapped_column(String(10))  # ok | fixed | rejected
    kab: Mapped[str] = mapped_column(Text)
    fr: Mapped[str] = mapped_column(Text)
    reviewer: Mapped[str] = mapped_column(String(80), default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


def init_db() -> None:
    Base.metadata.create_all(engine)
    # petites migrations (colonnes ajoutées après la création des tables)
    if engine.dialect.name == "postgresql":
        from sqlalchemy import text  # noqa: PLC0415
        with engine.begin() as con:
            con.execute(text("ALTER TABLE qa_reviews ADD COLUMN IF NOT EXISTS unknown BOOLEAN DEFAULT FALSE"))


def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
