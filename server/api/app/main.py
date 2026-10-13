import json
import secrets
from contextlib import asynccontextmanager
from datetime import timezone
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import tutor
from .auth import current_user, issue_token, upsert_user, verify_apple, verify_google
from .config import get_settings
from .db import ChatMessage, LearnerProfile, Review, SessionLocal, User, get_db, init_db, now
from .knowledge import kb


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()  # TODO: passer à Alembic pour les migrations
    kb.load(get_settings().data_dir)
    with SessionLocal() as db:  # réapplique les décisions du linguiste
        for r in db.scalars(select(Review)):
            kb.apply_review(r.item_id, r.status, r.kab, r.fr)
    yield


app = FastAPI(title="Amusnaw API", version="0.2.0", lifespan=lifespan)


# ---------- Auth ----------

class GoogleLogin(BaseModel):
    id_token: str
    interface_language: str = "en"


class AppleLogin(BaseModel):
    identity_token: str
    name: str | None = None
    interface_language: str = "en"


class DevLogin(BaseModel):
    name: str = "Testeur"
    device_id: str = Field(min_length=4, max_length=80)
    interface_language: str = "en"


def _session(user: User) -> dict:
    return {
        "access_token": issue_token(user),
        "token_type": "bearer",
        "user": {"id": user.id, "name": user.name, "email": user.email,
                 "interface_language": user.interface_language},
    }


@app.get("/health")
def health():
    return {"ok": True, "knowledge_items": len(kb.items)}


@app.post("/auth/google")
def login_google(body: GoogleLogin, db: Session = Depends(get_db)):
    c = verify_google(body.id_token)
    user = upsert_user(db, provider="google", sub=c["sub"], email=c.get("email"),
                       name=c.get("name"), language=body.interface_language)
    return _session(user)


@app.post("/auth/apple")
def login_apple(body: AppleLogin, db: Session = Depends(get_db)):
    c = verify_apple(body.identity_token)
    user = upsert_user(db, provider="apple", sub=c["sub"], email=c.get("email"),
                       name=body.name, language=body.interface_language)
    return _session(user)


@app.post("/auth/dev")
def login_dev(body: DevLogin, db: Session = Depends(get_db)):
    """Connexion de test (DEV_LOGIN=true) : un compte par téléphone, sans Google/Apple."""
    if not get_settings().dev_login:
        raise HTTPException(404)
    user = upsert_user(db, provider="dev", sub=body.device_id, email=None,
                       name=body.name, language=body.interface_language)
    return _session(user)


@app.get("/me")
def me(user: User = Depends(current_user)):
    return _session(user)["user"]


class LanguageUpdate(BaseModel):
    interface_language: str = Field(min_length=2, max_length=8)


@app.patch("/me/language")
def set_language(body: LanguageUpdate, user: User = Depends(current_user),
                 db: Session = Depends(get_db)):
    user.interface_language = body.interface_language
    db.merge(user)
    db.commit()
    return {"interface_language": user.interface_language}


# ---------- Tutor ----------

class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


