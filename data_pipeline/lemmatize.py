"""Lemmatiseur kabyle : ramène une forme écrite à son mot de base (lemme) avec
son analyse, à partir des ressources de la base (aucune forme inventée) :

  - mots-outils (function_words.json) ;
  - verbes (server/content/verbs.json) conjugués par les règles de K. Bouamara :
    4 aspects × 9 personnes, variante « ye- » de la 3e masc. (yella), participes
    (yellan, yilin) ;
  - noms des lexiques HCA, du programme, de Bouamara (niveau 0), des glossaires :
    forme libre, formes listées (pluriels…), état d'annexion (aqerru → uqerru,
    amdan → wemdan, tamurt → tmurt / teqbaylit, iles → yiles) ;
  - pronoms et particules collés par trait d'union (fell-as, isem-iw, yenna-yas).

    from lemmatize import Lemmatizer
    lem = Lemmatizer.load()
    lem.analyze("uqerru-iw")  →  [{"lemma": "aqerru", "pos": "nom", "how": "annexion", "fr": {...}}]
"""
from __future__ import annotations

import glob
import json
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server" / "api"))
from app.conjugation import PERSONS, conjugate, verb_forms  # noqa: E402

V = set("aeiu")
WORD = re.compile(r"[a-zɛɣḍṭẓṛṣḥčǧ]+(?:-[a-zɛɣḍṭẓṛṣḥčǧ]+)*")


def nfc(s: str) -> str:
    s = s.lower().replace("ε", "ɛ").replace("γ", "ɣ").replace("ğ", "ǧ")
    return unicodedata.normalize("NFC", s).strip()


def loose(s: str) -> str:
    """Sans points souscrits ni accents (pour les fautes de frappe : tellid ≈ telliḍ)."""
    s = unicodedata.normalize("NFD", nfc(s))
    return "".join(c for c in s if unicodedata.category(c) != "Mn").replace("ɛ", "e").replace("ɣ", "g")


def annexed(noun: str) -> set[str]:
    """Formes à l'état d'annexion possibles d'un nom à l'état libre."""
    n = noun
    out = set()
    if len(n) < 2:
        return out
    if n.startswith("ta") and len(n) > 3:
        rest = n[2:]
        out |= {"t" + rest, "te" + rest}
    elif n.startswith("a"):
        out |= {"u" + n[1:], "w" + n, "we" + n[1:]}
    elif n.startswith("i"):
        out |= {"y" + n, "ye" + n[1:]}
    elif n.startswith("u"):
        out |= {"w" + n}
    return out


