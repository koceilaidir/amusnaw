"""Mesure la qualité d'alignement des corpus parallèles (indépendante du marquage) :
part des phrases dont la VOISINE correspond mieux, et part sans aucun appui lexical."""
import json
import sys

from lexsim import similarity


def audit(path):
    R = [json.loads(line) for line in open(path, encoding="utf-8")]
    n = bad = zero = 0
    for i, r in enumerate(R):
        s = similarity(r["fr"], r["kab"])
        nb = max([similarity(R[j]["fr"], r["kab"]) for j in (i - 1, i + 1) if 0 <= j < len(R)] or [0])
        if s + nb == 0:
            continue
        n += 1
        bad += nb > s
        zero += s == 0
    conf = sum(r.get("confident", True) for r in R)
    return {"paires": len(R), "testables": n, "voisine_meilleure_%": round(100 * bad / max(n, 1), 1),
            "sans_appui_%": round(100 * zero / max(n, 1), 1), "fiables": conf}


if __name__ == "__main__":
    for p in sys.argv[1:]:
        print(p.split("/")[-1], audit(p))
