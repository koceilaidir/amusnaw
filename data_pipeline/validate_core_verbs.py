"""Ajoute à server/content/verbs.json les verbes très fréquents de core_verbs.json,
seulement si le corpus HCA atteste leurs formes (même contrôle que expand_verbs).
Un aspect sans preuve est retiré (habituel : au moins 2 formes attestées).

    python validate_core_verbs.py ../data ../server/content/verbs.json
"""
import json
import sys
from pathlib import Path

import expand_verbs as ev
from app.conjugation import conjugate


def main(data_dir, verbs_path):
    tok, ad, ur = ev.corpus_counts(Path(data_dir))
    core = json.loads((Path(__file__).parent / "core_verbs.json").read_text("utf-8"))["verbs"]
    d = json.loads(Path(verbs_path).read_text("utf-8"))
    # point de départ propre : seulement Bouamara + ajouts manuels ; le reste est recalculé ensuite
    d["verbs"] = [v for v in d["verbs"] if v.get("source") in ("bouamara", "amusnaw")]
    for v in d["verbs"]:
        for k in ("paradigm", "variants", "ext_id", "fr_more"):
            v.pop(k, None)
    known = {v["lemma"] for v in d["verbs"]}
    kept = 0
    for L, fr, p, n, a, i in core:
        if L in known or not a:
            continue
        t = conjugate({"themes": {"pret": p, "neg": n, "aor": a, "int": i}, "state": False})
        proof = {asp: ev.score(t[asp], asp, tok, ad, ur) for asp in t}
        g = {asp: len(proof[asp]) + sum(1 for f in [t[asp]["3sgm"]] if f.startswith("i") and tok["ye" + f[1:]])
             for asp in t}
        if g["aor"] < 2 or g["pret"] < 2:
            print(f"rejeté {L}: {g}")
            continue
        th = {"pret": p, "neg": n if g["neg"] else "", "aor": a, "int": i if g["int"] >= 2 else ""}
        d["verbs"].append({"lemma": L, "fr": fr, "type": "", "state": False, "themes": th, "source": "amusnaw-core",
                           "attested": proof, "needs_review": True})
        kept += 1
    Path(verbs_path).write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"verbes courants gardés : {kept} ; total {len(d['verbs'])}")


if __name__ == "__main__":
    main(*sys.argv[1:3])
