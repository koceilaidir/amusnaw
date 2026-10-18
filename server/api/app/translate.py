"""Traduction français ↔ kabyle.

1. Mémoire de traduction : phrases déjà traduites par des humains (Tatoeba, livres
   bilingues). Une phrase identique est rendue telle quelle ; les phrases proches
   servent d'exemples.
2. Moteur de traduction NLLB-200 (Meta), qui tourne sur le VPS (service « mt »).
3. Les mots importants sont expliqués avec le dictionnaire.

Le petit modèle de conversation ne traduit jamais lui-même un long texte : il invente.
"""
import json
import re
import sqlite3
import threading
import unicodedata
from pathlib import Path

import httpx

from .config import get_settings
from .knowledge import fold, kb

# ---------- Demande de traduction ----------

_ASK = re.compile(r"\b(tradui\w*|traduction|translate|translation|tsuqel|suqel)\b", re.I)
# Ligne qui n'est que la demande (« est-ce que tu peux traduire ça ? »)
_ASK_LINE = re.compile(
    r"^\s*(?:et\s+)?(?:est[- ]ce\s+que\s+)?(?:tu\s+(?:peux|pourrais|sais)\s+|peux[- ]tu\s+|pourrais[- ]tu\s+|"
    r"merci\s+de\s+|stp\s+|s'il\s+te\s+pla[iî]t\s+)?(?:me\s+)?(?:tradui\w*|traduction|translate)\b[^:\n]{0,60}?"
    r"(?:\?|!|\.)?\s*$", re.I)
_QUOTED = re.compile(r"«\s*([^»]{3,})\s*»|\"([^\"]{3,})\"|“([^”]{3,})”")
_TO_FR = re.compile(r"\ben\s+fran[çc]ais\b", re.I)
_TO_KAB = re.compile(r"\ben\s+(?:kabyle|taqbaylit|tamazight|berb[èe]re)\b", re.I)


def is_request(message: str) -> bool:
    return bool(_ASK.search(message))


def extract(message: str) -> str:
    """Le texte à traduire dans un message qui le demande (vide si le texte n'y est pas)."""
    q = [next(g for g in m.groups() if g) for m in _QUOTED.finditer(message)]
    if q and sum(len(x) for x in q) > len(message) * .3:
        return "\n".join(x.strip() for x in q)
    m = re.search(r"(?:tradui\w*|traduction)[^:\n]{0,40}:\s*(.+)", message, re.I | re.S)
    if m and len(m.group(1).split()) >= 2:
        return m.group(1).strip()
    lines = [ln for ln in message.splitlines()]
    kept = [ln for ln in lines if not (_ASK.search(ln) and (_ASK_LINE.match(ln) or len(ln) < 80))]
    text = "\n".join(kept).strip()
    if text and text != message.strip():
        return text
    # « traduis-moi bonjour, je m'appelle Koceila » sur une seule ligne
    m = re.search(r"(?:tradui\w*|traduction(?:\s+de)?)(.*)$", message, re.I | re.S)
    if m:
        rest = re.sub(_TO_KAB, "", re.sub(_TO_FR, "", m.group(1)))
        rest = re.sub(r"^[\s\-]*(?:moi|me)?\b", "", rest, flags=re.I)
        rest = re.sub(r"\b(?:ça|ca|cela|ceci|stp|svp|s'il te pla[iî]t|merci|please)\b", "", rest, flags=re.I)
        rest = rest.strip(" :?!.,")
        if rest:
            return rest
    return ""


# ---------- Langue du texte ----------

_KAB_LETTERS = re.compile(r"[ɣɛḍṭẓṛṣḥčǧƔƐḌṬẒṚṢḤČǦ]")
_KAB_WORDS = {"d", "ur", "ara", "deg", "di", "ɣer", "akked", "yiwen", "yiwet", "nekk", "kečč", "kemm", "nettat",
              "netta", "ad", "ay", "ayen", "acu", "anda", "amek", "ma", "i", "s", "n", "wa", "wagi", "tagi", "azul",
              "tanemmirt", "ih", "ala", "yella", "tella", "teɣ", "ɣef", "seg", "ger", "imi", "maca", "neɣ", "dima"}
_FR_WORDS = {"le", "la", "les", "de", "des", "du", "un", "une", "et", "je", "tu", "il", "elle", "nous", "vous",
             "est", "que", "qui", "pas", "ne", "pour", "dans", "sur", "avec", "mon", "ma", "mes", "ce", "cette",
             "au", "aux", "en", "son", "sa", "ses", "ai", "suis", "fait", "plus", "très", "tout"}


