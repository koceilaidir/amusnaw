"""Agrandit server/content/verbs.json : verbes des lexiques HCA conjugués avec
les règles de K. Bouamara, gardés seulement si le corpus HCA les atteste.

    python expand_verbs.py ../data ../server/content/verbs.json

Méthode :
1. Candidats : entrées d'un seul mot dont le sens français est un verbe
   (lexiques HCA), plus les verbes du lexique du corps humain, dont le livre
   donne les formes (accompli, accompli négatif, intensif).
2. Pour chaque candidat, on essaie les thèmes possibles d'après le schème du
   mot (tableaux de Bouamara) et on conjugue avec app/conjugation.py.
3. On compte les formes réellement présentes dans les 45 000 phrases du
   corpus : aoriste après « ad », négatif après « ur », prétérit avec ses
   suffixes de personne (-ɣ, -ḍ, -n). Le thème le mieux attesté gagne ;
   un aspect sans preuve suffisante est retiré ; un verbe sans preuve est rejeté.
Chaque verbe garde ses preuves (formes attestées) pour le linguiste.
"""
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "server" / "api"))
from app.conjugation import PERSONS, conjugate  # noqa: E402

V = set("aeiu")
WORD = re.compile(r"[a-zɛɣḍṭẓṛṣḥčǧ]+(?:-[a-zɛɣḍṭẓṛṣḥčǧ]+)*")
FR_VERB = re.compile(r"^(?:s['’]|se )?[a-zàâçéèêëîïôûùüÿœ-]{3,}(?:er|ir|re|oir|ire)$")
NOT_VERBS = {"mer", "fer", "hier", "hiver", "cuir", "air", "désir", "plaisir", "avenir", "loisir", "soir",
             "noir", "miroir", "mémoire", "ministre", "titre", "arbre", "centre", "nombre", "ordre", "lettre",
             "maître", "mètre", "livre", "libre", "membre", "lumière", "frère", "père", "mère", "terre",
             "verre", "guerre", "pierre", "rivière", "chambre", "chèvre", "fièvre", "poivre", "cuivre",
             "sucre", "beurre", "foire", "gloire", "histoire", "victoire", "poire", "armoire", "territoire",
             "dossier", "papier", "métier", "premier", "dernier", "entier", "boucher", "berger", "rocher",
             "plancher", "clocher", "danger", "étranger", "voilier", "congre", "pagre", "encre", "mammifère",
             "entennoire", "contre", "quatre", "rectangulaire", "nourriture", "vipère", "panthère", "cancer"}


# sens douteux dans le lexique source : exclus en attendant le linguiste
DOUBTFUL = {"es"}


def nfc(s):
    return unicodedata.normalize("NFC", s.lower().replace("ε", "ɛ").replace("γ", "ɣ"))


def fold_fr(s):
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def corpus_counts(data: Path):
    tok, after_ad, after_ur = Counter(), Counter(), Counter()
    files = [*sorted(data.glob("corpus_*.jsonl")), *sorted(data.glob("parallel_*.jsonl")), data / "tinfaliyin.jsonl",
             data / "tatoeba_kab.jsonl", data / "tatoeba_kab_tout.jsonl", data / "contes_numidya.jsonl",
             data / "wiki_kab.jsonl", data / "attestation_kab.jsonl", data / "commonvoice_kab.jsonl"]
    for f in files:
        if not Path(f).exists():
            continue
        for line in open(f, encoding="utf-8"):
            words = [w.split("-")[0] for w in WORD.findall(nfc(json.loads(line)["kab"]))]
            for i, w in enumerate(words):
                tok[w] += 1
                prev = words[i - 1] if i else ""
                prev2 = words[i - 2] if i > 1 else ""
                if prev in ("ad", "a", "ara") or (prev in ("as", "ak", "am", "asen", "d", "t", "tt", "iyi", "yi")
                                                   and prev2 in ("ad", "a", "ara")):
                    after_ad[w] += 1
                if prev == "ur" or (prev in ("d", "t", "as", "ak", "am", "iyi", "yi") and prev2 == "ur"):
                    after_ur[w] += 1
    return tok, after_ad, after_ur


def strip3(form: str) -> str:
    """Forme de 3e masc. sing. → thème : yuki → uki, ixẓer → xẓer, yebleɛ → bleɛ."""
    f = form.replace("ur ", "").strip()
    if f.startswith("ye") and len(f) > 3 and f[2] not in V and f[3] not in V:
        return f[2:]
    if f.startswith("y") and len(f) > 1 and f[1] in V:
        return f[1:]
    if f.startswith("i") and len(f) > 1 and f[1] not in V:
        return f[1:]
    return f


