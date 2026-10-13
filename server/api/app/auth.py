"""Connexion Google / Apple : on vérifie le jeton d'identité signé par le
fournisseur, puis on émet notre propre jeton (JWT) pour l'app."""

from datetime import timedelta

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import get_settings
from .db import LearnerProfile, User, get_db, now

APPLE_ISSUER = "https://appleid.apple.com"
_apple_jwks = jwt.PyJWKClient(f"{APPLE_ISSUER}/auth/keys", cache_keys=True)
_bearer = HTTPBearer(auto_error=False)


def _unauthorized(msg: str = "Invalid credentials") -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=msg)


def verify_google(token: str) -> dict:
    audiences = get_settings().google_audiences
    try:
        claims = google_id_token.verify_oauth2_token(token, google_requests.Request())
    except ValueError as e:
        raise _unauthorized(f"Google token rejected: {e}") from e
    if claims.get("aud") not in audiences:
        raise _unauthorized("Google token audience not allowed")
    return claims


def verify_apple(token: str) -> dict:
    audiences = get_settings().apple_audiences
    try:
        key = _apple_jwks.get_signing_key_from_jwt(token).key
        return jwt.decode(token, key, algorithms=["RS256"], audience=audiences, issuer=APPLE_ISSUER)
    except jwt.PyJWTError as e:
        raise _unauthorized(f"Apple token rejected: {e}") from e


def upsert_user(db: Session, *, provider: str, sub: str, email: str | None,
                name: str | None, language: str) -> User:
    user = db.scalar(select(User).where(User.provider == provider, User.provider_sub == sub))
    if user is None:
        user = User(provider=provider, provider_sub=sub, email=email, name=name,
                    interface_language=language)
        db.add(user)
        db.flush()
        db.add(LearnerProfile(user_id=user.id))
    else:
        user.email = email or user.email
        user.name = name or user.name
    db.commit()
    return user


def issue_token(user: User) -> str:
    s = get_settings()
    payload = {"sub": user.id, "iat": now(), "exp": now() + timedelta(days=s.jwt_days)}
    return jwt.encode(payload, s.jwt_secret, algorithm="HS256")


def current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    if creds is None:
        raise _unauthorized("Missing token")
    try:
        payload = jwt.decode(creds.credentials, get_settings().jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError as e:
        raise _unauthorized("Invalid token") from e
    user = db.get(User, payload["sub"])
    if user is None:
        raise _unauthorized("Unknown user")
    return user
