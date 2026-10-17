"""Apprend de nouvelles traductions kabyle → français à partir des textes traduits
alignés, au niveau des lemmes (pas de traduction « miroir » ligne à ligne).

    python learn_lexicon.py ../data            # écrit ../data/lexicon_appris.jsonl
    python learn_lexicon.py ../data --holdout  # test caché : précision mesurée

Données d'apprentissage (paires kabyle/français) :
  - corpus parallèles réalignés (paires « confident » seulement) ;
  - Tinfaliyin (préfixes séparés de l'auteur recollés quand la forme obtenue est connue) ;
  - expressions du lexique du corps humain ; blocs du programme A1 ;
  - Tatoeba kabyle-français (226 000 paires) et contes Numidya.
  (Le corpus de Bouamara, licence ND, n'est PAS utilisé.)

Méthode (« liaison compétitive ») :
  1. chaque mot kabyle est lemmatisé ; les mots déjà connus « expliquent » les mots
     français correspondants, qu'on retire de la phrase ;
  2. sur ce qui reste, on compte les cooccurrences lemme inconnu ↔ racine française ;
  3. une traduction est retenue si elle revient dans au moins 3 paires, avec un
     coefficient de Dice ≥ 0,3, et si c'est le meilleur choix dans les deux sens.
Chaque traduction apprise garde ses preuves (nombre de paires, exemple).
"""
from __future__ import annotations

import json
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

from lemmatize import WORD, Lemmatizer, nfc
from lexsim import STOPFR, WORD_FR, _stem, fr_stems

PREFIXES = {"i", "y", "t", "n", "tt", "ye", "te", "ne", "d"}


def load_pairs(data: Path, content: Path):
    pairs = []
    for p in sorted(data.glob("parallel_*.jsonl")):
        for line in open(p, encoding="utf-8"):
            r = json.loads(line)
            if r.get("confident"):
                pairs.append((r["kab"], r["fr"], p.stem))
    tinf = data / "tinfaliyin.jsonl"
    if tinf.exists():
        for line in open(tinf, encoding="utf-8"):
            r = json.loads(line)
            pairs.append((r["kab"], r["fr"], "tinfaliyin"))
    # Tatoeba kabyle-français (CC BY 2.0 FR) et contes Numidya (CC BY-NC 4.0)
    for name, tag in (("tatoeba_fr.jsonl", "tatoeba"), ("contes_numidya.jsonl", "contes")):
        if (data / name).exists():
            for line in open(data / name, encoding="utf-8"):
                r = json.loads(line)
                pairs.append((r["kab"], r["fr"], tag))
    corps = data / "lexicon_corps_humain.jsonl"
    if corps.exists():
        for line in open(corps, encoding="utf-8"):
            for ex in json.loads(line).get("expressions") or []:
                if ex.get("kab") and ex.get("fr"):
                    pairs.append((ex["kab"], ex["fr"], "corps"))
    cur = content / "curriculum_a1.json"
    if cur.exists():
        for u in json.loads(cur.read_text("utf-8"))["units"]:
            for c in u.get("chunks", []):
                pairs.append((c["kab"], c["fr"], "programme"))
    return pairs


def join_prefixes(tokens, lem):
    """« i tt ru » → « ittru », « I nna-yas » → « inna-yas » si la forme recollée est connue."""
    out, i = [], 0
    while i < len(tokens):
        t = tokens[i]
        if t in PREFIXES and i + 1 < len(tokens):
            for j in (3, 2):  # recoller jusqu'à 3 morceaux
                cand = "".join(tokens[i:i + j])
                if i + j <= len(tokens) and lem.analyze(cand) and not lem.analyze(cand)[0]["pos"] == "outil":
                    out.append(cand)
                    i += j
                    break
            else:
                out.append(t)
                i += 1
        else:
            out.append(t)
            i += 1
    return out


def unknown_key(token, freq):
    """Forme inconnue → clé regroupant ses variantes (annexion) : temdint → tamdint."""
    w = token.split("-")[0]
    cands = {w}
    if w.startswith("we") and len(w) > 3:
        cands.add("a" + w[2:])
    if w.startswith("u") and len(w) > 3:
        cands.add("a" + w[1:])
    if w.startswith("w") and len(w) > 2 and w[1] in "aiu":
        cands.add(w[1:])
    if w.startswith("yi") and len(w) > 3:
        cands.add(w[1:])
    if w.startswith("te") and len(w) > 3:
        cands.add("ta" + w[2:])
    if w.startswith("t") and len(w) > 3 and w[1] not in "aeiu":
        cands.add("ta" + w[1:])
    free = [c for c in cands if c[:1] in "ai" or c.startswith(("ta", "ti"))]
    best = max(free or cands, key=lambda c: (freq.get(c, 0), c == w))
    return best


