"""Le prof : construit le prompt, garde la conversation sur la langue et
la culture kabyles, et appelle le modèle (tout serveur compatible OpenAI :
Ollama, vLLM avec notre propre modèle, ou une API)."""

import json
import re
from pathlib import Path

import httpx

from .config import get_settings
from .db import LearnerProfile, User

# Réponse fixe quand la demande sort du cadre (code, devoirs d'autres
# matières, etc.). Le prompt système applique la même règle pour les cas
# que ce filtre ne voit pas.
OFF_TOPIC_REPLY = {
    "en": "I'm only here for Kabyle — the language, its culture and its history — so I'll leave that to others. Shall we get back to your lesson?",
    "fr": "Je suis là uniquement pour le kabyle — la langue, sa culture et son histoire — je laisse donc ça à d'autres. On reprend ta leçon ?",
    "ar": "أنا هنا فقط من أجل القبائلية — اللغة وثقافتها وتاريخها — لذا سأترك هذا لغيري. هل نعود إلى درسك؟",
    "es": "Solo estoy aquí para el cabilio — la lengua, su cultura y su historia —, así que eso lo dejo para otros. ¿Volvemos a tu lección?",
    "de": "Ich bin nur für Kabylisch da — die Sprache, ihre Kultur und Geschichte —, das überlasse ich also anderen. Machen wir mit deiner Lektion weiter?",
}

# Signaux évidents de demande hors sujet (code, programmation).
_CODE_SNIPPET = r"```|\b(def |console\.log|public static|select .+ from)\b"
_TECH_WORDS = r"\b(python|javascript|typescript|java|c\+\+|php|sql|html|css|flutter|dart|api|bug)\b"
_BUILD_VERBS = r"\b(write|écri\w*|ecri\w*|cod\w*|program\w*|debug\w*|débug\w*|développ\w*|develop\w*|build|crée|créer|make)\b"
_BUILD_NOUNS = r"\b(script|code|program|programme|logiciel|software|app|application|site|fonction|function)s?\b"


# Une question de vocabulaire (« comment dit-on 'logiciel' en kabyle ? ») reste dans le sujet.
_LANGUAGE_QUESTION = r"\b(say|translate|word for|dire|dit-on|traduire|traduction|kabyle|kabyl|taqbaylit|tamazight)\b"


def is_obviously_off_topic(message: str) -> bool:
    text = message.lower()
    if re.search(_LANGUAGE_QUESTION, text) and "```" not in text:
        return False
    if re.search(_CODE_SNIPPET, text):
        return True
    has_noun = re.search(_BUILD_NOUNS, text) is not None
    return has_noun and (re.search(_TECH_WORDS, text) is not None
                         or re.search(_BUILD_VERBS, text) is not None)


def off_topic_reply(language: str) -> str:
    return OFF_TOPIC_REPLY.get(language, OFF_TOPIC_REPLY["en"])


def build_system_prompt(user: User, profile: LearnerProfile, *, days_away: int,
                        session_plan: str, references: str,
                        words_to_reuse: list[str] | None = None) -> str:
    template = (Path(get_settings().prompts_dir) / "tutor_system_prompt.md").read_text("utf-8")
    body = template.split("---", 1)[-1]
    values = {
        "name": user.name or "",
        "interface_language": user.interface_language,
        "level": profile.level.upper(),
        "goals": ", ".join(profile.goals) or "unknown yet",
        "background": profile.background or "unknown yet",
        "frequent_errors": ", ".join(profile.frequent_errors) or "none yet",
        "days_away": str(days_away),
        "session_plan": session_plan,
        "validated_lexicon_and_examples": references or "(none provided)",
        "words_to_reuse": ", ".join(words_to_reuse or []) or "(none yet)",
    }
    for key, val in values.items():
        body = body.replace("{{" + key + "}}", val)
    return body.strip()


async def stream_model(system: str, history: list[dict], message: str):
    """Génère la réponse morceau par morceau (format SSE compatible OpenAI)."""
    s = get_settings()
    messages = [{"role": "system", "content": system}, *history, {"role": "user", "content": message}]
    async with httpx.AsyncClient(timeout=httpx.Timeout(300, connect=10)) as client:
        async with client.stream(
            "POST", f"{s.llm_base_url}/chat/completions",
            headers={"Authorization": f"Bearer {s.llm_api_key}"},
            json={"model": s.llm_model, "messages": messages, "temperature": 0.4, "stream": True},
        ) as r:
            r.raise_for_status()
            async for line in r.aiter_lines():
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    delta = json.loads(data)["choices"][0]["delta"].get("content")
                except (ValueError, KeyError, IndexError):
                    continue
                if delta:
                    yield delta


async def ask_model(system: str, history: list[dict], message: str) -> str:
    s = get_settings()
    messages = [{"role": "system", "content": system}, *history, {"role": "user", "content": message}]
    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.post(
            f"{s.llm_base_url}/chat/completions",
            headers={"Authorization": f"Bearer {s.llm_api_key}"},
            json={"model": s.llm_model, "messages": messages, "temperature": 0.4},
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()
