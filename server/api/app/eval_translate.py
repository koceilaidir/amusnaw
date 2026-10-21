"""Banc d'essai de traduction : la même série de phrases pour tous les moteurs.

  docker compose exec api python -m app.eval_translate            # NLLB, les deux sens
  docker compose exec api python -m app.eval_translate --n 50     # plus court

Score chrF (0 à 100) : ressemblance, caractère par caractère, entre la traduction
du moteur et la traduction humaine. Plus haut = mieux. Repères : < 20 très faible,
30–40 compréhensible, > 50 bon.

Les phrases du banc d'essai sont tirées au sort une fois pour toutes (graine fixe) ;
elles sont exclues de l'entraînement de nos modèles (voir eval_ids()).
"""
import argparse
import asyncio
import hashlib
import json
import random
import time
from collections import Counter
from pathlib import Path

from .config import get_settings
from . import translate as T

SEED = 2026


def _pairs(path: Path, need_confident: bool):
    if not path.exists():
        return []
    out = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if need_confident and not r.get("confident"):
                continue
            fr, kab = (r.get("fr") or "").strip(), (r.get("kab") or "").strip()
            if 4 <= len(fr.split()) <= 25 and fr and kab:
                out.append({"fr": fr, "kab": kab})
    return out


def eval_set(data_dir: str | None = None, n_daily: int = 200, n_books: int = 100) -> list[dict]:
    """200 phrases du quotidien (Tatoeba) + 100 phrases de livres (Petit Prince, Feraoun, Camus)."""
    d = Path(data_dir or get_settings().data_dir)
    rng = random.Random(SEED)
    daily = _pairs(d / "tatoeba_fr.jsonl", False)
    daily = [p for p in daily if len(p["fr"].split()) <= 15]
    books = []
    for name in ("parallel_petit_prince.jsonl", "parallel_feraoun.jsonl", "parallel_camus.jsonl"):
        books += _pairs(d / name, True)
    rng.shuffle(daily)
    rng.shuffle(books)
    return ([{**p, "set": "quotidien"} for p in daily[:n_daily]] +
            [{**p, "set": "livres"} for p in books[:n_books]])


def eval_ids(data_dir: str | None = None) -> set[str]:
    """Empreintes des phrases du banc d'essai (à retirer des données d'entraînement)."""
    return {hashlib.sha1(T._norm(p["fr"]).encode()).hexdigest() for p in eval_set(data_dir)} | \
           {hashlib.sha1(T._norm(p["kab"]).encode()).hexdigest() for p in eval_set(data_dir)}


def chrf(hyp: str, ref: str, n: int = 6, beta: float = 2.0) -> float:
    """chrF (Popović 2015), sans espaces, moyenne des n-grammes de 1 à 6 caractères."""
    h, r = hyp.replace(" ", ""), ref.replace(" ", "")
    precs, recs = [], []
    for k in range(1, n + 1):
        hc = Counter(h[i:i + k] for i in range(len(h) - k + 1))
        rc = Counter(r[i:i + k] for i in range(len(r) - k + 1))
        if not hc or not rc:
            continue
        match = sum((hc & rc).values())
        precs.append(match / sum(hc.values()))
        recs.append(match / sum(rc.values()))
    if not precs:
        return 0.0
    p, rr = sum(precs) / len(precs), sum(recs) / len(recs)
    if p + rr == 0:
        return 0.0
    return 100 * (1 + beta ** 2) * p * rr / (beta ** 2 * p + rr)


async def _nllb(items, src, tgt):
    out = []
    for i in range(0, len(items), 16):
        res = await T.machine([p[src] for p in items[i:i + 16]], src, tgt)
        if res is None:
            return None
        out += res
    return out


def _nearest(items, src, tgt):
    """Base de comparaison : la phrase la plus proche de la mémoire humaine (sans la phrase elle-même)."""
    out = []
    for p in items:
        near = T.similar(p[src], src, 1, exclude=p[src])
        out.append(near[0][tgt] if near else "")
    return out


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=0, help="limiter le nombre de phrases (test rapide)")
    ap.add_argument("--out", default="/tmp/eval_traduction.json")
    args = ap.parse_args()
    if not T._TM_PATH.exists():
        T.build_memory()
    items = eval_set()
    if args.n:
        items = items[: args.n // 2] + [p for p in items if p["set"] == "livres"][: args.n - args.n // 2]
    report = {"date": time.strftime("%Y-%m-%d %H:%M"), "phrases": len(items), "scores": {}, "exemples": []}
    # nom du modèle chargé par le service de traduction (NLLB de base ou amusnaw-mt)
    engine = "NLLB"
    try:
        import httpx  # noqa: PLC0415
        m = httpx.get(get_settings().mt_url.rstrip("/") + "/health", timeout=5).json().get("model", "")
        engine = "amusnaw-mt" if "amusnaw" in m else "NLLB"
    except Exception:  # noqa: BLE001
        pass
    for src, tgt in (("fr", "kab"), ("kab", "fr")):
        engines = {"mémoire (phrase proche)": _nearest(items, src, tgt)}
        t = time.time()
        nl = await _nllb(items, src, tgt)
        if nl is not None:
            engines[engine] = nl
            print(f"{engine} {src}→{tgt} : {len(items)} phrases en {time.time() - t:.0f} s", flush=True)
        else:
            print("NLLB indisponible (service « mt » lancé ?)", flush=True)
        for name, hyps in engines.items():
            for subset in ("quotidien", "livres"):
                sc = [chrf(h, p[tgt]) for h, p in zip(hyps, items) if p["set"] == subset]
                if sc:
                    report["scores"][f"{src}→{tgt} | {name} | {subset}"] = round(sum(sc) / len(sc), 1)
        if engine in engines:
            for h, p in list(zip(engines[engine], items))[:8]:
                report["exemples"].append({"sens": f"{src}→{tgt}", "source": p[src], "humain": p[tgt], engine: h})
    Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\nScores chrF (0–100, plus haut = mieux) :")
    for k, v in report["scores"].items():
        print(f"  {v:5.1f}  {k}")
    print(f"\nDétail et exemples : {args.out}")


if __name__ == "__main__":
    asyncio.run(main())