@app.post("/tutor/chat")
async def chat(body: ChatIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    profile = db.get(LearnerProfile, user.id) or LearnerProfile(user_id=user.id)

    if tutor.is_obviously_off_topic(body.message):
        reply, off_topic, model = tutor.off_topic_reply(user.interface_language), True, None
    else:
        recent = db.scalars(
            select(ChatMessage).where(ChatMessage.user_id == user.id)
            .order_by(ChatMessage.created_at.desc()).limit(12)
        ).all()
        history = [{"role": m.role, "content": m.content} for m in reversed(recent)]
        last = profile.last_session_at
        if last is not None and last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        days_away = (now() - last).days if last else 0
        # Le message + la dernière réponse du prof servent à chercher dans la base
        context = body.message + " " + (history[-1]["content"] if history else "")
        system = tutor.build_system_prompt(
            user, profile, days_away=days_away,
            session_plan="Getting to know the learner: level, goals, background.",
            references=kb.references_for(context),
        )
        try:
            reply = await tutor.ask_model(system, history, body.message)
        except Exception as e:  # modèle indisponible
            raise HTTPException(503, "Tutor is unavailable, try again shortly.") from e
        off_topic, model = False, get_settings().llm_model

    db.add_all([
        ChatMessage(user_id=user.id, role="user", content=body.message, off_topic=off_topic),
        ChatMessage(user_id=user.id, role="assistant", content=reply, off_topic=off_topic, model=model),
    ])
    profile.last_session_at = now()
    db.merge(profile)
    db.commit()
    return {"reply": reply, "off_topic": off_topic}


# ---------- Relecture par le linguiste ----------

def require_reviewer(x_review_token: str = Header(default="")) -> None:
    expected = get_settings().review_token
    if not expected or not secrets.compare_digest(x_review_token, expected):
        raise HTTPException(401, "Invalid review token")


@app.get("/review")
def review_page():
    return FileResponse(Path(__file__).parent / "static" / "review.html")


@app.get("/review/stats", dependencies=[Depends(require_reviewer)])
def review_stats():
    stats: dict[str, dict[str, int]] = {}
    for it in kb.items.values():
        s = stats.setdefault(it.kind, {"total": 0, "pending": 0, "ok": 0, "fixed": 0, "rejected": 0, "doubtful": 0})
        s["total"] += 1
        s[it.status] += 1
        if it.status == "pending" and not it.confident:
            s["doubtful"] += 1
    return stats


@app.get("/review/items", dependencies=[Depends(require_reviewer)])
def review_items(kind: str = Query("pair", pattern="^(pair|word)$"),
                 status: str = Query("pending", pattern="^(pending|ok|fixed|rejected)$"),
                 doubtful_first: bool = True, q: str = "", limit: int = Query(30, le=200)):
    items = [it for it in kb.items.values() if it.kind == kind and it.status == status]
    if q:
        ql = q.lower()
        items = [it for it in items if ql in it.kab.lower() or ql in it.fr.lower()]
    if doubtful_first:
        items.sort(key=lambda it: it.confident)
    return [{"id": it.id, "kab": it.kab, "fr": it.fr, "source": it.source,
             "confident": it.confident, "status": it.status} for it in items[:limit]]


class ReviewIn(BaseModel):
    status: str = Field(pattern="^(ok|fixed|rejected|pending)$")
    kab: str | None = None
    fr: str | None = None
    reviewer: str = ""


@app.post("/review/items/{item_id}", dependencies=[Depends(require_reviewer)])
def review_item(item_id: str, body: ReviewIn, db: Session = Depends(get_db)):
    it = kb.items.get(item_id)
    if not it:
        raise HTTPException(404)
    if body.status == "pending":
        row = db.get(Review, item_id)
        if row:
            db.delete(row)
        db.commit()
        it.status = "pending"
        return {"ok": True}
    kab = body.kab if body.status == "fixed" and body.kab else it.kab
    fr = body.fr if body.status == "fixed" and body.fr else it.fr
    db.merge(Review(item_id=item_id, status=body.status, kab=kab, fr=fr,
                    reviewer=body.reviewer, updated_at=now()))
    db.commit()
    kb.apply_review(item_id, body.status, kab, fr)
    return {"ok": True}


@app.get("/review/export.jsonl", dependencies=[Depends(require_reviewer)])
def review_export():
    """Paires et mots validés (ok + corrigés) : le jeu d'entraînement d'amusnaw-v1."""
    lines = [json.dumps({"kind": it.kind, "kab": it.kab, "fr": it.fr, "source": it.source,
                         "status": it.status}, ensure_ascii=False)
             for it in kb.items.values() if it.status in ("ok", "fixed")]
    return PlainTextResponse("\n".join(lines) + "\n", media_type="application/x-ndjson")