class Lemmatizer:
    def __init__(self):
        self.forms: dict[str, list[dict]] = defaultdict(list)
        self.loose_forms: dict[str, list[dict]] = defaultdict(list)
        self.meanings: dict[str, set[str]] = defaultdict(set)
        self.verb_fr: dict[str, str] = {}
        self.meanings_en: dict[str, str] = {}  # sens anglais (Tatoeba ou traductions de logiciels)
        self.meanings_en_src: dict[str, str] = {}

    def _put(self, form, lemma, pos, how, extra=None):
        form = nfc(form)
        if not form:
            return
        a = {"lemma": lemma, "pos": pos, "how": how, **(extra or {})}
        if a not in self.forms[form]:
            self.forms[form].append(a)
            self.loose_forms[loose(form)].append(a)

    @classmethod
    def load(cls, data=ROOT / "data", content=ROOT / "server" / "content", learned=True) -> "Lemmatizer":
        self = cls()
        here = Path(__file__).resolve().parent
        # 1. mots-outils
        fw = json.loads((here / "function_words.json").read_text("utf-8"))["words"]
        for w, fr in fw.items():
            self._put(w, w, "outil", "mot-outil")
            self.meanings[w].add(fr)
        # 2. verbes
        verbs = json.loads((Path(content) / "verbs.json").read_text("utf-8"))["verbs"]
        for v in verbs:
            L = v["lemma"]
            self.meanings[L].add(v["fr"])
            if v.get("fr"):
                self.verb_fr.setdefault(L, v["fr"])
            table = conjugate(v, rules_only=True)
            for f, (asp, p) in verb_forms(v).items():  # règles + tables + variantes
                if asp == "part":
                    self._put(f, L, "verbe", f"participe {p}")
                elif asp in ("imp", "imp_int"):
                    self._put(f, L, "verbe", "impératif")
                elif asp != "int_neg":
                    self._put(f, L, "verbe", f"{asp} {p}")
            for asp, forms in table.items():
                for p, f in forms.items():
                    if p == "3sgm":
                        if f.startswith("i") and len(f) > 2 and f[1] not in V:
                            self._put("ye" + f[1:], L, "verbe", f"{asp} {p}")  # yella, yebɣa
                        part = (("ye" + f[1:]) if f.startswith("i") and f[1] not in V else f)
                        for base in {f, part}:
                            self._put(base + "n", L, "verbe", f"participe {asp}")  # yellan, yilin
            self._put(L, L, "verbe", "impératif / lemme")
        # 3. noms et autres mots des lexiques
        files = [*sorted(glob.glob(str(Path(data) / "lexicon*.jsonl"))), str(Path(data) / "glossaries.jsonl")]
        files.sort(key=lambda p: "appris" in p)  # les sens appris en dernier
        for p in files:
            if not Path(p).exists() or (not learned and "appris" in p):
                continue
            for line in open(p, encoding="utf-8"):
                r = json.loads(line)
                k = nfc(re.sub(r"\s*\(.*?\)", "", r.get("kab", "")))
                if not k or " " in k or len(k) > 30 or r.get("kind") == "phrase":
                    continue
                fr = (r.get("fr") or "").strip()
                if r.get("category") == "verbe":
                    continue  # les verbes passent par le conjugueur
                if "appris" in p:
                    # sens appris : seulement pour un mot qui n'a encore aucun sens, jamais pour un verbe
                    if k in self.verb_fr or self.meanings.get(k) or any(
                            a["pos"] == "verbe" for a in self.forms.get(k, [])):
                        continue
                self._add_noun(k, fr, r.get("forms") or [])
        for line in open(Path(data) / "bouamara_niveaux.jsonl", encoding="utf-8"):
            r = json.loads(line)
            if r.get("level") == 0 and " " not in r["kab"].strip():
                self._add_noun(nfc(r["kab"]), r["fr"], [])
        # 3a. sens anglais appris sur Tatoeba (si présents)
        ep = Path(data) / "sens_anglais_appris.jsonl"
        for line in (open(ep, encoding="utf-8") if ep.exists() and learned else []):
            r = json.loads(line)
            if r["kab"] not in self.meanings_en:
                self.meanings_en[r["kab"]] = r["en"]
                self.meanings_en_src[r["kab"]] = "tatoeba"
        tp = Path(data) / "termes_modernes_en.jsonl"
        for line in (open(tp, encoding="utf-8") if tp.exists() and learned else []):
            r = json.loads(line)
            k = nfc(r["kab"]).strip(" .!?")
            if " " not in k and k not in self.meanings_en:
                self.meanings_en[k] = r["en"]
                self.meanings_en_src[k] = "logiciels"
        # 3b. correcteur orthographique (Hunspell, MIT) : pluriels, féminins, formes → mot de base
        hp = Path(data) / "hunspell_kab.jsonl"
        for line in (open(hp, encoding="utf-8") if hp.exists() else []):
            r = json.loads(line)
            f, L, pos = nfc(r["form"]), nfc(r["lemma"]), r.get("pos", "")
            if not f or " " in f:
                continue
            if pos == "verbe" or L in self.verb_fr:
                if f not in self.forms:
                    self._put(f, L, "verbe", "forme (correcteur)")
            elif pos in ("nom", "adjectif", "nom d'action", "numéral", "nom de pays", "nom de lieu", ""):
                how = "pluriel (correcteur)" if "pluriel" in r.get("infl", []) else "forme (correcteur)"
                if f == L:
                    how = "forme libre"
                if not any(a["lemma"] == L for a in self.forms.get(f, [])):
                    self._put(f, L, "nom", how)
                for a in annexed(f):
                    if a not in self.forms:
                        self._put(a, L, "nom", "annexion" if f == L else "annexion du pluriel")
            elif f not in self.forms:
                self._put(f, L, "outil" if pos not in ("nom de personne",) else "nom propre", pos)
        # 4. noms propres : majuscule dans > 80 % des emplois (Lezzayer, Muḥend, Ṛebbi)
        from collections import Counter
        caps, alln = Counter(), Counter()
        for f in [*glob.glob(str(Path(data) / "corpus_*.jsonl")), *glob.glob(str(Path(data) / "parallel_*.jsonl"))]:
            for line in open(f, encoding="utf-8"):
                k = json.loads(line)["kab"]
                for m in re.finditer(r"(?<![.!?»:] )(?<!^)\b([A-ZƐƔḌṬẒṚṢḤČǦ][a-zɛɣḍṭẓṛṣḥčǧ]+)", k):
                    caps[nfc(m.group(1))] += 1
                for w in WORD.findall(nfc(k)):
                    alln[w] += 1
        for w, c in caps.items():
            if c >= 3 and c / max(alln[w], 1) > 0.8 and w not in self.forms:
                self._put(w, w, "nom propre", "nom propre")
                for a in annexed(w):
                    if a not in self.forms:
                        self._put(a, w, "nom propre", "annexion")
        # 4b. toponymes kabyles d'OpenStreetMap (ODbL) : noms de lieux d'un seul mot
        tp = Path(data) / "toponymes.jsonl"
        for line in (open(tp, encoding="utf-8") if tp.exists() else []):
            w = nfc(json.loads(line)["kab"])
            if " " not in w and "-" not in w and w not in self.forms:
                self._put(w, w, "nom propre", "nom de lieu")
        cur = Path(content) / "curriculum_a1.json"
        if cur.exists():
            for u in json.loads(cur.read_text("utf-8"))["units"]:
                for w in u["words"]:
                    if " " not in w["kab"].strip():
                        self._add_noun(nfc(w["kab"]), w["fr"], [])
        return self

    def _add_noun(self, k, fr, forms):
        k = k.strip(" .!?,;:")
        if not re.fullmatch(r"[a-zɛɣḍṭẓṛṣḥčǧ'-]+", k):
            return
        self.meanings[k].add(fr)
        self._put(k, k, "nom", "forme libre")
        for a in annexed(k):
            self._put(a, k, "nom", "annexion")
        for f in forms:
            f = nfc(f)
            if f.startswith("ur ") or " " in f or not f:
                continue
            self._put(f, k, "nom", "forme listée (pluriel…)")
            for a in annexed(f):
                self._put(a, k, "nom", "annexion du pluriel")

    def analyze(self, token: str) -> list[dict]:
        t = nfc(token).strip("-")
        parts = t.split("-")
        base, clitics = parts[0], parts[1:]
        res = list(self.forms.get(base, []))
        if not res and clitics:  # « a-t-id-yawi » : la base peut être après les particules
            for i in range(1, len(parts)):
                if parts[i] in self.forms and len(parts[i]) > 2:
                    res = list(self.forms[parts[i]])
                    break
        how = None
        if not res:
            res = list(self.loose_forms.get(loose(base), []))
            how = "approché (points/accents)" if res else None
        out = []
        for a in res:
            a = dict(a)
            if clitics:
                a["clitics"] = clitics
            if how:
                a["how"] += f", {how}"
            a["fr"] = [self.verb_fr[a["lemma"]]] if a["pos"] == "verbe" and a["lemma"] in self.verb_fr \
                else sorted(self.meanings.get(a["lemma"], []))[:3]
            if a["lemma"] in self.meanings_en:
                a["en"] = self.meanings_en[a["lemma"]]
            out.append(a)
        return out


def coverage(lem: Lemmatizer, data=ROOT / "data"):
    from collections import Counter
    tok = Counter()
    for f in [*glob.glob(str(Path(data) / "corpus_*.jsonl")), *glob.glob(str(Path(data) / "parallel_*.jsonl"))]:
        for line in open(f, encoding="utf-8"):
            tok.update(WORD.findall(nfc(json.loads(line)["kab"])))
    total = sum(tok.values())
    known = exact = 0
    unknown = Counter()
    for w, n in tok.items():
        a = lem.analyze(w)
        if a:
            known += n
            exact += n if "approché" not in a[0]["how"] else 0
        else:
            unknown[w] = n
    return total, known, exact, unknown


if __name__ == "__main__":
    lem = Lemmatizer.load()
    total, known, exact, unknown = coverage(lem)
    print(f"formes connues : {len(lem.forms)} ; lemmes avec sens : {len(lem.meanings)}")
    print(f"couverture du corpus : {100 * known / total:.1f} % des mots ({100 * exact / total:.1f} % exacts)")
    if "-v" in sys.argv:
        print("formes inconnues les plus fréquentes :", unknown.most_common(80))
