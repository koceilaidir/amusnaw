"""Fusionne les tables de conjugaison de « taqbaylit/kabyle-verbs » (Hugging Face,
CC BY 4.0 déclarée ; identifiants et contenu issus du conjugueur amyag.com)
avec server/content/verbs.json.

    python import_verbs.py ../data ../server/content/verbs.json

Règles de fusion (mesurées : accord forme par forme avec nos règles —
aoriste 98-100 %, prétérit 88-100 %, négatif/intensif plus faibles pour nos
verbes devinés, où leurs tables sont meilleures) :
  - verbes de Bouamara : ses thèmes restent la référence (180 formes vérifiées),
    les tables externes sont gardées comme variantes ;
  - autres verbes connus : la table externe devient la référence ;
  - verbes absents de notre base : ajoutés avec leur sens français.
Chaque verbe reçoit le nombre de ses formes attestées dans le corpus HCA.
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

import pyarrow.parquet as pq

import expand_verbs as ev
from app.conjugation import conjugate

P = {"firstSingular": "1sg", "secondSingular": "2sg", "thirdSingular": "3sgm", "thirdSingularFeminine": "3sgf",
     "firstPlural": "1pl", "secondPlural": "2plm", "secondPluralFeminine": "2plf", "thirdPlural": "3plm",
     "thirdPluralFeminine": "3plf"}
IMP = {"secondSingular": "2sg", "secondPlural": "2plm", "secondPluralFeminine": "2plf"}
SRC = ("taqbaylit/kabyle-verbs (Hugging Face, CC BY 4.0), tables issues du conjugueur amyag.com")


def load_ext(data: Path):
    rows = []
    for p in sorted((data / "externes").glob("verbes_tables_*.parquet")):
        rows += pq.read_table(p).to_pylist()
    return rows


def paradigm(e) -> dict:
    """Table externe → {aspect: {personne: [formes]}} + participes, impératif."""
    t = {}
    for asp, key in (("pret", "preterite"), ("neg", "negativePreterite"), ("aor", "aorist")):
        d = json.loads(e[key]) if e.get(key) else {}
        t[asp] = {P[k]: list(dict.fromkeys(v)) for k, v in d.items() if k in P and v}
    t["int"], t["int_neg"], t["imp_int"] = {}, {}, {}
    for it in json.loads(e["intensiveForms"]) if e.get("intensiveForms") else []:
        for k, v in (it.get("intensiveAorist") or {}).items():
            if k in P:
                t["int"].setdefault(P[k], [])
                t["int"][P[k]] += [x for x in v if x not in t["int"][P[k]]]
        for k, v in (it.get("intensiveImperative") or {}).items():
            if k in IMP:
                t["imp_int"].setdefault(IMP[k], []).extend(v)
    imp = json.loads(e["imperative"]) if e.get("imperative") else {}
    t["imp"] = {IMP[k]: v for k, v in imp.items() if k in IMP}
    t["part"] = {}
    for asp, key in (("aor", "aoristParticiple"), ("pret", "preteriteParticiple"), ("neg", "negativePreteriteParticiple")):
        v = json.loads(e[key]) if e.get(key) else []
        if v:
            t["part"][asp] = v
    return {k: v for k, v in t.items() if v}


def all_forms(par: dict) -> set:
    out = set()
    for asp, d in par.items():
        for v in (d.values() if isinstance(d, dict) else [d]):
            out.update(v if isinstance(v, list) else [v])
    return out


def short_fr(tr: str) -> str:
    parts = [p.strip() for p in (tr or "").replace(" ; ", ";").split(";") if p.strip()]
    return " ; ".join(parts[:2])


def main(data_dir, verbs_path):
    data = Path(data_dir)
    tok, after_ad, after_ur = ev.corpus_counts(data)
    ext = load_ext(data)
    by_name = defaultdict(list)
    for e in ext:
        by_name[e["name"]].append(e)
    doc = json.loads(Path(verbs_path).read_text("utf-8"))
    doc["verbs"] = [v for v in doc["verbs"] if v.get("source") != "amyag"]
    used_ids = set()
    replaced = enriched = 0
    for v in doc["verbs"]:
        cands = by_name.get(v["lemma"], [])
        if not cands:
            continue
        mine = conjugate(v)
        best = max(cands, key=lambda e: sum(1 for a in mine for p, f in mine[a].items()
                                            if f in paradigm(e).get(a, {}).get(p, [])))
        used_ids.add(best["id"])
        par = paradigm(best)
        v["ext_id"] = best["id"]
        if v.get("source") == "bouamara":
            v["variants"] = par  # Bouamara reste la référence
        else:
            v["paradigm"] = par  # la table externe devient la référence
            replaced += 1
        if not v.get("fr"):
            v["fr"] = short_fr(best["translation"])
            v["fr_source"] = SRC
            enriched += 1
        else:
            v["fr_more"] = short_fr(best["translation"])
    added = 0
    for e in ext:
        if e["id"] in used_ids or not e.get("name"):
            continue
        par = paradigm(e)
        forms = all_forms(par)
        att = sorted(f for f in forms if tok.get(f))
        doc["verbs"].append({
            "lemma": e["name"], "fr": short_fr(e["translation"]), "type": f"amyag {e.get('pattern_number', '')}",
            "state": False, "derived": bool(e.get("isDerived")), "irregular": bool(e.get("isIrregular")),
            "pattern": e.get("pattern_verb"), "paradigm": par, "source": "amyag", "ext_id": e["id"],
            "attested_forms": len(att), "attested_examples": att[:6], "needs_review": True})
        added += 1
    Path(verbs_path).write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    n_att = sum(1 for v in doc["verbs"] if v.get("source") == "amyag" and v["attested_forms"] > 0)
    print(f"verbes existants : {replaced} reçoivent la table externe, {enriched} reçoivent un sens ; "
          f"ajoutés : {added} (dont {n_att} attestés dans les livres HCA) ; total {len(doc['verbs'])}")


if __name__ == "__main__":
    main(*sys.argv[1:3])
