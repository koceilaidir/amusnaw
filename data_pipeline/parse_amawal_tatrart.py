"""Parse « Amawal n tmaziɣt tatrart » (H. A. Mansouri, HCA 2004),
lexique Français → Tamaziɣt, en JSON Lines.

    python parse_amawal_tatrart.py [livre.pdf] [sortie.jsonl]

Le texte est relu directement depuis le PDF, caractère par caractère, avec la
police de chaque morceau :
  - côté français (Times New Roman) : texte brut, accents français intacts ;
  - côté kabyle (police AmazighTimesNewRoman) : table « Tira » de
    kabyle_fonts, appliquée sans heuristique « mot français » ni fusion des
    lettres doublées (ici « uîîun » = uṭṭun, une vraie gémination).
Les entrées commencent par un mot français en gras en début de ligne ; les
sous-entrées (« - action : … », « (- de la route) : … ») héritent du mot-vedette.
"""
import json
import re
import sys
from pathlib import Path

import pymupdf

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kabyle_fonts import SYMBOL, TIRA  # noqa: E402

PDF = "/mnt/user-data/uploads/pdf/2004/04-AMAWAL-n-Tmazi-t-tatrart-Francais-Tamazight/livre.pdf"
OUT = "/home/claude/amusnaw/data/lexicon_tatrart.jsonl"
SOURCE = "H. A. Mansouri, Amawal n tmaziɣt tatrart, HCA 2004"
DOMAIN = "mots nouveaux"
FIRST_PAGE = 8  # page PDF où commence la lettre A


# ---------------------------------------------------------------- extraction
def font_class(font: str) -> str:
    f = font.split("+", 1)[-1]
    if f.startswith("Symbol"):
        return "S"
    if "Amazigh" in f or "Bangle" in f:
        return "K"
    if "Bold" in f:
        return "B"
    return "R"


def page_lines(page):
    """Lignes de la page : liste de [(caractère brut, classe de police)].
    Une ligne contenant deux entrées (« … asugen. Concierge : … ») est coupée."""
    lines = []
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            chars = []
            for s in line["spans"]:
                c = font_class(s["font"])
                chars.extend((ch, c) for ch in s["text"])
            for part in split_midline(chars):
                part = strip_chars(part)
                if part:
                    lines.append(part)
    return lines


def strip_chars(chars):
    i, j = 0, len(chars)
    while i < j and chars[i][0].isspace():
        i += 1
    while j > i and chars[j - 1][0].isspace():
        j -= 1
    return chars[i:j]


def split_midline(chars):
    """Coupe avant un mot-vedette gras qui suit du texte non gras, avant « - »
    après un point, et avant « Mot : » (sous-sens) après un point."""
    cuts, prev, prev_cls, subs = [0], "", "", set()
    for i, (ch, c) in enumerate(chars):
        if ch.isspace():
            continue
        if prev_cls and prev_cls != "B" and c == "B" and ch.isupper():
            cuts.append(i)
        elif prev == "." and prev_cls != "B" and chars[i - 1][0].isspace() and c == "R":
            rest = raw_text(chars[i:])
            if ch in "-–":
                cuts.append(i)
            elif ch.isupper() and re.match(r"[^\W\d_][\w’' -]{0,30}?\s*:", rest) \
                    and all(cc != "K" for _, cc in chars[i:i + rest.index(":")]):
                cuts.append(i)
                subs.add(i)
        prev, prev_cls = ch, c
    cuts.append(len(chars))
    return [([("-", "R"), (" ", "R")] if a in subs else []) + chars[a:b]
            for a, b in zip(cuts, cuts[1:])]


LOCAL = {"Ô": "Ṛ"}
OPEN, CLOSE = "⟦", "⟧"  # balisent le texte hors police kabyle (notes françaises)


def kab_text(chars) -> str:
    """Partie kabyle : conversion Tira des morceaux en police amazighe ; les
    mots écrits dans une autre police sont entourés de ⟦ ⟧."""
    out, run = [], []

    def flush():
        if run:
            t = "".join(run)
            out.append(OPEN + t + CLOSE if any(x.isalpha() for x in t) else t)
            run.clear()

    for i, (ch, c) in enumerate(chars):
        if c == "K":
            flush()
            if ch in "ùÙ" and i + 1 < len(chars) and chars[i + 1][0] in "mM":
                continue  # « ù » parasite devant m
            out.append(LOCAL.get(ch) or TIRA.get(ch, ch))
        elif c == "S":
            flush()
            out.append(SYMBOL.get(ch, ch))
        elif ch.isalpha() or run:
            run.append(ch)
        else:
            out.append(ch)
    flush()
    s = "".join(out).replace("$", "ɣ").replace("", "ɛ")
    # ⟦ ⟧ n'englobent pas les espaces/ponctuation finaux
    s = re.sub(OPEN + r"([^" + CLOSE + r"]*?)([\s.,;:)\]]*)" + CLOSE, lambda m: OPEN + m.group(1) + CLOSE + m.group(2), s)
    return s


def unmark(s: str) -> str:
    return s.replace(OPEN, "").replace(CLOSE, "")


