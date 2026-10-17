import json
import secrets
from contextlib import asynccontextmanager
from datetime import timezone
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import tutor
from .auth import current_user, issue_token, upsert_user, verify_apple, verify_google
from .config import get_settings
from .limits import chat_limit, signup_limit
from .db import (ChatMessage, LearnedWord, LearnerProfile, Review, SessionLocal, User, get_db,
                 init_db, now)
from .knowledge import kb
from . import content, learning, router


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()  # TODO: passer à Alembic pour les migrations
    kb.load(get_settings().data_dir, get_settings().content_dir)
    try:  # analyse des formes conjuguées / annexées (yeswa → sew, uqerru → aqerru)
        from .morph import Lemmatizer
        router.MORPH = Lemmatizer.load(get_settings().data_dir, get_settings().content_dir)
    except Exception as e:  # noqa: BLE001 — l'app marche sans
        print(f"[morph] non chargé : {e}", flush=True)
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
def login_dev(body: DevLogin, request: Request, db: Session = Depends(get_db)):
    """Connexion sans compte (DEV_LOGIN=true) : un compte par appareil, sans Google/Apple."""
    if not get_settings().dev_login:
        raise HTTPException(404)
    ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "?").split(",")[0]
    signup_limit.check(ip)
    user = upsert_user(db, provider="dev", sub=body.device_id, email=None,
                       name=body.name, language=body.interface_language)
    return _session(user)


@app.post("/auth/refresh")
def refresh(user: User = Depends(current_user)):
    """Renouvelle le jeton à chaque ouverture : l'élève reste connecté tant
    qu'il revient au moins une fois tous les `jwt_days` jours."""
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
    # Décalage horaire de l'élève en minutes (ex. +60 à Tizi-Ouzou) : sert à
    # savoir si un mot a été découvert « un autre jour ».
    tz_offset_minutes: int = Field(0, ge=-840, le=840)
    # Choix fait sur l'écran d'accueil : "learn" (apprendre) ou "talk" (discuter).
    intent: str | None = Field(None, max_length=16)


INTENT_HINTS = {
    "learn": "\n\nL'élève vient de choisir « Apprendre » : propose tout de suite une petite "
             "activité sur la leçon en cours et termine par [[EXERCICE]].",
    "talk": "\n\nL'élève vient de choisir « Discuter » : propose deux ou trois sujets de culture "
            "ou d'histoire kabyles (fêtes, village, chansons, personnages) et laisse-le choisir.",
}


def _prepare_turn(body: "ChatIn", user: User, db: Session):
    """Ce qui précède l'appel au modèle : mots réemployés, filtre, prompt."""
    profile = db.get(LearnerProfile, user.id) or LearnerProfile(user_id=user.id)
    tz = body.tz_offset_minutes
    # 1. L'élève a-t-il réemployé des mots découverts un jour précédent ?
    newly_learned = learning.check_reused(db, user.id, body.message, tz)
    if tutor.is_obviously_off_topic(body.message):
        return profile, newly_learned, None, None, None
    # 2. Réponse exacte écrite par le serveur (vocabulaire, conjugaison, hors sujet évident)
    direct = router.direct_reply(body.message, user.interface_language)
    if direct:
        return profile, newly_learned, None, None, direct
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
    # Unité du programme : la première dont l'élève n'a pas encore vu tous les mots.
    seen = set(db.scalars(select(LearnedWord.word_key).where(LearnedWord.user_id == user.id)))
    plan = content.session_plan(content.current_unit(seen))
    if not history:
        plan = ("Premier échange : fais connaissance (niveau, objectifs, vécu), puis propose "
                "la première activité.\n" + plan)
    system = tutor.build_system_prompt(
        user, profile, days_away=days_away,
        session_plan=plan,
        references="\n".join(x for x in (kb.references_for(context), router.verb_hints(body.message)) if x),
        words_to_reuse=learning.words_to_reuse(db, user.id, tz),
    )
    system += INTENT_HINTS.get(body.intent or "", "")
    return profile, newly_learned, system, history, None


def _finish_turn(db: Session, user: User, profile, message: str, reply: str,
                 off_topic: bool, newly_learned: list[str], intent: str | None = None,
                 system: str = "") -> dict:
    """Ce qui suit la réponse : blocs, mots découverts, historique, total."""
    model = None if off_topic else get_settings().llm_model
    reply, markers = content.strip_markers(reply)
    if intent == "learn" and not any(k in ("EXERCICE", "EXERCISE") for k, _ in markers):
        markers.append(("EXERCICE", ""))  # « Apprendre » donne toujours un exercice
    blocks = content.build_blocks(reply, markers, seed=f"{user.id}{len(reply)}") if not off_topic else []
    if not off_topic:
        # 2. Les mots kabyles employés par le prof sont « découverts » aujourd'hui.
        learning.introduce(db, user.id, kb.kabyle_words(reply), "tutor")
    db.add_all([
        ChatMessage(user_id=user.id, role="user", content=message, off_topic=off_topic),
        ChatMessage(user_id=user.id, role="assistant", content=reply, off_topic=off_topic, model=model),
    ])
    profile.last_session_at = now()
    db.merge(profile)
    db.commit()
    # Contrôle qualité : kabyle cité par le prof mais absent des références.
    unverified = [] if off_topic else content.unverified_kabyle(reply, system)
    if unverified:
        print(f"[tutor] kabyle non vérifié ({user.id}): {unverified}", flush=True)
    return {
        "unverified": unverified,
        "reply": reply,
        "off_topic": off_topic,
        "learned": {"new": newly_learned, "total": learning.total_learned(db, user.id)},
        "blocks": blocks,
    }