def units(kab, lem, freq, hidden, learned=None):
    learned = learned or {}
    toks = join_prefixes(WORD.findall(nfc(kab)), lem)
    known, unknown = {}, set()
    for t in toks:
        an = lem.analyze(t)
        if an and an[0]["pos"] in ("outil", "nom propre"):
            continue
        lemmas = {a["lemma"] for a in an}
        if lemmas and not (lemmas & hidden):
            for L in lemmas:
                st = set()
                for fr in lem.meanings.get(L, ()):
                    st |= fr_stems(re.sub(r"\(.*?\)", "", fr))
                if st:
                    known[L] = st
            if any(known.get(L) for L in lemmas):
                continue
        key = sorted(lemmas & hidden)[0] if lemmas & hidden else (
            sorted(lemmas)[0] if lemmas else unknown_key(t, freq))
        if key in learned:  # appris à un tour précédent : explique désormais sa traduction
            known[key] = {learned[key]}
            continue
        if len(key) >= 3:
            unknown.add(key)
    return known, unknown


def learn(pairs, lem, freq, hidden=frozenset(), min_pairs=3, min_dice=0.3, learned=None):
    verbs = set(lem.verb_fr)
    cK, cF, cKF = Counter(), Counter(), Counter()
    surface = defaultdict(Counter)
    example = {}
    for kab, fr, src in pairs:
        known, unk = units(kab, lem, freq, hidden, learned)
        explained = set().union(*known.values()) if known else set()
        words = [w.lower() for w in WORD_FR.findall(fr.replace("’", "'"))]
        stems = set()
        for w in words:
            if w in STOPFR or len(w) <= 2:
                continue
            s = _stem.stemWord(w)
            if s not in explained:
                stems.add(s)
                surface[s][w] += 1
        if not unk or not stems:
            continue
        for k in unk:
            cK[k] += 1
        for s in stems:
            cF[s] += 1
        for k in unk:
            for s in stems:
                cKF[k, s] += 1
                example.setdefault((k, s), (kab, fr, src))
    best_for_f = {}
    for (k, s), n in cKF.items():
        d = 2 * n / (cK[k] + cF[s])
        if d > best_for_f.get(s, (0, None))[0]:
            best_for_f[s] = (d, k)
    out = {}
    for (k, s), n in cKF.items():
        if n < min_pairs:
            continue
        d = 2 * n / (cK[k] + cF[s])
        if d < (max(min_dice, 0.6) if len(k) <= 3 else min_dice):  # mots très courts : plus d'exigence
            continue
        if best_for_f[s][1] != k and best_for_f[s][0] > d * 1.2:
            continue
        if k not in out or d > out[k]["dice"]:
            forms = [w for w, _ in surface[s].most_common()]
            inf = [w for w in forms if w.endswith(("er", "ir", "re", "oir"))]
            sing = [w for w in forms if not w.endswith(("s", "x"))]
            # infinitif pour un verbe kabyle, singulier sinon (abrid → chemin, pas « cheminer »)
            nouns = [w for w in sing if w not in inf]
            fr_word = ((inf or sing or forms) if k in verbs else (nouns or sing or forms))[0]
            out[k] = {"kab": k, "fr": fr_word, "stem": s, "pairs": n, "dice": round(d, 2),
                      "example": {"kab": example[k, s][0][:160], "fr": example[k, s][1][:160],
                                  "source": example[k, s][2]}}
    return out


def iterate(pairs, lem, freq, hidden=frozenset(), rounds=4, log=None):
    """Apprentissage en plusieurs tours : ce qui est appris explique la phrase au tour suivant."""
    learned, entries = {}, {}
    for r in range(1, rounds + 1):
        res = learn(pairs, lem, freq, hidden, learned=learned)
        new = {k: v for k, v in res.items() if k not in entries}
        for k, v in new.items():
            entries[k] = {**v, "round": r}
            learned[k] = v["stem"]
        if log:
            log(r, entries, new)
        if not new:
            break
    return entries