def raw_text(chars) -> str:
    return "".join(ch for ch, _ in chars)


# ---------------------------------------------------------------- découpage
FORM_MARK = re.compile(r"^\(\s*f\s*\.\s*([fp])\s*\.\s*\)", re.I)


def is_section_letter(line) -> bool:
    t = raw_text(line).strip()
    return len(t) == 1 and t.isupper() and line[0][1] != "K"


def collect_entries(doc):
    """Regroupe les lignes en entrées : dict(kind=main|sub, page, chars)."""
    entries = []
    cur = None

    def opened_sense(e):  # la partie française de l'entrée courante est close ?
        return any(ch == ":" for ch, _ in e["chars"]) or any(
            c == "K" and ch.isalpha() for ch, c in e["chars"])

    for pno in range(FIRST_PAGE - 1, doc.page_count):
        lines = page_lines(doc[pno])
        if lines and raw_text(lines[0]).strip().isdigit():
            lines = lines[1:]  # numéro de page
        for line in lines:
            t = raw_text(line)
            if t.strip() == "BIBLIOGRAPHIE":
                if cur:
                    entries.append(cur)
                return entries
            if is_section_letter(line):
                continue
            first_cls = line[0][1]
            start = None
            if first_cls == "B" and t[:1] not in "([-–":
                start = "main"
            elif cur is not None and opened_sense(cur) and not FORM_MARK.match(t) and (
                    t[:1] in "-–" or (first_cls in "RB" and t[:1] == "(")):
                start = "sub"
            if start:
                if cur:
                    entries.append(cur)
                cur = {"kind": start, "page": pno + 1, "chars": list(line)}
            elif cur is not None:
                cur["chars"].append((" ", "R"))
                cur["chars"].extend(line)
    if cur:
        entries.append(cur)
    return entries


# ---------------------------------------------------------------- analyse
def split_top(s: str, seps: str):
    parts, depth, buf = [], 0, []
    for ch in s:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        if ch in seps and depth == 0:
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    parts.append("".join(buf))
    return parts


def norm_space(s: str) -> str:
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"\(\s+", "(", s)
    s = re.sub(r"\s+\)", ")", s)
    return s


def fix_case(s: str) -> str:
    # ɣ / ɛ n'ont été convertis qu'en minuscule : on les ignore
    letters = [c for c in s if c.isalpha() and c not in "ɣɛ"]
    if len(letters) > 1 and all(c.isupper() for c in letters):
        return s.lower()
    return s


def split_fr_kab(chars):
    """Coupe l'entrée en (français brut, kabyle converti)."""
    # 1re lettre en police kabyle hors parenthèses (« (fem.) », « ( assez -) »
    # sont parfois tapés en police kabyle mais restent du français)
    first_k, colon, depth = None, None, 0
    for i, (ch, c) in enumerate(chars):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        elif ch == ":" and depth == 0:
            colon = i
            break
        elif first_k is None and depth == 0 and c == "K" and ch.isalpha():
            first_k = i
    if colon is not None and (first_k is None or colon < first_k):
        return raw_text(chars[:colon]), kab_text(chars[colon + 1:])
    if first_k is not None:
        return raw_text(chars[:first_k]), kab_text(chars[first_k:])
    return raw_text(chars), ""


DASH = re.compile(r"(?<![\w’'])[-–](?![\w])")


def clean_fr(s: str) -> str:
    s = norm_space(s).strip(" :;,.")
    while s.startswith("(") and s.count("(") > s.count(")"):
        s = s[1:].strip()
    if s.count("(") > s.count(")"):
        s += ")"
    return s


def bare_word(fr: str) -> str:
    return re.split(r"\s*\(", fr, maxsplit=1)[0].strip()


def sub_fr(parent_fr: str, s: str) -> str:
    s = clean_fr(s)
    s = re.sub(r"^[-–]\s*", "", s).strip()
    if not s:
        return parent_fr
    word = bare_word(parent_fr)
    inner = s
    while (m := re.fullmatch(r"\((.*)\)", inner)):
        inner = m.group(1).strip()
    if inner.rstrip(".").lower() in ("fem", "fém", "f"):
        return f"{word} (féminin)"
    if DASH.search(inner):
        w = word[:1].lower() + word[1:]
        res = DASH.sub(w, inner, count=1)
        res = re.sub(r"\s+", " ", res).strip()
        return res[:1].upper() + res[1:]
    return f"{word} ({inner})"


GRAM_NOTE = re.compile(r"\b(masc|fém|fem|plur|sing|adj|pl\.|n\.|v\.|f\.\s*d|e\.\s*l)|\+", re.I)


def fix_ur(kab: str) -> str:
    """« SLEḌ (ISLEḌ, (UR) ISLIḌ » / « SDERFI (UR) ISDERFI, …) » : parenthèses
    parasites autour de la négation."""
    out, depth, i = [], 0, 0
    while i < len(kab):
        m = re.match(r"\(\s*(ur)\s*\)", kab[i:], re.I)
        if m:
            out.append(m.group(1) if depth else "(" + m.group(1))
            if not depth:
                depth = 1
            i += m.end()
            continue
        ch = kab[i]
        depth += ch == "("
        depth -= ch == ")" and depth > 0
        out.append(ch)
        i += 1
    return "".join(out)