def language_of(text: str) -> str:
    words = re.findall(r"[^\W\d_]+", text.lower())
    if not words:
        return "fr"
    kab = sum(w in _KAB_WORDS for w in words) + 3 * len(_KAB_LETTERS.findall(text))
    fr = sum(w in _FR_WORDS for w in words) + 2 * len(re.findall(r"[éèêàùçôîœ]", text))
    return "kab" if kab > fr else "fr"


# ---------- Mémoire de traduction (SQLite FTS5) ----------

_TM_PATH = Path("/tmp/amusnaw_tm.sqlite")
_tm_lock = threading.Lock()
_tm_ready = False


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFC", s).lower().replace("’", "'")
    return " ".join(re.findall(r"[^\W_]+", s))


def _tm_rows(data_dir: Path):
    """Paires humaines : Tatoeba (CC BY 2.0 FR) et livres bilingues (paires jugées sûres)."""
    for name, src in (("tatoeba_fr.jsonl", "Tatoeba"), ("parallel_petit_prince.jsonl", "livre"),
                      ("parallel_feraoun.jsonl", "livre"), ("parallel_camus.jsonl", "livre")):
        p = data_dir / name
        if not p.exists():
            continue
        with p.open(encoding="utf-8") as f:
            for line in f:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if src == "livre" and not r.get("confident"):
                    continue
                fr, kab = (r.get("fr") or "").strip(), (r.get("kab") or "").strip()
                if fr and kab and len(fr) < 400 and len(kab) < 400:
                    yield fr, kab, src


def build_memory(data_dir: str | None = None, path: Path = _TM_PATH) -> int:
    """Construit l'index (quelques secondes, une fois au démarrage)."""
    global _tm_ready
    d = Path(data_dir or get_settings().data_dir)
    with _tm_lock:
        tmp = path.with_suffix(".tmp")
        tmp.unlink(missing_ok=True)
        con = sqlite3.connect(tmp)
        con.execute("CREATE VIRTUAL TABLE tm USING fts5(fr_n, kab_n, fr UNINDEXED, kab UNINDEXED, src UNINDEXED, "
                    "tokenize='unicode61 remove_diacritics 0')")
        n = 0
        seen = set()
        batch = []
        for fr, kab, src in _tm_rows(d):
            key = (_norm(fr), _norm(kab))
            if key in seen:
                continue
            seen.add(key)
            batch.append((key[0], key[1], fr, kab, src))
            if len(batch) >= 5000:
                con.executemany("INSERT INTO tm VALUES (?,?,?,?,?)", batch)
                n += len(batch)
                batch = []
        if batch:
            con.executemany("INSERT INTO tm VALUES (?,?,?,?,?)", batch)
            n += len(batch)
        con.commit()
        con.close()
        tmp.replace(path)
        _tm_ready = n > 0
    print(f"[traduction] mémoire : {n} paires humaines", flush=True)
    return n


def _fts_query(text: str) -> str:
    words = [w for w in _norm(text).split() if len(w) > 1][:24]
    return " OR ".join(f'"{w}"' for w in words)


def similar(text: str, src_lang: str, k: int = 3, exclude: str | None = None,
            path: Path = _TM_PATH) -> list[dict]:
    """Phrases proches déjà traduites par des humains, de la plus proche à la moins proche."""
    if not path.exists():
        return []
    q = _fts_query(text)
    if not q:
        return []
    col = "fr_n" if src_lang == "fr" else "kab_n"
    con = sqlite3.connect(path)
    try:
        rows = con.execute(f"SELECT fr, kab, src, bm25(tm) FROM tm WHERE {col} MATCH ? ORDER BY bm25(tm) LIMIT ?",
                           (f"{{{col}}}: ({q})", k + 3)).fetchall()
    except sqlite3.Error:
        return []
    finally:
        con.close()
    out = []
    for fr, kab, src, score in rows:
        if exclude and _norm(fr if src_lang == "fr" else kab) == _norm(exclude):
            continue
        out.append({"fr": fr, "kab": kab, "src": src, "score": -score})
    return out[:k]


def exact(text: str, src_lang: str, path: Path = _TM_PATH) -> dict | None:
    """Même phrase (à la ponctuation et aux majuscules près) déjà traduite par un humain."""
    want = _norm(text)
    for r in similar(text, src_lang, 5, path=path):
        if _norm(r["fr"] if src_lang == "fr" else r["kab"]) == want:
            return r
    return None


# ---------- Moteur NLLB ----------