def shape(L: str) -> str:
    return "".join("e" if c == "e" else ("V" if c in V else "C") for c in L)


def candidates(L: str) -> dict:
    """Thèmes possibles (Bouamara, tableaux II) selon le schème du lemme."""
    s = shape(L)
    pret, neg, intens = {L}, set(), {"tt" + L, "tte" + L}
    c = [ch for ch in L]
    if s == "CCeC":  # G3.1-1 lmed / G4-3 ɣer-like non
        neg.add(L[:2] + "i" + L[3])
        intens.add(L[0] + "e" + L[1] + L[1] + "e" + L[3])
        intens.add("tt" + L[:2] + "i" + L[3])
    if s == "CeC":  # G3.1 (ger) / G4-3 (ɣer)
        pret.add(L[0] + L[2] + "a")
        neg |= {L[0] + L[2] + "i", L[0] + "i" + L[2]}
        intens |= {L[0] + L[0] + "a" + L[2], L + L[2], "tt" + L[0] + "a" + L[2]}
    if s == "CCV" and L.endswith("u"):  # G4-1 bḍu
        pret.add(L[:2] + "a")
        neg.add(L[:2] + "i")
        intens.add(L[0] + "e" + L[1] + L[1] + "u")
    if s == "CCV" and L.endswith("i"):  # G2-5 fsi
        intens.add(L[0] + "e" + L[1] + L[1] + "i")
    if s == "CeCCeC":  # G2-1 cerreg
        intens.add("tt" + L[:4] + "i" + L[5])
    if s == "CVCC" and L[2] == L[3]:  # G2-2 cudd
        intens.add("tt" + L + "u")
    if s == "VCV" and L[0] == "a":  # G4-6 aru
        pret.add("u" + L[1] + "a")
        neg.add("u" + L[1] + "i")
    if s == "VCeC" and L[0] == "a":  # G4-2 afeg
        pret.add("u" + L[1:])
        neg.add("u" + L[1] + "i" + L[3])
    if s == "eCC":  # G4-8 els
        pret.add(L[1:] + "a")
        neg.add(L[1:] + "i")
        intens |= {"tt" + L[1] + "u" + L[2], "tt" + L[1] + "u" + L[2] + "u"}
    if s == "eC":  # eg → ga / gi (yega, ur yegi)
        pret.add(L[1] + "a")
        neg.add(L[1] + "i")
    if s == "VC":  # G4-10 af → ufa ; aɣ → uɣ
        pret |= {"u" + L[1] + "a", "u" + L[1]}
    if s == "CVC" and L[1] == "i":  # G3.2-3 fiq
        pret.add(L[0] + "a" + L[2])
    if s == "CCVC" and L[2] == "i":  # G3.2-10 mlil
        pret.add(L[:2] + "a" + L[3])
        intens.add("tte" + L)
    if s == "VCV" and L[0] == "a" and L[2] == "i":  # G3.2-13 ali
        pret.add("u" + L[1:])
    if s == "CeCCV" and L.endswith("i"):  # G3.2-6 jerri
        pret.add(L[:-1] + "a")
    for p in list(pret):
        if p.endswith("a"):
            neg.add(p[:-1] + "i")
        neg.add(p)
    return {"pret": pret, "neg": neg, "int": intens}


def score(forms: dict, aspect: str, tok, after_ad, after_ur) -> list[str]:
    """Formes de l'aspect attestées dans le bon contexte."""
    out = []
    for p, f in forms.items():
        if aspect == "aor":
            ok = after_ad[f] > 0
        elif aspect == "neg":
            ok = after_ur[f] > 0
        elif aspect == "pret":
            # suffixes de personne : très spécifiques au verbe
            # attestée hors de « ad » et de « ur » (sinon c'est un aoriste ou un négatif)
            ok = tok[f] - after_ad[f] - after_ur[f] > 0
        else:
            ok = tok[f] > 0
        if ok:
            out.append(f)
    return sorted(set(out))