@app.post("/tutor/chat")
async def chat(body: ChatIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    chat_limit.check(str(user.id))
    profile, newly, system, history, direct = _prepare_turn(body, user, db)
    if direct:
        return _finish_turn(db, user, profile, body.message, direct, False, newly, body.intent, direct)
    if system is None:
        reply = tutor.off_topic_reply(user.interface_language)
        return _finish_turn(db, user, profile, body.message, reply, True, newly)
    try:
        reply = await tutor.ask_model(system, history, body.message)
    except Exception as e:  # modèle indisponible
        raise HTTPException(503, "Tutor is unavailable, try again shortly.") from e
    return _finish_turn(db, user, profile, body.message, reply, False, newly, body.intent, system)


@app.post("/tutor/chat/stream")
async def chat_stream(body: ChatIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    chat_limit.check(str(user.id))
    """Même chose que /tutor/chat, mais la réponse arrive mot par mot (SSE) :
      data: {"type": "delta", "text": "…"}      (plusieurs fois)
      data: {"type": "done", "reply": …, "off_topic": …, "learned": {…}}
      data: {"type": "error", "message": …}
    """
    profile, newly, system, history, direct = _prepare_turn(body, user, db)

    def event(obj: dict) -> str:
        return "data: " + json.dumps(obj, ensure_ascii=False) + "\n\n"

    async def gen():
        if direct:
            shown, _ = content.strip_markers(direct)
            yield event({"type": "delta", "text": shown})
            yield event({"type": "done", **_finish_turn(db, user, profile, body.message, direct, False, newly,
                                                         body.intent, direct)})
            return
        if system is None:
            reply = tutor.off_topic_reply(user.interface_language)
            yield event({"type": "delta", "text": reply})
            yield event({"type": "done", **_finish_turn(db, user, profile, body.message, reply, True, newly)})
            return
        parts: list[str] = []
        sent = 0  # caractères déjà envoyés ; on n'envoie jamais une balise [[…]]
        try:
            async for piece in tutor.stream_model(system, history, body.message):
                parts.append(piece)
                full = "".join(parts)
                cut = full.find("[[")
                safe = full if cut < 0 else full[:cut]
                if full.endswith("["):  # peut-être le début d'une balise
                    safe = safe[:-1] if cut < 0 else safe
                if len(safe) > sent:
                    yield event({"type": "delta", "text": safe[sent:]})
                    sent = len(safe)
        except Exception:
            yield event({"type": "error", "message": "Tutor is unavailable, try again shortly."})
            return
        reply = "".join(parts).strip()
        yield event({"type": "done", **_finish_turn(db, user, profile, body.message, reply, False, newly, body.intent, system)})

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.delete("/me")
def delete_me(user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Suppression du compte et de toutes ses données (exigé par Google et Apple)."""
    for model in (LearnedWord, ChatMessage, LearnerProfile):
        db.query(model).filter(model.user_id == user.id).delete()
    db.delete(db.get(User, user.id))
    db.commit()
    return {"deleted": True}


# ---------- Contenus (leçons, mot du jour, capsules) ----------

@app.get("/content/today")
def content_today(tz_offset_minutes: int = Query(0, ge=-840, le=840)):
    return content.today(learning.local_day(now(), tz_offset_minutes))


@app.get("/content/lessons")
def content_lessons():
    return content.lesson_summaries()


@app.get("/content/lessons/{lesson_id}")
def content_lesson(lesson_id: str):
    l = content.lesson(lesson_id)
    if not l:
        raise HTTPException(404)
    return l


@app.get("/content/capsules")
def content_capsules():
    return content.capsules()


@app.get("/privacy")
def privacy_page():
    html = (Path(__file__).parent / "static" / "privacy.html").read_text("utf-8")
    email = get_settings().contact_email.strip()
    if email:
        html = html.replace("[ADRESSE E-MAIL DE CONTACT]", f'<a href="mailto:{email}">{email}</a>')
    return HTMLResponse(html)


@app.get("/me/progress")
def my_progress(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return {"words_learned": learning.total_learned(db, user.id)}


class SeenIn(BaseModel):
    words: list[str] = Field(max_length=50)


@app.post("/learning/seen")
def words_seen(body: SeenIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Mots travaillés dans un exercice : découverts aujourd'hui, ils compteront
    comme appris quand l'élève les réemploiera dans une autre conversation."""
    words = {}
    for w in body.words:
        words.update(learning.tokens_of(w))
    learning.introduce(db, user.id, words, "exercise")
    db.commit()
    return {"ok": True}



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