NLLB = {"fr": "fra_Latn", "kab": "kab_Latn", "en": "eng_Latn"}


def _sentences(text: str) -> list[str]:
    """Découpe en phrases. Les vers d'un poème sont recollés jusqu'à la ponctuation forte."""
    flat = re.sub(r"\s*\n\s*", " ", text.strip())
    parts = re.split(r"(?<=[.!?…;:])\s+(?=[\"«“(—–-]?\s*\w)", flat)
    return [p.strip() for p in parts if p.strip()]


def _fix_letters(t: str) -> str:
    """NLLB écrit parfois les lettres kabyles avec leurs sosies grecs (ε, γ) : on remet les bonnes."""
    return t.replace("ε", "ɛ").replace("γ", "ɣ").replace("Ɛ", "Ɛ")


async def machine(sentences: list[str], src: str, tgt: str) -> list[str] | None:
    """Traduit une liste de phrases avec NLLB. None si le service n'est pas lancé."""
    url = get_settings().mt_url.rstrip("/")
    if not url or not sentences:
        return None
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(180, connect=5)) as client:
            r = await client.post(f"{url}/translate", json={
                "sentences": sentences, "src": NLLB[src], "tgt": NLLB[tgt]})
            r.raise_for_status()
            return [_fix_letters(t) for t in r.json()["translations"]]
    except Exception as e:  # noqa: BLE001 — service absent ou en panne : on le dit, sans planter
        print(f"[traduction] NLLB indisponible : {type(e).__name__}: {e}", flush=True)
        return None


async def translate_text(text: str, src: str, tgt: str) -> tuple[str, list[str]] | None:
    """Texte traduit + origine de chaque phrase (« humain » ou « machine »)."""
    sents = _sentences(text)
    if not sents:
        return None
    out: list[str | None] = [None] * len(sents)
    origin = ["machine"] * len(sents)
    for i, s in enumerate(sents):
        hit = exact(s, src)
        if hit:
            out[i] = hit["kab"] if tgt == "kab" else hit["fr"]
            origin[i] = "humain"
    todo = [i for i, x in enumerate(out) if x is None]
    if todo:
        res = await machine([sents[i] for i in todo], src, tgt)
        if res is None:
            return None
        for i, t in zip(todo, res):
            out[i] = t
    return " ".join(x or "" for x in out).strip(), origin


# ---------- Réponse ----------

def _keywords(kab_text: str, n: int = 4) -> list[tuple[str, str]]:
    """Mots kabyles du texte que le dictionnaire connaît, avec leur sens."""
    from . import router  # noqa: PLC0415 — import tardif (router importe beaucoup)
    out, seen = [], set()
    for k, form in kb.kabyle_words(kab_text).items():
        if k in seen:
            continue
        it = router.lookup_kab(form)
        if it and fold(it.kab) == k and it.fr:
            out.append((it.kab, it.fr.split(";")[0].split(",")[0].strip()))
            seen.add(k)
        if len(out) >= n:
            break
    return out


async def reply(text: str, language: str = "fr") -> str | None:
    """Réponse complète du prof pour une demande de traduction, ou None si on ne peut pas traduire ici."""
    text = text.strip()
    if not text:
        return ("Envoie-moi le texte à traduire, en français ou en kabyle, "
                "et je te donne la traduction avec les mots importants.")
    src = language_of(text)
    tgt = "fr" if src == "kab" else "kab"
    if len(text.split()) <= 3:  # un mot ou une expression : le dictionnaire vérifié d'abord
        from . import router  # noqa: PLC0415
        d = router.direct_reply(f"Traduis {text}" if src == "fr" else f"Que veut dire {text}", language)
        if d:
            return d
    res = await translate_text(text, src, tgt)
    if res is None:
        return None
    out, origin = res
    lines = [f"**{out}**"]
    kab_side = out if tgt == "kab" else text
    kw = _keywords(kab_side)
    if kw:
        lines += ["", "Mots à retenir :"] + [f"- « {k} » : {f}" for k, f in kw]
    if len(_sentences(text)) == 1 and origin[0] == "machine":
        near = [r for r in similar(text, src, 2) if r["score"] > 8]
        if near:
            r = near[0]
            lines += ["", "Une phrase proche, traduite par un humain :",
                      f"- {r['kab']}", f"  ({r['fr']})"]
    if all(o == "humain" for o in origin):
        lines += ["", "Cette traduction vient d'un humain : tu peux t'y fier."]
    else:
        lines += ["", "Traduction automatique : elle peut contenir des erreurs, vérifie les phrases importantes."]
    return "\n".join(lines)