def evaluate(L, themes_opts, tok, after_ad, after_ur, given=None):
    best = {"aor": L}
    proof = {}
    # aoriste = lemme (règle 1) : il doit être attesté après « ad »
    aor = conjugate({"themes": {"aor": L}, "state": False})["aor"]
    proof["aor"] = score(aor, "aor", tok, after_ad, after_ur)
    for aspect in ("pret", "neg", "int"):
        ranked = []
        for th in themes_opts[aspect]:
            forms = conjugate({"themes": {aspect: th}, "state": False})[aspect]
            n = len(score(forms, aspect, tok, after_ad, after_ur))
            # thème donné par le livre : prioritaire dès qu'une forme est attestée
            ranked.append((n + (100 if given and th in given.get(aspect, ()) and n else 0), th, forms))
        ranked.sort(key=lambda r: (-r[0], len(r[1])))
        if ranked and (ranked[0][0] >= (2 if aspect != "neg" else 1) or ranked[0][0] > 100):
            best[aspect] = ranked[0][1]
            proof[aspect] = score(ranked[0][2], aspect, tok, after_ad, after_ur)
    return best, proof


def main(data_dir: str, verbs_path: str):
    data = Path(data_dir)
    tok, after_ad, after_ur = corpus_counts(data)
    doc = json.loads(Path(verbs_path).read_text(encoding="utf-8"))
    base = [v for v in doc["verbs"] if v.get("source") not in ("corpus", "découvert")]
    known = {v["lemma"] for v in base}

    glosses: dict[str, dict] = {}
    for f in [data / "lexicon.jsonl", data / "glossaries.jsonl", *sorted(data.glob("lexicon_*.jsonl"))]:
        if not Path(f).exists():
            continue
        for line in open(f, encoding="utf-8"):
            r = json.loads(line)
            k = nfc(r["kab"]).strip(" .!?")
            fr = re.sub(r"\s+", " ", r.get("fr", "")).strip(" .;").lower()
            first = re.split(r"[,;(/]", fr)[0].strip()
            if " " in k or "-" in k or not first or len(k) < 2:
                continue
            is_verb = r.get("category") == "verbe" or (FR_VERB.match(first) and first.split()[-1] not in NOT_VERBS) \
                or first.startswith(("être ", "avoir ", "se ", "s'", "faire "))
            if not is_verb:
                continue
            g = glosses.setdefault(k, {"fr": [], "sources": set(), "given": None})
            if fold_fr(first) not in [fold_fr(x) for x in g["fr"]]:
                g["fr"].append(first)
            g["sources"].add(r.get("source", f.name))
            if r.get("category") == "verbe" and r.get("grammar"):
                g["given"] = r
    added, rejected = [], 0
    for L, g in sorted(glosses.items()):
        if L in known or L in DOUBTFUL:
            continue
        opts = candidates(L)
        given = g["given"]
        book = {"pret": set(), "neg": set(), "int": set()}
        if given:  # formes données par le livre (lexique du corps humain)
            gm = given["grammar"]
            for key, rx in (("int", r"intensif\s*:?\s*([^,]+)"), ("pret", r"accompli\s*:?\s*([^,]+)"),
                            ("neg", r"accompli négatif\s*:?\s*([^,]+)")):
                m = re.search(rx, gm)
                if m:
                    for f in re.split(r"\s*/\s*|\s+ou\s+", m.group(1)):
                        f = nfc(f).strip(" :")
                        if f and not f.startswith("ur") or key == "neg":
                            opts[key].add(strip3(f))
                            book[key].add(strip3(f))
        best, proof = evaluate(L, opts, tok, after_ad, after_ur, book)
        n = sum(len(v) for v in proof.values())
        short = len(L) <= 2  # mots très courts : risque de coïncidence, il faut plus de preuves
        if len(proof.get("aor", [])) < 2 or "pret" not in best or n < (10 if short else 6):
            rejected += 1
            continue
        best.setdefault("neg", best["pret"])
        added.append({
            "lemma": L, "fr": ", ".join(g["fr"][:3]), "type": shape(L), "state": False,
            "themes": {"pret": best["pret"], "neg": best["neg"], "aor": L, "int": best.get("int", "")},
            "source": "corpus", "sources": sorted(g["sources"])[:3],
            "attested": {k: v for k, v in proof.items()}, "needs_review": True,
        })
    doc["verbs"] = base + added
    doc["note"] = ("source=corpus : verbe des lexiques HCA conjugué par les règles de Bouamara ; "
                   "chaque aspect gardé seulement si le corpus HCA en atteste les formes (champ attested).")
    Path(verbs_path).write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"candidats {len(glosses)} · ajoutés {len(added)} · rejetés {rejected} · total {len(doc['verbs'])}")


if __name__ == "__main__":
    main(*sys.argv[1:3])
