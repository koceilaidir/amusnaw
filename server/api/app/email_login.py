"""Connexion par e-mail, sans mot de passe : l'élève reçoit un code à 6 chiffres
(envoyé par Brevo), le tape dans l'app, et il est connecté.

Réglages (.env) : BREVO_API_KEY, MAIL_FROM (adresse d'expédition validée chez
Brevo, sur ton nom de domaine), MAIL_FROM_NAME. Sans clé, la connexion par
e-mail est désactivée (l'app ne montre pas le bouton).
"""
import hashlib
import hmac
import re
import secrets
import time

import httpx
from fastapi import HTTPException

from .config import get_settings
from .limits import RateLimit

EMAIL_RE = re.compile(r"^[^@\s]{1,64}@[^@\s]+\.[a-z]{2,}$", re.I)
CODE_TTL = 15 * 60       # un code vaut 15 minutes
MAX_TRIES = 5            # 5 essais par code

_codes: dict[str, tuple[str, float, int]] = {}  # e-mail → (empreinte du code, expiration, essais)
per_email = RateLimit(5, 3600, "Trop de codes demandés pour cette adresse. Réessaie dans une heure.")
per_ip = RateLimit(20, 3600, "Trop de demandes depuis cette connexion. Réessaie plus tard.")

SUBJECT = {"fr": "Ton code Amusnaw : {code}", "en": "Your Amusnaw code: {code}"}
BODY = {
    "fr": ("Azul !\n\nVoici ton code pour te connecter à Amusnaw : {code}\n\n"
           "Il est valable 15 minutes. Si tu n'as rien demandé, ignore simplement ce message.\n\n— Amusnaw"),
    "en": ("Azul!\n\nHere is your code to sign in to Amusnaw: {code}\n\n"
           "It is valid for 15 minutes. If you didn't ask for it, just ignore this message.\n\n— Amusnaw"),
}


def enabled() -> bool:
    s = get_settings()
    return bool(s.brevo_api_key and s.mail_from)


def normalize(email: str) -> str:
    e = email.strip().lower()
    if not EMAIL_RE.match(e):
        raise HTTPException(422, "Adresse e-mail invalide.")
    return e


def _hash(email: str, code: str) -> str:
    return hmac.new(get_settings().jwt_secret.encode(), f"{email}:{code}".encode(), hashlib.sha256).hexdigest()


HTML_LINES = {
    "fr": ("Voici ton code pour te connecter à Amusnaw :",
           "Il est valable 15 minutes. Si tu n'as rien demandé, ignore simplement ce message."),
    "en": ("Here is your code to sign in to Amusnaw:",
           "It is valid for 15 minutes. If you didn't ask for it, just ignore this message."),
}


def _html(code: str, lang: str) -> str:
    intro, outro = HTML_LINES[lang]
    return f"""<div style="font-family:-apple-system,Segoe UI,Roboto,sans-serif;max-width:440px;margin:auto;padding:28px;color:#1d1b17">
<div style="background:#56662E;color:#F8F6F1;border-radius:14px;padding:18px 22px;font-size:20px;font-weight:600">amusnaw</div>
<p style="margin:22px 0 4px;font-size:16px">Azul !</p>
<p style="margin:0 0 12px;font-size:16px">{intro}</p>
<div style="font-size:34px;letter-spacing:8px;font-weight:700;background:#F1EEE6;border-radius:12px;padding:16px;text-align:center;margin:8px 0 18px">{code}</div>
<p style="color:#6b665c;font-size:14px">{outro}</p></div>"""


async def start(email: str, ip: str, lang: str = "fr") -> None:
    if not enabled():
        raise HTTPException(503, "La connexion par e-mail n'est pas encore activée.")
    email = normalize(email)
    per_ip.check(ip)
    per_email.check(email)
    code = f"{secrets.randbelow(1_000_000):06d}"
    _codes[email] = (_hash(email, code), time.time() + CODE_TTL, 0)
    lang = lang if lang in BODY else "en"
    text = BODY[lang].format(code=code)
    s = get_settings()
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.post("https://api.brevo.com/v3/smtp/email",
                                  headers={"api-key": s.brevo_api_key, "accept": "application/json"},
                                  json={"sender": {"email": s.mail_from, "name": s.mail_from_name},
                                        "to": [{"email": email}],
                                        "subject": SUBJECT[lang].format(code=code),
                                        "textContent": text,
                                        "htmlContent": _html(code, lang)})
            r.raise_for_status()
    except httpx.HTTPError as e:
        print(f"[e-mail] envoi impossible : {e}", flush=True)
        raise HTTPException(502, "L'e-mail n'a pas pu être envoyé. Réessaie dans un instant.") from e


def verify(email: str, code: str) -> str:
    """Renvoie l'adresse normalisée si le code est bon, sinon erreur 401."""
    email = normalize(email)
    entry = _codes.get(email)
    if not entry or entry[1] < time.time():
        _codes.pop(email, None)
        raise HTTPException(401, "Code expiré : demande un nouveau code.")
    digest, exp, tries = entry
    if tries >= MAX_TRIES:
        _codes.pop(email, None)
        raise HTTPException(401, "Trop d'essais : demande un nouveau code.")
    if not hmac.compare_digest(digest, _hash(email, code.strip())):
        _codes[email] = (digest, exp, tries + 1)
        raise HTTPException(401, "Code incorrect.")
    _codes.pop(email, None)
    return email
