"""Photo → mots kabyles, sans risque pour le kabyle.

1. Un modèle de vision open source (Ollama, par défaut qwen2.5vl:3b) regarde la photo et
   donne seulement les NOMS FRANÇAIS des objets visibles (JSON).
2. Le serveur cherche chaque nom dans la base kabyle vérifiée (router.lookup_fr).
   Le modèle n'écrit jamais de kabyle ; un objet sans mot vérifié est dit honnêtement
   et part en relecture.

La photo n'est jamais enregistrée : réduite en mémoire, envoyée au modèle, oubliée.
"""
import base64
import io
import json
import random
import re
from collections import Counter

import httpx

from . import router, tutor
from .config import get_settings
from .knowledge import Item, fold, kb

MAX_SIDE = 768        # pixels : assez pour reconnaître, peu de calcul sur processeur
MAX_OBJECTS = 6

PROMPT = (
    "Regarde cette photo. Liste les objets, animaux, plantes, aliments, vêtements, parties du corps ou "
    "éléments de paysage bien visibles, du plus important au moins important (6 au maximum).\n"
    "Pour chacun, donne le nom commun en français, au singulier, sans article, sans couleur ni marque, "
    "et un ou deux synonymes français plus simples si le mot est rare.\n"
    "Réponds uniquement en JSON, exactement sous cette forme :\n"
    '{"objets": [{"nom": "chaise", "synonymes": ["siège"]}, {"nom": "tasse", "synonymes": ["bol"]}]}\n'
    'Si la photo est floue ou vide, réponds {"objets": []}.'
)


def shrink(raw: bytes) -> bytes:
    """Réduit la photo (et retire ses métadonnées : lieu, appareil…). Lève ValueError si ce n'est pas une image."""
    from PIL import Image, ImageOps  # noqa: PLC0415

    try:
        img = Image.open(io.BytesIO(raw))
        img = ImageOps.exif_transpose(img)  # photo de téléphone : bon sens de lecture
    except Exception as e:  # noqa: BLE001
        raise ValueError("pas une image") from e
    img = img.convert("RGB")
    img.thumbnail((MAX_SIDE, MAX_SIDE))
    out = io.BytesIO()
    img.save(out, "JPEG", quality=85)
    return out.getvalue()


def _parse(text: str) -> list[list[str]]:
    """[["chaise", "siège"], ["tasse", "bol"]] — tolérant aux petites erreurs de JSON."""
    m = re.search(r"\{[\s\S]*\}", text or "")
    try:
        data = json.loads(m.group(0)) if m else {}
    except json.JSONDecodeError:
        data = {}
    out: list[list[str]] = []
    for o in (data.get("objets") or data.get("objects") or [])[:MAX_OBJECTS]:
        if isinstance(o, str):
            names = [o]
        elif isinstance(o, dict):
            names = [o.get("nom") or o.get("name") or ""] + list(o.get("synonymes") or o.get("synonyms") or [])
        else:
            continue
        names = [re.sub(r"^(?:une?|les?|la|l['’]|des)\s+", "", str(n).strip().lower()) for n in names]
        names = [n for n in names if n and len(n) <= 40]
        if names and all(names[0] != x[0] for x in out):
            out.append(names)
    return out


async def objects(jpeg: bytes) -> list[list[str]]:
    """Noms français des objets de la photo (avec synonymes). Lève une exception si le modèle ne répond pas."""
    url = tutor._ollama_url()  # noqa: SLF001
    if not url:
        raise RuntimeError("Ollama non configuré")
    s = get_settings()
    async with httpx.AsyncClient(timeout=httpx.Timeout(s.vision_timeout, connect=5)) as client:
        r = await client.post(f"{url}/api/chat", json={
            "model": s.vision_model, "stream": False, "format": "json",
            # libère la mémoire après quelques minutes sans photo (le serveur n'a que 8 Go)
            "keep_alive": s.vision_keep_alive,
            "messages": [{"role": "user", "content": PROMPT, "images": [base64.b64encode(jpeg).decode()]}],
            "options": {"temperature": 0.1, "num_predict": 200, "num_ctx": 4096},
        })
        r.raise_for_status()
        text = r.json().get("message", {}).get("content", "")
    print(f"[vision] {text[:200]!r}", flush=True)
    return _parse(text)


