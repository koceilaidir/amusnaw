"""Lexiques juridiques du HCA (M. Z. Benramdane) → paires kabyle ↔ français.

Sources (texte déjà extrait des PDF, converti en Unicode, une page = « ==== p N ») :
  - Amawal azerfan, Tamaziɣt-Tafransist (HCA 2013)
  - Amawal n tutlayt tazerfant / Lexique de la langue juridique (HCA 2021)

Le corps des deux livres est une suite continue « Tamaziɣt «Français», … »
classée par racines (« GFR », « 070. GFR »). Le livre de 2021 contient aussi un
index français → tamazight (« Absence [Iba, pl. Ibaten]: 001; 003. ») : on le lit
dans l'autre sens pour que `kab` soit toujours le côté tamazight.

`page` = numéro de page physique du PDF (1 = première page du fichier), pas le
numéro imprimé.

Usage :
  python parse_juridique.py [txt_2013] [txt_2021] [../data/lexicon_juridique.jsonl]
"""

import json
import re
import sys
from collections import Counter
from pathlib import Path

SRC_2013 = "M. Z. Benramdane, Amawal azerfan, HCA 2013"
SRC_2021 = "M. Z. Benramdane, Amawal n tutlayt tazerfant, HCA 2021"

DEFAULT_TXT = Path("/tmp/claude-0/-home-claude/4d0a5699-ac07-5264-8a09-fea839f824ef/scratchpad/txt")
DEFAULT_OUT = Path(__file__).resolve().parent.parent / "data" / "lexicon_juridique.jsonl"

ROOT_LETTERS = "A-ZČḌƐƔǦḤṚṢṬẒ"
RE_PAGE = re.compile(r"^==== p (\d+)\s*$")
RE_HEADER = [
    re.compile(r"^-\s*\d+\s*-$"),                                     # « - 49 - »
    re.compile(r"^\d{1,3}$"),                                         # numéro de page nu
    re.compile(r"^Amawal n tutlayt tazerfant\s*:\s*Lexique de la langue juridique$"),
    re.compile(r"^(TERMINOLOGIE JURIDIQUE|AMAZIGH-FRANÇAIS|INDEX RÉCAPITULATIF|FRANÇAIS-AMAZIGH)$"),
    re.compile(rf"^(\d{{3}}\.\s*)?[{ROOT_LETTERS}]{{1,6}}$"),         # racine « GFR », « 070. GFR », lettre « B »
]

# ---------------------------------------------------------------- pages


def read_pages(path):
    """→ liste de (n° page, [lignes])."""
    pages, cur = [], None
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        m = RE_PAGE.match(line)
        if m:
            cur = (int(m.group(1)), [])
            pages.append(cur)
        elif cur is not None:
            cur[1].append(line.replace("­", "").rstrip())
    return pages


def section(pages, start_marker, end_marker, first_page=1):
    """Lignes (page, texte) entre la ligne `start_marker` (exclue) et `end_marker` (exclue)."""
    out, on, footnote = [], False, False
    for pno, lines in pages:
        if pno < first_page:
            continue
        for ln in lines:
            s = ln.strip()
            if not on:
                on = s == start_marker
                continue
            if s == end_marker:
                return out
            if not s or any(r.match(s) for r in RE_HEADER):
                continue
            # note de bas de page « 76 Les chiffres en gras … » (jusqu'au point final)
            if footnote or re.match(r"^\d{1,3} [A-ZÉ][a-zé]+ [a-zé]", s):
                footnote = not s.endswith(".")
                continue
            out.append((pno, s))
    return out


# ---------------------------------------------------------------- recollage


def build_vocab(*texts):
    return Counter(w.lower() for t in texts for w in re.findall(r"[\w’'-]+", t))


def join_lines(lines, vocab):
    """Recolle les lignes en un flux unique ; renvoie (texte, [(offset, page)])."""
    buf, marks = "", []
    for pno, s in lines:
        marks.append((len(buf), pno))
        if buf.endswith("-") and re.search(r"\w-$", buf) and re.match(r"\w", s):
            # mot coupé en fin de ligne : on garde le tiret s'il fait partie du mot
            left = re.search(r"([\w’'-]+)-$", buf).group(1)
            right = re.match(r"[\w’'-]+", s).group(0)
            joined, hyph = (left + right).lower(), (left + "-" + right).lower()
            if vocab[joined] > 0 and vocab[hyph] == 0 and not right[0].isupper():
                buf = buf[:-1]
            buf += s
        else:
            buf += (" " if buf else "") + s
    return buf, marks


def page_at(marks, offset):
    pno = marks[0][1]
    for off, p in marks:
        if off > offset:
            break
        pno = p
    return pno


# ---------------------------------------------------------------- nettoyage

RE_SPACES = re.compile(r"\s+")
FR_WORDS = set("""le la les l’ l' un une des du de d’ d' et ou en au aux pour par sur dans avec sans contre
est être fait action""".split())


