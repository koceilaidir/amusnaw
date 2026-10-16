"""Lexique de didactique et des sciences du langage (M. Mahrazi, HCA 2013)
→ data/lexicon_didactique.jsonl

Entrée : texte extrait page par page (« ==== p N ») du PDF, déjà en Unicode.
On lit la partie I (français → amazigh) :
    ► Individuel
     anemdan ―u ▬ inemdanen ―yi
Un enregistrement par équivalent kabyle. La partie II (amazigh → français,
avec étymologies) reprend les mêmes entrées ; on ne lui emprunte que les
couples absents de la partie I (voir --report).

  python parse_didactique.py [txt] [out.jsonl] [--report]
"""
import json
import re
import sys
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_TXT = Path("/tmp/claude-0/-home-claude/4d0a5699-ac07-5264-8a09-fea839f824ef/"
                   "scratchpad/txt/02-LEXIQUE-DE-DIDACT.txt")
DEFAULT_OUT = HERE.parent / "data" / "lexicon_didactique.jsonl"
SOURCE = "M. Mahrazi, Lexique de didactique et des sciences du langage, HCA 2013"
DOMAIN = "langue et didactique"

BULLET = ""            # puce () devant chaque équivalent amazigh
MARK = "―"                   # précède l'indice d'état d'annexion
PLUR = "▬"                   # sépare singulier et pluriel
KAB_OK = re.compile(r"^[a-zčḍǧɣḥṛṣṭẓɛ'-]+( [a-zčḍǧɣḥṛṣṭẓɛ'-]+| [A-Z][a-z]+)*$")
# Restes d'anciennes polices dans les mots kabyles (vérifiés sur la partie II)
KAB_FIX = str.maketrans({"é": "ẓ", "v": "ḍ", "î": "ṭ", "ε": "ɛ", "Ñ": None})


def pages(path):
    """(n° de page imprimé, lignes) pour chaque page."""
    cur, num, out = [], None, []
    for line in Path(path).read_text(encoding="utf-8").split("\n"):
        m = re.match(r"==== p (\d+)", line)
        if m:
            if cur or num:
                out.append((num, cur))
            cur, num = [], int(m.group(1)) - 1  # repli : page PDF - 1
            continue
        m = re.fullmatch(r"\s*-\s*(\d+)\s*-\s*", line)
        if m:
            num = int(m.group(1))
            continue
        cur.append(line.rstrip())
    out.append((num, cur))
    return out


def clean_fr(s):
    s = s.replace("‟", "'").replace("’", "'")
    s = re.sub(r"(?<=[a-zé\)])\d+\b", "", s)      # appel de note « Correct2 »
    s = re.sub(r"-{3,}", " ", s)                       # « Double (----- articulation) »
    s = re.sub(r"\s+", " ", s).replace("( ", "(").replace(" )", ")").strip()
    return s


def norm_kab(s):
    # tables de correction sur les mots kabyles seulement (pas « Markov »)
    s = " ".join(w if w[:1].isupper() and len(w) > 1 and w[1:].islower() and i
                 else w.translate(KAB_FIX) for i, w in enumerate(s.split()))
    s = unicodedata.normalize("NFC", s)
    # « ameqqran (asekkil) » → « asekkil ameqqran » ; « tis-snat (tutlayt ---) »
    m = re.fullmatch(r"(.+?) \((\w+)(?: -+)?\)", s)
    if m:
        head, noun = m.group(1), m.group(2)
        if "-" in s[s.index("("):] or noun in ("asekkil", "isekkilen"):
            s = f"{noun} {head}"
        else:
            s = f"{head} {noun}"
    if s[:1].isupper() and " " not in s:
        s = s[0].lower() + s[1:]
    return s


def split_part(part):
    """« tiwulemt / aswulem ―t/u » → (['tiwulemt', 'aswulem'], ['t', 'u'])."""
    marks = []
    m = re.search(MARK + r"\s*([\w/ ]+?)\s*$", part)
    if m:
        marks = [x.strip() for x in m.group(1).split("/") if x.strip()]
        part = part[:m.start()]
    part = part.replace(MARK, " ")
    alts = [a.strip() for a in part.split("/") if a.strip()]
    if len(alts) == 2:
        a, b = alts[0].split(), alts[1].split()
        if len(a) == 1 and len(b) > 1:          # tiddukla / tamesmunt tafransist…
            alts = [" ".join([a[0]] + b[1:]), alts[1]]
        elif len(a) > 1 and len(b) == 1:        # snat n tenqiḍin / tneqqaḍ
            if a[-2] == "n" and b[0][:2] in ("am", "an"):
                alts = [alts[0], " ".join(a[:-2] + b)]   # iger n unamek / amnamek
            else:
                alts = [alts[0], " ".join(a[:-1] + b)]
    return alts, marks


