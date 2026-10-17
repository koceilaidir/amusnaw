"""Découvre des verbes kabyles absents des lexiques, grâce aux règles de conjugaison.

    python discover_verbs.py ../data ../server/content/verbs.json

Idée : après « ad », le kabyle met un verbe à l'aoriste. Pour chaque forme inconnue
vue après « ad » (ad yečč, ad nruḥ, ad xedmeɣ…), on retire la marque de personne
pour obtenir un lemme possible ; on essaie les thèmes compatibles avec son schème
(tableaux de Bouamara), on conjugue, et on garde le verbe seulement si le corpus
atteste assez de ses formes au bon endroit (aoriste après « ad », prétérit sans
« ad », négatif après « ur »). Le sens est rattaché ensuite (lexiques, apprentissage).
Les verbes gardés ont source = "découvert" et needs_review.
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

import expand_verbs as ev
from lemmatize import Lemmatizer, nfc

V = set("aeiu")


def lemma_guesses(form: str) -> set[str]:
    """Aoriste conjugué → lemmes possibles (personne retirée)."""
    f = form.split("-")[0]
    out = set()
    # 1re sing. / 3e plur. / 2e plur. : suffixes
    for suf in ("eɣ", "ɣ", "en", "n", "ent", "nt"):
        if f.endswith(suf) and len(f) - len(suf) >= 2:
            stem = f[: -len(suf)]
            if not (f.startswith(("t", "n", "y")) and suf in ("eɣ", "ɣ")):
                out.add(stem)
                # schwa effacé devant suffixe vocalique : gennzeɣ → gennez, lemdeɣ → lmed
                if len(stem) >= 3 and stem[-1] not in V and stem[-2] not in V:
                    out.add(stem[:-1] + "e" + stem[-1])
                    if len(stem) >= 4 and stem[1] == "e":
                        out.add(stem[0] + stem[2:-1] + "e" + stem[-1])
    # 3e masc. / 3e fém. / 1re plur. : préfixes
    for pre in ("ye", "y", "i", "te", "t", "ne", "n"):
        if f.startswith(pre) and len(f) - len(pre) >= 2:
            rest = f[len(pre):]
            if pre in ("y",) and rest[0] not in V:
                continue
            if pre == "i" and rest[0] in V:
                continue
            out.add(rest)
    return {x for x in out if 2 <= len(x) <= 9 and re.fullmatch(r"[a-zɛɣḍṭẓṛṣḥčǧ]+", x)}


def main(data_dir, verbs_path):
    data = Path(data_dir)
    lem = Lemmatizer.load(data, data.parent / "server" / "content", learned=False)
    tok, after_ad, after_ur = ev.corpus_counts(data)
    doc = json.loads(Path(verbs_path).read_text("utf-8"))
    doc["verbs"] = [v for v in doc["verbs"] if v.get("source") != "découvert"]
    known = {v["lemma"] for v in doc["verbs"]}
    cands = Counter()
    for w, n in after_ad.items():
        if n < 2 or lem.analyze(w) or len(w) < 3:
            continue  # déjà reconnu, ou trop rare
        for L in lemma_guesses(w):
            if L not in known and not lem.analyze(L):
                cands[L] += n
    print(f"{len(cands)} lemmes possibles à tester")
    added = []
    for L, _ in cands.most_common(4000):
        opts = ev.candidates(L)
        best, proof = ev.evaluate(L, opts, tok, after_ad, after_ur)
        n_aor, n_pret = len(proof.get("aor", [])), len(proof.get("pret", []))
        total = sum(len(v) for v in proof.values())
        if n_aor < 3 or n_pret < 2 or total < 8:
            continue
        best.setdefault("neg", "")
        added.append({"lemma": L, "fr": "", "type": ev.shape(L), "state": False,
                      "themes": {"pret": best["pret"], "neg": best.get("neg", ""), "aor": L,
                                 "int": best.get("int", "")},
                      "source": "découvert", "attested": proof, "needs_review": True})
        known.add(L)
    # Doublons d'un verbe DÉJÀ connu (enɣ = neɣ, fek = efk, ett = habituel de ečč) :
    # si la moitié de ses formes attestées appartiennent à un verbe connu, on l'écarte.
    from app.conjugation import conjugate
    known_forms = {f for v in doc["verbs"] for a in conjugate(v).values() for f in a.values()}
    added = [v for v in added
             if (lambda att: len(att & known_forms) * 2 < len(att))({f for x in v["attested"].values() for f in x})]
    # Artefacts et variantes : au moins 3 lettres, pas de préfixe d'habitude « tt- »,
    # et un seul verbe par squelette consonantique (raḥ ~ ruḥ, qim ~ qqim, ewt ~ wwet).
    def skeleton(L):
        """Consonnes + place des voyelles, géminées réduites : raḥ ~ ruḥ, qim ~ qqim, ɛiwed ~ ɛawed
        (variantes), mais bnu ≠ ban, ffer ≠ fru (verbes différents)."""
        x = re.sub(r"(.)\1+", r"\1", L)
        return (re.sub(r"[aeiu]", "", x), re.sub(r"[aeiu]", "V", re.sub(r"[^aeiu]", "C", x)))
    known_sk = {skeleton(v["lemma"]) for v in doc["verbs"]}
    added = [v for v in added if len(v["lemma"]) >= 3 and not v["lemma"].startswith(("tt", "es", "et"))
             and skeleton(v["lemma"]) not in known_sk]
    best_by_sk = {}
    for v in added:
        sk, score = skeleton(v["lemma"]), sum(len(x) for x in v["attested"].values())
        if sk not in best_by_sk or score > best_by_sk[sk][0]:
            best_by_sk[sk] = (score, v)
    added = [v for _, v in best_by_sk.values()]
    # Doublons : deux lemmes qui génèrent les mêmes formes (ex. variantes de schwa) → garder le mieux attesté
    from app.conjugation import conjugate
    seen, final = {}, []
    for v in sorted(added, key=lambda v: -sum(len(x) for x in v["attested"].values())):
        sig = frozenset(f for a in conjugate(v).values() for f in a.values())
        if any(len(sig & s) > len(sig) // 2 for s in seen.values()):
            continue
        seen[v["lemma"]] = sig
        final.append(v)
    doc["verbs"] += final
    Path(verbs_path).write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"verbes découverts : {len(final)} ; total {len(doc['verbs'])}")
    for v in final[:40]:
        t = v["themes"]
        print(f"  {v['lemma']:10} prét {t['pret']:9} nég {t['neg']:9} intensif {t['int']:10} "
              f"preuves {sum(len(x) for x in v['attested'].values())}")


if __name__ == "__main__":
    main(*sys.argv[1:3])