def clean(s):
    s = RE_SPACES.sub(" ", s.replace("'", "’")).strip()
    s = re.sub(r"\s+([,;.:)\]])", r"\1", s)
    s = re.sub(r"([(\[])\s+", r"\1", s)
    s = s.strip(" ,;:.-–—")
    # parenthèses / crochets orphelins
    if s.count("(") < s.count(")") and s.endswith(")"):
        s = s[:-1].rstrip()
    if s.count("[") != s.count("]"):
        s = s.replace("[", "").replace("]", "")
    return s


def kab_headword(seg):
    """« Asegfer, pl. Isegfar, fém. … » → « Asegfer » ; renvoie aussi les variantes séparées par « ; »."""
    seg = clean(seg)
    seg = re.split(r",?\s*\b(?:pl|fém|sg|masc)(?:\.|\s)", seg)[0]
    seg = re.sub(r"\s*\((?:ɣer|i|n|seg|di|s)\)", "", seg)   # « Amassaɣ (ɣer) » : préposition régie
    parts = []
    for p in seg.split(";"):
        p = clean(p)
        sub = [clean(x) for x in p.split(",")]
        # « Iwanaken Yedduklen, Iwunak Yedduklen » : variantes ; mais
        # « … tilsanin, n usileɣ d yiẓuyar » : une seule expression
        if len(sub) > 1 and all(x[:1].isupper() for x in sub):
            parts += sub
        else:
            parts.append(p)
    return [p for p in parts if p]


