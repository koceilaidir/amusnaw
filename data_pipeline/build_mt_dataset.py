"""Fabrique de données pour entraîner amusnaw-mt (traducteur français ↔ kabyle).

  python build_mt_dataset.py ../data ../data/mt

Produit dans ../data/mt :
  pairs_train.jsonl  paires HUMAINES nettoyées {"fr", "kab", "origin"}
  pairs_dev.jsonl    1 000 paires mises de côté pour suivre l'entraînement
  eval_set.jsonl     les 300 phrases du banc d'essai (jamais vues à l'entraînement)
  mono_kab.txt       vrai kabyle humain, une phrase par ligne, pour la rétro-traduction
  stats.json         combien de phrases viennent d'où
  amusnaw-mt-data.zip  tout ça, à envoyer sur Kaggle (jeu de données PRIVÉ)

Règles :
- Seulement du kabyle écrit par des humains (jamais de kabyle produit par une machine).
- Le livre de Bouamara (licence CC BY-NC-ND) est exclu : sa licence interdit l'entraînement.
- Les phrases du banc d'essai sont retirées partout, sinon le score serait truqué.
"""
import gzip
import hashlib
import json
import random
import re
import sys
import unicodedata
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "server" / "api"))

KAB_LETTERS = re.compile(r"[ɣɛḍṭẓṛṣḥčǧƔƐḌṬẒṚṢḤČǦ]")
KAB_WORDS = {"d", "ur", "ara", "deg", "di", "ɣer", "akked", "yiwen", "yiwet", "nekk", "kečč", "kemm", "netta",
             "nettat", "ad", "ayen", "acu", "anda", "amek", "ma", "wa", "ɣef", "seg", "ger", "imi", "maca", "neɣ",
             "yella", "tella", "ii", "i", "n", "s", "yettwa", "mačči", "akka", "dagi", "tura", "ass", "yiwen"}
FR_WORDS = {"le", "la", "les", "de", "des", "du", "un", "une", "et", "je", "tu", "il", "elle", "nous", "vous",
            "est", "que", "qui", "pas", "ne", "pour", "dans", "sur", "avec", "mon", "ce", "au", "aux", "en", "son"}
LETTER_FIX = str.maketrans({"ε": "ɛ", "γ": "ɣ", "’": "'", "‘": "'"})


def clean(s: str) -> str:
    s = unicodedata.normalize("NFC", (s or "").translate(LETTER_FIX))
    s = re.sub(r"\s+", " ", s).strip()
    return s.strip("\"“”«» ").strip()


def norm(s: str) -> str:
    s = unicodedata.normalize("NFC", s).lower().replace("’", "'")
    return " ".join(re.findall(r"[^\W_]+", s))


def key(s: str) -> str:
    return hashlib.sha1(norm(s).encode()).hexdigest()


def jsonl(path: Path):
    if not path.exists():
        print(f"  (absent) {path.name}")
        return
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as f:
        for line in f:
            try:
                yield json.loads(line)
            except ValueError:
                continue


def looks_kabyle(s: str) -> bool:
    w = re.findall(r"[^\W\d_]+", s.lower())
    if not w:
        return False
    kab = sum(x in KAB_WORDS for x in w) + 2 * len(KAB_LETTERS.findall(s))
    fr = sum(x in FR_WORDS for x in w)
    return kab >= 1 and kab > fr


def good_sentence(s: str, lo: int = 3, hi: int = 40) -> bool:
    n = len(s.split())
    if not lo <= n <= hi or len(s) > 400:
        return False
    if re.search(r"https?://|www\.|@|\d{4,}|[A-ZÉ]{5,}", s):  # liens, numéros, titres en majuscules
        return False
    letters = sum(c.isalpha() for c in s)
    return letters >= 0.6 * len(s)


def good_pair(fr: str, kab: str) -> bool:
    if not fr or not kab or norm(fr) == norm(kab):
        return False
    if not re.search(r"[^\W\d_]{2}", fr) or not re.search(r"[^\W\d_]{2}", kab):  # entrée abîmée (« : », « ( »…)
        return False
    a, b = len(fr), len(kab)
    if a > 400 or b > 400:
        return False
    return 0.4 <= (b + 5) / (a + 5) <= 2.5