# Pour une photo, le mot de tous les jours d'abord (akursi plutôt que le néologisme tasɣimt)
_EVERYDAY = {"programme": 0, "vocabulaire de base": 1, "corps humain": 1, "animaux": 1, "animaux marins": 1,
             "général": 2, "sciences de la terre": 2, "santé": 3, "expressions": 3, "contes": 3, "tatoeba": 3,
             "appris": 4, "mots nouveaux": 5}
_attest: Counter | None = None


def _attested(k: str) -> int:
    """Nombre d'entrées de la base où ce mot kabyle apparaît (forme courante > variante rare)."""
    global _attest
    if _attest is None or _attest.get("__n__") != len(kb.items):
        c = Counter(fold(w) for it in kb.items.values() for w in re.findall(r"[^\W\d_]+", it.kab))
        c["__n__"] = len(kb.items)
        _attest = c
    return _attest.get(fold(k), 0)


def word_for(name: str) -> Item | None:
    """Le mot kabyle vérifié le plus courant pour un nom français, ou None."""
    fr_idx, _ = router._indexes()  # noqa: SLF001
    key = re.sub(router.ARTICLES, "", fold(name)).strip()
    found = fr_idx.get(key) or (fr_idx.get(key[:-1]) if key.endswith(("s", "x")) else None) or []
    ok = [it for it in found
          if not re.search(r"[A-Z]{2,}|\d|[()]", it.kab) and len(it.kab.split()) <= 3
          and not (it.domain == "appris" and router._looks_plural(fold(it.kab)))]  # noqa: SLF001
    if not ok:
        return None
    def rank(it: Item) -> float:  # le tableau de synonymes .docx mélange les parlers : après l'usage courant
        return 4.5 if (it.source or "").startswith("Dictionnaire français-berbère") else _EVERYDAY.get(it.domain, 6)
    return min(ok, key=lambda it: (rank(it), -_attested(router._kab(it)),  # noqa: SLF001
                                   len(it.kab)))


def reply(found_names: list[list[str]], seed: str) -> tuple[str, list[str]]:
    """Réponse du prof écrite par le serveur, et les noms français sans mot vérifié (pour la relecture)."""
    rng = random.Random(seed)
    found: list[tuple[str, str]] = []
    missing: list[str] = []
    seen_kab: set[str] = set()
    for names in found_names:
        it = next((x for x in (word_for(n) for n in names) if x), None)
        if it is None:
            missing.append(names[0])
            continue
        k = router._kab(it)  # noqa: SLF001
        if k.lower() in seen_kab:
            continue
        seen_kab.add(k.lower())
        found.append((k, names[0]))
    if not found and not missing:
        return ("Je n'arrive pas à reconnaître clairement ce qu'il y a sur cette photo. "
                "Essaie avec une photo plus nette, l'objet bien au centre et assez de lumière."), []
    lines = []
    if found:
        lines.append(rng.choice(["Sur ta photo, je vois :", "Voici ce que je reconnais sur ta photo :",
                                 "Belle photo ! J'y vois :"]))
        lines += [f"- « {k} » : {fr}" for k, fr in found]
    if missing:
        names = ", ".join(f"« {m} »" for m in missing)
        if found:
            lines.append(f"\nJe vois aussi {names}, mais je n'ai pas encore le mot kabyle vérifié. "
                         "Je l'ai noté : un kabylophone va le vérifier.")
        else:
            lines.append(f"Je reconnais {names}, mais je n'ai pas encore le mot kabyle vérifié. "
                         "Je l'ai noté : un kabylophone va le vérifier, et je saurai te le dire la prochaine fois.")
    if found:
        k = found[0][0]
        lines.append("\n" + rng.choice([
            f"À toi : écris « {k} » une fois pour le retenir.",
            f"Essaie d'employer « {k} » dans une petite phrase, je te corrige.",
            "Lequel veux-tu retenir ? Écris-le une fois, je te corrige.",
        ]))
    text = "\n".join(lines)
    text += "".join(f"\n[[MOT: {k}]]" for k, _ in found[:2])  # cartes mot (kabyle vérifié, tifinagh)
    return text, missing