def looks_french(kab):
    words = re.findall(r"[\w’']+", kab.lower())
    if not words:
        return True
    if re.search(r"[éèêàâùûôçœ]", kab.lower()):
        return True
    return sum(w in FR_WORDS for w in words) >= max(1, len(words) // 2) and not re.search("[ɣḍṭẓṛṣḥɛčǧ]", kab.lower())


# ---------------------------------------------------------------- corps (tamazight «français»)

RE_ENTRY = re.compile(r"(?P<kab>[^«»]*?)«(?P<fr>[^«»]*)»")


class Pair:
    """Équivalent minimal d'un `re.Match` pour les paires sorties du scanner."""

    def __init__(self, kab, fr, kab_start, fr_start):
        self._g = {"kab": kab, "fr": fr}
        self._s = {"kab": kab_start, "fr": fr_start}

    def group(self, k):
        return self._g[k]

    def start(self, k):
        return self._s[k]


def scan_pairs(text, problems):
    """Découpe « kab «fr», … » en tenant compte des guillemets imbriqués :
    « Taggayin n yisensa «Catégories des hôtels (Taggayt tamenzut: … «1ère catégorie: …», …)» »
    → (Taggayin n yisensa, Catégories des hôtels) + les paires internes."""
    pairs, depth, seg_start, open_at = [], 0, 0, None
    for i, ch in enumerate(text):
        if ch == "«":
            if depth == 0:
                open_at = i
            depth += 1
        elif ch == "»" and depth:
            depth -= 1
            if depth == 0:
                kab, fr = text[seg_start:open_at], text[open_at + 1:i]
                if "«" in fr:
                    problems["paires imbriquées (bloc)"] += 1
                    cut = re.search(r"\s*(?::\s*\[|\[|\()", fr)
                    outer = fr[:cut.start()] if cut else fr[:fr.index("«")]
                    pairs.append(Pair(kab, outer, seg_start, open_at + 1))
                    inner_off = open_at + 1 + (cut.end() if cut else 0)
                    inner = text[inner_off:i]
                    for m in RE_ENTRY.finditer(inner):
                        k = re.sub(r"^[\s,;.\[(]*", "", m.group("kab"))
                        if not re.search(r"[a-zɣḍṭẓṛṣḥɛčǧ]{2}", k):   # codes « D.Ɣ.12 «E.C.12» »
                            problems["codes d'abréviation ignorés"] += 1
                            continue
                        pairs.append(Pair(k, m.group("fr"), inner_off + m.start("kab"), inner_off + m.start("fr")))
                else:
                    pairs.append(Pair(kab, fr, seg_start, open_at + 1))
                seg_start = i + 1
    if depth:
        problems["guillemet « non fermé"] += 1
    return pairs


def clean_fr(fr):
    fr = clean(fr)
    # « s’Abstenir de », « se Jurer » → « S’abstenir de », « se jurer »
    fr = re.sub(r"\b(s’|s'|se )([A-ZÉÈÊÀ])", lambda m: m.group(1) + m.group(2).lower(), fr)
    if fr[:1].islower():
        fr = fr[0].upper() + fr[1:]
    return fr


def parse_body(text, marks, source, problems):
    out = []
    for m in scan_pairs(text, problems):
        raw_kab, fr = m.group("kab"), clean_fr(m.group("fr"))
        # le segment tamazight commence après le dernier « », » ; on enlève un reste
        # « , fém. Tanabayt, pl. … » rattaché à l'entrée précédente
        raw_kab = re.sub(r"^\s*[,.;]?\s*", "", raw_kab)
        raw_kab = re.sub(r"^(?:(?:pl|fém|sg|masc)\.\s+[^,]+,\s*)+", "", raw_kab)
        if not fr:
            problems["fr vide"] += 1
            continue
        heads = kab_headword(raw_kab)
        if not heads:
            problems["kab vide"] += 1
            continue
        for kab in heads:
            if looks_french(kab):
                problems["kab ressemble au français"] += 1
                continue
            out.append(dict(kab=kab, fr=fr, page=page_at(marks, m.start("fr")), source=source))
    return out


# ---------------------------------------------------------------- index 2021 (français [tamazight]: renvois)

RE_INDEX = re.compile(r"(?P<fr>[^\[\]:;]+?)\s*\[(?P<kab>[^\[\]]+)\]\s*:")


def parse_index(text, marks, source, problems):
    out = []
    for m in RE_INDEX.finditer(text):
        fr = m.group("fr")
        fr = re.sub(r"^[\d\s.;,]*", "", fr)                 # renvois de l'entrée précédente
        # marques de flexion « Absolu (s, e) », « Minier (ière, s) », « Maternel (s, le, les) »
        fr = clean(re.sub(r"\s*\((?:[a-zéèêàç]{1,7})(?:,\s*[a-zéèêàç]{1,7})*\)", "", fr))
        # « Abstenir de (s’) » → « S’abstenir de »
        mm = re.match(r"^(.*?)\s*\((s’|s'|se)\)\s*(.*)$", fr)
        if mm:
            verb = (mm.group(1) + " " + mm.group(3)).strip()
            sep = " " if mm.group(2) == "se" else ""
            if mm.group(2) == "se" and verb[:1].lower() in "aeéèêiouh":
                mm2, sep = "s’", ""
            else:
                mm2 = mm.group(2)
            fr = mm2.capitalize() + sep + verb[0].lower() + verb[1:]
        fr = clean_fr(fr)
        if not fr:
            problems["index: fr vide"] += 1
            continue
        for kab in kab_headword(m.group("kab")):
            if looks_french(kab):
                problems["index: kab ressemble au français"] += 1
                continue
            out.append(dict(kab=kab, fr=fr, page=page_at(marks, m.start("kab")), source=source))
    return out


# ---------------------------------------------------------------- main


def main():
    a = sys.argv[1:]
    txt13 = Path(a[0]) if len(a) > 0 else DEFAULT_TXT / "01-AMAWAL-azerfan-Ta.txt"
    txt21 = Path(a[1]) if len(a) > 1 else DEFAULT_TXT / "03-AMAWAL-N-TUTLAYT-.txt"
    out_path = Path(a[2]) if len(a) > 2 else DEFAULT_OUT

    p13, p21 = read_pages(txt13), read_pages(txt21)
    body13 = section(p13, "AMAZIGH-FRANÇAIS", "RÉFÉRENCES BIBLIOGRAPHIQUES", first_page=40)
    body21 = section(p21, "AMAZIGH-FRANÇAIS", "CHAPITRE DEUXIÈME", first_page=52)
    index21 = section(p21, "FRANÇAIS-AMAZIGH", "RÉFÉRENCES BIBLIOGRAPHIQUES", first_page=528)

    vocab = build_vocab(*(s for _, s in body13 + body21))
    problems = Counter()
    recs = []
    # ordre = priorité au dédoublonnage : 2021 (corps, puis index) avant 2013
    for lines, src, fn in ((body21, SRC_2021, parse_body), (index21, SRC_2021, parse_index),
                           (body13, SRC_2013, parse_body)):
        text, marks = join_lines(lines, vocab)
        recs += fn(text, marks, src, problems)

    seen, final = set(), []
    for r in recs:
        if "«" in r["fr"] or "»" in r["fr"] or "«" in r["kab"] or "»" in r["kab"]:
            problems["guillemets restants"] += 1
            continue
        key = (r["kab"].casefold(), r["fr"].casefold())
        if key in seen:
            continue
        seen.add(key)
        n = len(r["kab"].split())
        final.append({"kab": r["kab"], "fr": r["fr"], "kind": "term" if n <= 3 else "phrase",
                      "domain": "droit", "page": r["page"], "source": r["source"], "needs_review": True})

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        for r in final:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    kinds = Counter(r["kind"] for r in final)
    srcs = Counter(r["source"] for r in final)
    print(f"{len(recs)} paires lues, {len(final)} après dédoublonnage → {out_path}")
    print(" ", dict(kinds))
    print(" ", dict(srcs))
    for k, v in problems.items():
        print(f"  ! {k}: {v}")


if __name__ == "__main__":
    main()