def parse_kab(kab: str):
    """→ liste de (terme, formes, note)."""
    kab = re.sub(r"\[\s*\d+\s*\]", " ", kab)
    kab = kab.replace("[", "(").replace("]", ")")
    kab = re.sub(r"\.\s*\w\s*$", ".", kab.strip())  # lettre de section collée : « tasnawit . M »
    kab = re.sub(r"[{}]\s*\d*", " ", kab)
    kab = fix_ur(norm_space(kab))
    out = []
    extra_note = ""
    # « ahareg (ihurag) = exercices physiques » ; « talalit (date et lieu de -) :
    # azemz … » : ce qui suit « = » ou un « : » de premier niveau n'est pas
    # un équivalent du mot-vedette → note
    for sep in ("=", ":"):
        parts = split_top(kab, sep)
        if len(parts) > 1:
            kab = parts[0]
            extra_note = norm_space(unmark(sep.join(parts[1:]))).strip(" .;,)")
            if sep == "=":
                extra_note = "= " + extra_note
            break
    # marques de formes dérivées : (F.F.) forme factitive, (f.p.) passive
    chunks = re.split(r"(\(\s*f\s*\.\s*[fp]\s*\.\s*\))", kab, flags=re.I)
    note = ""
    for chunk in chunks:
        m = FORM_MARK.match(chunk.strip())
        if m:
            note = "forme factitive" if m.group(1).lower() == "f" else "forme passive"
            continue
        for piece in split_top(chunk, ";"):
            piece_start = len(out)
            for term in split_top(piece, ","):
                term = term.strip(" .:;,-–")
                if not term:
                    continue
                if term.count(")") > term.count("("):
                    # « SILEɣ (ISSALEɣ), ISSALAɣ, ASILEɣ) » : parenthèse mal fermée
                    # dans la source → ces termes sont des formes du premier
                    tail = term.replace(")", "").strip()
                    if len(out) > piece_start:
                        h, f, n = out[piece_start]
                        extra = [t for t, _, _ in out[piece_start + 1:]]
                        del out[piece_start + 1:]
                        out[piece_start] = (h, f + extra + [fix_case(unmark(tail))], n)
                        continue
                    words = tail.split()
                    term = words[0] + (" (" + ", ".join(words[1:]) + ")" if len(words) > 1 else "")
                forms, notes = [], [note] if note else []
                for par in re.findall(r"\(([^()]*)\)", term):
                    if OPEN in par or GRAM_NOTE.search(par):
                        notes.append(norm_space(unmark(par)))
                        continue
                    forms += [f.strip(" .;,") for f in re.split(r"[,;]", par)]
                head = re.sub(r"\([^()]*\)?", " ", term)
                # mots en police française dans le terme → note
                for seg in re.findall(OPEN + r"([^" + CLOSE + r"]*)" + CLOSE, head):
                    notes.append(seg.strip())
                head = re.sub(OPEN + r"[^" + CLOSE + r"]*" + CLOSE, " ", head)
                head = norm_space(unmark(head)).strip(" .:;,-–")
                forms = [norm_space(unmark(f)) for f in forms]
                if not head:
                    continue
                head = fix_case(head)
                forms = [fix_case(f) for f in forms if f and not f.isdigit()]
                if head[:1].islower():
                    forms = [f[:1].lower() + f[1:] if f[1:2].islower() else f for f in forms]
                out.append((head, forms, "; ".join(n for n in notes if len(n) > 1)))
    if extra_note:
        out = [(h, f, "; ".join(x for x in (n, extra_note) if x)) for h, f, n in out]
    return out


def valid(kab: str, fr: str) -> bool:
    if not kab or not fr:
        return False
    if len(kab.split()) > 6 or re.search(r"[\d=:]", kab):
        return False
    if not re.search(r"[a-zA-Zɣḍṭẓṛṣḥɛǧč]", kab):
        return False
    # un mot français évident dans le kabyle → probablement un débordement
    if re.search(r"\b(le|la|les|des|du|une|est|dans|pour)\b", kab):
        return False
    return True


def main(pdf=PDF, out=OUT):
    doc = pymupdf.open(pdf)
    entries = collect_entries(doc)
    records, parent_fr = [], ""
    for e in entries:
        fr_raw, kab = split_fr_kab(e["chars"])
        if e["kind"] == "main":
            fr = clean_fr(fr_raw)
            parent_fr = fr
        else:
            fr = sub_fr(parent_fr, fr_raw)
        for term, forms, note in parse_kab(kab):
            if not valid(term, fr) or re.search(r"\(ex\b", fr):
                continue
            rec = {"kab": term, "fr": fr, "forms": forms}
            if note:
                rec["note"] = note
            rec.update({"kind": "entry", "domain": DOMAIN, "page": e["page"],
                        "source": SOURCE, "needs_review": True})
            records.append(rec)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"{len(entries)} entrées, {len(records)} enregistrements → {out}")


if __name__ == "__main__":
    main(*sys.argv[1:3])