def main(data: Path, out: Path):
    out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(7)
    from app import eval_translate  # noqa: PLC0415 — même tirage que le banc d'essai du serveur
    evals = eval_translate.eval_set(str(data))
    banned = {key(p["fr"]) for p in evals} | {key(p["kab"]) for p in evals}
    with (out / "eval_set.jsonl").open("w", encoding="utf-8") as f:
        for p in evals:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")

    # ---------- 1. Paires humaines ----------
    pairs, seen, stats = [], set(), {}

    def add(fr, kab, origin, words=False):
        fr, kab = clean(fr), clean(kab)
        if not good_pair(fr, kab) or key(fr) in banned or key(kab) in banned:
            return
        if not words and len(fr.split()) < 1:
            return
        k = (norm(fr), norm(kab))
        if k in seen:
            return
        seen.add(k)
        pairs.append({"fr": fr, "kab": kab, "origin": origin})
        stats[origin] = stats.get(origin, 0) + 1

    print("Paires humaines…")
    for r in jsonl(data / "tatoeba_fr.jsonl"):
        add(r.get("fr"), r.get("kab"), "tatoeba")
    for name in ("parallel_petit_prince", "parallel_feraoun", "parallel_camus"):
        for r in jsonl(data / f"{name}.jsonl"):
            if r.get("confident"):
                add(r.get("fr"), r.get("kab"), "livres")
    for r in jsonl(data / "contes_numidya.jsonl"):
        add(r.get("fr"), r.get("kab"), "contes")
    for r in jsonl(data / "externes" / "contes_numidya_train.jsonl"):
        add(r.get("fr"), r.get("kab"), "contes")
    for r in jsonl(data / "tinfaliyin.jsonl"):
        add(r.get("fr"), r.get("kab"), "expressions")
    # Mots du dictionnaire : premier sens seulement, entrées courtes (vocabulaire)
    for name in ("lexicon_tatrart", "lexicon_terre_animaux", "lexicon_corps_humain", "lexicon_glossaires_livres",
                 "lexicon_tinfaliyin", "glossaries", "lexicon_didactique", "lexicon"):
        for r in jsonl(data / f"{name}.jsonl"):
            fr = re.split(r"[;,(]", r.get("fr") or "")[0].strip()
            kab = (r.get("kab") or "").strip()
            if fr and kab and len(fr.split()) <= 4 and len(kab.split()) <= 4:
                add(fr, kab, "dictionnaire", words=True)
    rng.shuffle(pairs)
    dev, train = pairs[:1000], pairs[1000:]
    for name, rows in (("pairs_train.jsonl", train), ("pairs_dev.jsonl", dev)):
        with (out / name).open("w", encoding="utf-8") as f:
            for p in rows:
                f.write(json.dumps(p, ensure_ascii=False) + "\n")
    print(f"  {len(train)} paires d'entraînement, {len(dev)} de contrôle : {stats}")

    # ---------- 2. Kabyle humain pour la rétro-traduction ----------
    print("Kabyle monolingue…")
    in_pairs = {norm(p["kab"]) for p in pairs}
    mono, mseen, mstats = [], set(), {}
    sources = [("tatoeba_kab_tout.jsonl.gz", "tatoeba"), ("tatoeba_kab_tout.jsonl", "tatoeba"),
               ("corpus_hca.jsonl", "livres"), ("wiki_kab.jsonl", "wikipedia"), ("attestation_kab.jsonl", "web"),
               ("commonvoice_kab.jsonl", "commonvoice"), ("corpus_poesie.jsonl", "poesie")]
    for name, origin in sources:
        for r in jsonl(data / name):
            for s in re.split(r"(?<=[.!?])\s+", clean(r.get("kab") or "")):
                s = s.strip()
                k = norm(s)
                if not k or k in mseen or k in in_pairs or key(s) in banned:
                    continue
                if not good_sentence(s) or not looks_kabyle(s):
                    continue
                mseen.add(k)
                mono.append(s)
                mstats[origin] = mstats.get(origin, 0) + 1
    rng.shuffle(mono)
    (out / "mono_kab.txt").write_text("\n".join(mono) + "\n", encoding="utf-8")
    print(f"  {len(mono)} phrases kabyles : {mstats}")

    json.dump({"paires": stats, "train": len(train), "dev": len(dev), "mono": mstats, "mono_total": len(mono),
               "eval": len(evals)}, (out / "stats.json").open("w"), ensure_ascii=False, indent=1)
    with zipfile.ZipFile(out / "amusnaw-mt-data.zip", "w", zipfile.ZIP_DEFLATED) as z:
        for n in ("pairs_train.jsonl", "pairs_dev.jsonl", "eval_set.jsonl", "mono_kab.txt", "stats.json"):
            z.write(out / n, n)
    print(f"Prêt : {out / 'amusnaw-mt-data.zip'}")


if __name__ == "__main__":
    d = Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / "data")
    o = Path(sys.argv[2] if len(sys.argv) > 2 else d / "mt")
    main(d, o)