def parse_equiv(line):
    """Ligne d'équivalent → liste de (kab, pluriels, annexion)."""
    line = line.replace(BULLET, " ").strip()
    if PLUR in line:
        sing, plur = line.split(PLUR, 1)
    else:
        # pluriel sans ▬ : « ibḍi ―yi  ibḍiyen ―yi »
        m = re.fullmatch(r"(\S+ ―\S+)\s+(\S+ ―\S+)", line)
        sing, plur = (m.group(1), m.group(2)) if m else (line, "")
    s_alts, s_marks = split_part(sing)
    p_alts, p_marks = split_part(plur) if plur.strip() else ([], [])
    # un seul pluriel pour plusieurs singuliers : celui dont l'indice d'annexion
    # correspond (« asakez / tukza ―u/tu ▬ tukziwin ―tu » → tukza)
    owner = 0
    if len(p_alts) == 1 and len(s_alts) > 1 and len(s_marks) == len(s_alts) and p_marks:
        hits = [i for i, m in enumerate(s_marks) if m == p_marks[0]] or \
               [i for i, m in enumerate(s_marks) if m[:1] == p_marks[0][:1]]
        owner = hits[0] if hits else 0
    out = []
    for i, kab in enumerate(s_alts):
        if len(p_alts) == len(s_alts) and len(s_alts) > 1:
            forms = [p_alts[i]]
        elif len(s_alts) == 1:
            forms = p_alts
        else:
            forms = p_alts if i == owner else []
        ann = s_marks[i] if len(s_marks) == len(s_alts) else (s_marks[0] if len(s_marks) == 1 and i == 0 else None)
        out.append((norm_kab(kab), [norm_kab(f) for f in forms], ann))
    return out


def is_headword_like(s):
    """Vedette sans ► (« Centripète »)."""
    return bool(re.match(r"^[A-ZÉÈÂ][a-zéèêëàâîïôûç\-' ]+(\(.*\))?$", s)) and MARK not in s


def parse_part1(pgs):
    recs, fr, in_part = [], None, False
    last = None
    for page, lines in pgs:
        for raw in lines:
            s = raw.strip()
            if s == "PARTIE I":
                in_part = True
                continue
            if s == "PARTIE II":
                return recs
            if not in_part or not s or re.fullmatch(r"[A-Z]", s):
                continue
            if s.startswith("►"):
                fr, last = clean_fr(s[1:]), None
                continue
            if s.startswith(MARK) and last is not None:      # suite de ligne coupée
                last["line"] += " " + s
                continue
            if s.startswith("<") or re.match(r"^\d+ ", s) or "<" in s:
                continue                                     # étymologie, note
            if s.startswith(BULLET) or (fr and re.match(r"^[a-zɣḍčǧṭẓṣḥɛ]", s)):
                last = {"fr": fr, "line": s, "page": page}
                recs.append(last)
                continue
            if is_headword_like(s):
                fr, last = clean_fr(s), None
                continue
            print("ignoré p%s: %s" % (page, s), file=sys.stderr)
    return recs


def parse_part2(pgs):
    """Couples (kab, fr, page, ligne) de la partie II, pour contrôle."""
    out, in_part, head = [], False, None
    for page, lines in pgs:
        for raw in lines:
            s = raw.strip()
            if s == "PARTIE II":
                in_part = True
                continue
            if s == "INDEX":
                return out
            if not in_part:
                continue
            if s.startswith("►") and "/" in s:
                head = s[1:].split("/", 1)[1]
                head = re.sub(r"\(Muqel[^)]*\)", "", head)
                continue
            if s.startswith(BULLET) and head:
                out.append({"fr": clean_fr(head), "line": s.replace("►", MARK), "page": page})
                head = None
    return out


def build(path):
    pgs = pages(path)
    part1 = parse_part1(pgs)
    part2 = parse_part2(pgs)
    records, seen = [], set()

    def emit(raw, extra=False):
        for kab, forms, ann in parse_equiv(raw["line"]):
            if not kab or not KAB_OK.match(kab) or kab[0].isupper():
                if kab and kab != raw["fr"]:
                    print("rejeté p%s: %r ← %s" % (raw["page"], kab, raw["fr"]), file=sys.stderr)
                continue
            key = (kab, raw["fr"].lower())
            if key in seen:
                continue
            seen.add(key)
            forms = [f for f in forms if f and KAB_OK.match(f)]
            rec = {"kab": kab, "fr": raw["fr"], "forms": forms, "kind": "entry",
                   "domain": DOMAIN, "page": raw["page"], "source": SOURCE,
                   "needs_review": True}
            if ann:
                rec["ann"] = ann
            if extra:
                rec["note"] = "partie II seulement"
            records.append(rec)

    for r in part1:
        emit(r)
    # Partie II : on n'ajoute que les vedettes françaises absentes de la partie I ;
    # les autres écarts sont des variantes graphiques (tabder/tabdert…) signalées.
    def fr_key(fr):
        return re.sub(r"\s*\(.*?\)|[-' ]", "", fr.lower())
    fr1 = {fr_key(r["fr"]) for r in records}
    kabs1 = {r["kab"] for r in records}
    added, variants = [], []
    for r in part2:
        new = [k for k, _, _ in parse_equiv(r["line"]) if k not in kabs1]
        if not new:
            continue
        if fr_key(r["fr"]) in fr1:
            variants.append(r)
        else:
            added.append(r)
            emit(r, extra=True)
    return records, part1, part2, added, variants


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    txt = args[0] if args else DEFAULT_TXT
    out = Path(args[1]) if len(args) > 1 else DEFAULT_OUT
    records, p1, p2, added, variants = build(txt)
    with open(out, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"{len(records)} entrées → {out} (partie I : {len(p1)} lignes, "
          f"partie II : {len(p2)} lignes, {len(added)} ajoutées depuis la partie II)")
    if "--report" in sys.argv:
        for r in added:
            print("  ajout II p%s: %s | %s" % (r["page"], r["fr"], r["line"]))
        for r in variants:
            print("  variante II p%s: %s | %s" % (r["page"], r["fr"], r["line"]))