def main(data_dir, holdout=False):
    data = Path(data_dir)
    content = data.parent / "server" / "content"
    # toujours sans les mots déjà appris : chaque grand tour réapprend tout sur le meilleur alignement
    lem = Lemmatizer.load(data, content, learned=False)
    freq = {}
    for line in open(data / "word_freq.tsv", encoding="utf-8"):
        w, n = line.rstrip("\n").split("\t")
        freq[w] = int(n)
    pairs = load_pairs(data, content)
    print(f"{len(pairs)} paires d'apprentissage")
    if holdout:
        # Test caché : on retire 20 % des noms connus (avec un sens), on réapprend, on compare.
        nouns = sorted({a["lemma"] for f, an in lem.forms.items() for a in an
                        if a["pos"] == "nom" and lem.meanings.get(a["lemma"])})
        random.seed(42)
        hidden = frozenset(random.sample(nouns, len(nouns) // 5))
        def log(r, entries, new):
            f = {k: v for k, v in entries.items() if k in hidden}
            ok = sum(plain(v["stem"]) in gold_of(k) for k, v in f.items())
            print(f"  tour {r}: +{len(new)} appris (total {len(entries)}) ; cachés retrouvés {len(f)}, "
                  f"précision {100 * ok / max(len(f), 1):.0f} %")

        import unicodedata

        def plain(x):
            return "".join(c for c in unicodedata.normalize("NFD", x) if unicodedata.category(c) != "Mn")

        def gold_of(k):
            g = set()
            for fr in lem.meanings[k]:
                g |= {plain(x) for x in fr_stems(re.sub(r"\(.*?\)", "", fr))}
            return g
        res = iterate(pairs, lem, freq, hidden, log=log)
        found = {k: v for k, v in res.items() if k in hidden}
        good = sum(plain(v["stem"]) in gold_of(k) for k, v in found.items())
        print(f"test caché : {len(hidden)} mots cachés, {len(found)} retrouvés, "
              f"précision {100 * good / max(len(found), 1):.0f} % ({good}/{len(found)})")
        for k, v in list(found.items())[:25]:
            print(f"   {k:14} → {v['fr']:14} (vrai : {'; '.join(sorted(lem.meanings[k]))[:50]})  "
                  f"paires {v['pairs']} dice {v['dice']}")
        return
    res = iterate(pairs, lem, freq, log=lambda r, e, n: print(f"  tour {r}: +{len(n)} (total {len(e)})"))
    rows = []
    for k, v in sorted(res.items(), key=lambda x: -x[1]["pairs"]):
        rows.append({**v, "kind": "entry", "domain": "appris", "needs_review": True,
                     "source": "Appris par Amusnaw sur des textes traduits (livres HCA, Tatoeba, contes), à valider"})
    with open(data / "lexicon_appris.jsonl", "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"{len(rows)} traductions apprises → lexicon_appris.jsonl")
    # Sens des verbes découverts (sans sens) : repris de l'apprentissage
    vp = content / "verbs.json"
    doc = json.loads(vp.read_text("utf-8"))
    learned_fr = {r["kab"]: r for r in rows}
    n = 0
    for v in doc["verbs"]:
        if not v.get("fr") and v["lemma"] in learned_fr:
            v["fr"] = learned_fr[v["lemma"]]["fr"]
            v["fr_source"] = "appris (livres traduits), à valider"
            n += 1
    # Puis noms verbaux de Tinfaliyin, seulement selon un modèle de dérivation régulier :
    #   a + verbe (aɣiwel ← ɣiwel), aCCaC ← CCeC (agzam ← gzem), ou forme intensive (kennu ← knu).
    tv = data / "lexicon_tinfaliyin.jsonl"
    heads = {}
    if tv.exists():
        for line in open(tv, encoding="utf-8"):
            r = json.loads(line)
            first = re.split(r"[,;]", r["fr"])[0].strip(" (").lower()
            if first and re.fullmatch(r"(se |s'|s’)?[a-zéèêàâçîïôûù-]+(er|ir|re|oir)", first) and first not in (
                    "clair", "noir", "soir", "air"):
                heads.setdefault(r["kab"].split()[0].strip("( )"), first)
    m = 0
    for v in doc["verbs"]:
        if v.get("fr") or v.get("source") != "découvert":
            continue
        L = v["lemma"]
        pats = {"a" + L, v["themes"].get("int") or "#"}
        if re.fullmatch(r"[^aeiu][^aeiu]e[^aeiu]", L):
            pats.add("a" + L[0] + L[1] + "a" + L[3])
        hit = [heads[h] for h in pats if h in heads]
        if len(hit) == 1:
            v["fr"] = hit[0]
            v["fr_source"] = "Tinfaliyin (nom verbal), à valider"
            m += 1
    # Enfin, les lexiques HCA eux-mêmes : même mot (géminées réduites : akki ~ aki), sens à l'infinitif
    def collapse(x):
        return re.sub(r"(.)\1+", r"\1", x)
    lex = {}
    for p in sorted(data.glob("lexicon_*.jsonl")):
        if "appris" in p.name:
            continue
        for line in open(p, encoding="utf-8"):
            r = json.loads(line)
            k = nfc(r.get("kab", "")).strip(" .!")
            first = re.split(r"[,;(]", (r.get("fr") or ""))[0].strip().lower()
            if " " not in k and re.fullmatch(r"(se |s'|s’)?[a-zéèêàâçîïôûù-]+(er|ir|re|oir)", first):
                lex.setdefault(collapse(k), first)
    o = 0
    for v in doc["verbs"]:
        if not v.get("fr") and v.get("source") == "découvert" and collapse(v["lemma"]) in lex:
            v["fr"] = lex[collapse(v["lemma"])]
            v["fr_source"] = "lexiques HCA (même mot), à valider"
            o += 1
    vp.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{n} verbes découverts reçoivent un sens appris ; {m} un sens par leur nom verbal (Tinfaliyin) ; "
          f"{o} un sens des lexiques")
    for r in rows[:15]:
        print(f"   {r['kab']:14} → {r['fr']:14} paires {r['pairs']:3} dice {r['dice']}")


if __name__ == "__main__":
    main(sys.argv[1], "--holdout" in sys.argv)
