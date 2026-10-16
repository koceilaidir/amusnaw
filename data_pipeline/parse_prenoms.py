"""Recueil de prénoms amazighs (M. A. Haddadou, HCA 2003)
→ data/lexicon_prenoms.jsonl

Le texte est relu directement dans le PDF, morceau par morceau (span) :
  - morceaux en police « AmazighTimesNewRoman* » : lettres kabyles (table Tira,
    sans l'heuristique « mot français » de kabyle_fonts.convert_span, qui
    laissait passer « O » = Ǧ : BEOE → BEǦE) ;
  - morceaux SymbolMT : ε / Ε ;
  - tout le reste (Times New Roman) est gardé tel quel : le français garde
    ses accents (c'est le contenu du fichier .raw.txt, sans réalignement).
Le découpage en lignes est celui de pdf_lines.py, donc identique aux fichiers
03-RECUEIL-DE-PRENOM(.raw).txt.

Fiche type :
    0293- IṬU,
    MC, Chl, fém., augmentatif de tiṭ ‘’œil’’, p. ext. ‘’fontaine’’

  python parse_prenoms.py [livre.pdf] [out.jsonl] [--check converted.txt]
"""
import json
import re
import sys
import unicodedata
from pathlib import Path

import pymupdf

from kabyle_fonts import TIRA, OVERSTRIKE

HERE = Path(__file__).resolve().parent
DEFAULT_PDF = Path("/mnt/user-data/uploads/pdf/2003/03-RECUEIL-DE-PRENOMS-AMAZIGHS/livre.pdf")
DEFAULT_OUT = HERE.parent / "data" / "lexicon_prenoms.jsonl"
SOURCE = "M. A. Haddadou, Recueil de prénoms amazighs, HCA 2003"
DOMAIN = "prénoms"

GREEK = str.maketrans({"Ε": "Ɛ", "ε": "ɛ"})

# Légende des abréviations (p. 4-5 du livre)
REGIONS = [
    (r"Ant\.?", "Antiquité (inscriptions)"),
    (r"M\s?\.\s?[Aa]\.?|MA\.?", "Moyen Âge (écrits)"),
    (r"B\.?", "commun au berbère"),
    (r"Chaw?\.?", "chaoui (Algérie)"),
    (r"Chl\.?", "chleuh (Maroc)"),
    (r"Ghd\.?", "ghadamsi (Libye)"),
    (r"K\.?", "kabyle (Algérie)"),
    (r"MC\.?", "tamaziɣt du Maroc central"),
    (r"Mzb\.?", "mozabite (Algérie)"),
    (r"T\s?w\.?", "touareg tawellemet (Azawagh, Niger)"),
    (r"T\s?Y\.?|Y\.?", "touareg tayert (Aïr, Niger)"),
    (r"Top?\.?|TO", "touareg de l'Ahaggar (Algérie)"),
    (r"Wrg\.?", "ouargli (Algérie)"),
    (r"Zng\.?", "zénaga (Mauritanie)"),
]
GENDERS = [(r"[Mm]sc\s?\.?|[Mm]asc\.?", "masc."), (r"[Ff]ém\.*", "fém."), (r"[Ee]tc\.?|M\.", None)]
TOKEN_END = r"(?=\s*[,;:]|\s|[‘’'\"«]|$)"
LEAD = re.compile(r"\s*(?:" + "|".join(f"(?P<r{i}>{p})" for i, (p, _) in enumerate(REGIONS))
                  + "|" + "|".join(f"(?P<g{i}>{p})" for i, (p, _) in enumerate(GENDERS))
                  + r")" + TOKEN_END + r"(?:\s*[,;:])*")

HEAD = re.compile(r"^(\d{3,4})\s*/?\s*-\s*(?:-\s*)?(.+)$")
ROOT = re.compile(r"^[B-DF-HJ-NP-TV-ZḌṬẒṢḤƔǦČƐ°]{1,7}$")   # racines : consonnes seules
# « à l. prb. », « à lprb : », « à lpb », « à lrpb. », « à lpbr. », « A lprb »
ALPRB = r"\b[àaA]\s?l\.?\s?(?:prb|pbr|rpb|pb)\.?\s*[,:;]?"
VOWELS = re.compile(r"[AEIOUaeiou]")


# ---------------------------------------------------------------- extraction
def convert(text, font):
    font = font.split("+", 1)[-1]
    if font.startswith("Amazigh"):
        for group, upper, lower in OVERSTRIKE:          # lettres en surimpression
            text = re.sub(f"[{re.escape(group)}]{{2,}}",
                          lambda m: upper if any(c.isupper() for c in m.group(0)) else lower,
                          text)
        return "".join(TIRA.get(ch, ch) for ch in text)
    if font.startswith("Symbol"):
        return text.translate(GREEK)
    if ("Bold" in font or "Italic" in font) and re.search(r"(?i)abôra", text):
        text = text.replace("ô", "o").replace("Ô", "O")  # touareg « abôra », index : ABORA
    return text


def pdf_pages(path):
    doc = pymupdf.open(path)
    for i, page in enumerate(doc):
        lines = []
        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                t = "".join(convert(s["text"], s["font"]) for s in line["spans"]).strip()
                if t:
                    lines.append(t.translate(GREEK))
        yield i + 1, lines


# ---------------------------------------------------------------- nettoyage
def cap_name(name):
    name = unicodedata.normalize("NFC", name.strip().strip(",").strip())
    return re.sub(r"[^\s\-]+", lambda m: m.group(0)[0].upper() + m.group(0)[1:].lower(), name)


def fix_quotes(s):
    # guillemets du livre : ‘’ … ’’ (variantes ‚’’, ‚’, ‘‘, parfois ’’ en ouvrant,
    # parfois une seule ’ en fermant) ; chaque groupe ouvre ou ferme selon l'état.
    out, opened, i = [], False, 0
    while i < len(s):
        m = re.match(r"[‚‘’']{2,3}|‚", s[i:])
        if m:
            out.append("»" if opened else "«")
            opened = not opened
            i += m.end()
            continue
        ch = s[i]
        if ch == "’" and opened and not s[i + 1:i + 2].isalpha():
            ch, opened = "»", False
        out.append(ch)
        i += 1
    s = "".join(out)
    if s.count("«") != s.count("»"):             # paires mal formées : on les retire
        s = s.replace("«", "").replace("»", "")
        return re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"(\w)«", r"\1 «", s)
    s = re.sub(r"«\s*", "« ", s)
    s = re.sub(r"\s*»", " »", s)
    return s


def first_gloss(fr):
    m = re.search(r"« ([^»]+) »", fr)
    return m.group(1) if m else None


def expand(text, prev, gender=None):
    pn = prev["kab"] if prev else None
    t = text
    if pn and re.fullmatch(r"d\.?\s?pr?\.?", t.strip()):     # « fém. dp » : féminin du précédent
        return {"fém.": "Féminin", "masc.": "Masculin"}.get(gender, "Forme") + f" de {pn}"
    t = re.sub(ALPRB, "à lire probablement ", t)
    if pn:
        t = re.sub(r"\b[Mm]s(?:qpr?|pq|q)\.?|\b[Mm]s\.(?=\s*$)", f"même sens que {pn}", t)
        t = re.sub(r"\bv\.\s?d\.\s?pr\.?|\bvdpr?\.?", f"variante de {pn}", t)
        t = re.sub(r"\bd\.\s?d\.\s?pr\.?|\bddpr?\.?", f"diminutif de {pn}", t)
        t = re.sub(r"\bd\.\s?pr\.?", f"de {pn}", t)
    t = re.sub(r"^[Vv]\. de\b", "variante de", t)
    t = re.sub(r"^[.?,\s]+(?=\w)", "", t)          # « ., à lire… »
    t = re.sub(r"\bar\.\s", "arabe ", t)
    t = re.sub(r"\b[Dd]im\.\s", "diminutif ", t)
    t = re.sub(r"\s+([,.;])", r"\1", t)
    t = re.sub(r"\s+", " ", t).strip(" ,;")
    # glose du précédent quand la fiche se résume au renvoi
    if prev and re.fullmatch(rf"(même sens que|variante de) {re.escape(pn)}\.?", t):
        g = first_gloss(prev["fr"])
        if g:
            t = t.rstrip(".") + f" : « {g} »"
    return t


def parse_desc(desc):
    """→ (régions, genre, reste du texte)."""
    regions, genders = [], []
    pos = 0
    while True:
        m = LEAD.match(desc, pos)
        if not m or m.end() == pos:
            break
        for k, v in m.groupdict().items():
            if v is None:
                continue
            i = int(k[1:])
            if k[0] == "r":
                lab = REGIONS[i][1]
                if lab not in regions:
                    regions.append(lab)
            else:
                lab = GENDERS[i][1]
                if lab and lab not in genders:
                    genders.append(lab)
        pos = m.end()
    gender = " et ".join(genders) if genders else None
    return regions, gender, desc[pos:].strip()


# ---------------------------------------------------------------- analyse
def parse(pdf):
    entries, cur, started = [], None, False
    for pno, lines in pdf_pages(pdf):
        if any(l.startswith("INDEX ALPHABETIQUE") for l in lines):
            break                                    # l'index commence sur cette page
        printed = None
        for ln in lines:
            s = ln.strip()
            if s.startswith("INDEX ALPHABETIQUE"):
                if cur:
                    entries.append(cur)
                return entries
            if printed is None and re.fullmatch(r"\d{1,3}", s):
                printed = int(s)
                continue
            m = HEAD.match(s)
            if m:
                started = True
                if cur:
                    entries.append(cur)
                no, rest = int(m.group(1)), m.group(2)
                name, _, after = rest.partition(",")
                cur = {"no": no, "name": name.strip(), "desc": after.strip(),
                       "page": printed if printed is not None else pno - 1}
                continue
            if not started:
                continue
            if ROOT.match(re.sub(r"[\s/()]", "", s)):  # racine (BDD, BHƔRT, GR / GWR, KF (T))
                if cur:
                    entries.append(cur)
                cur = None
                continue
            if cur:
                cur["desc"] = (cur["desc"] + " " + s).strip()
            else:
                print("ignoré p%s: %s" % (pno, s), file=sys.stderr)
    if cur:
        entries.append(cur)
    return entries


def index_genders(pdf):
    """Index final « ACNANI, msc., 202 » → {202: 'masc.'} (complète le genre)."""
    out, on = {}, False
    for _, lines in pdf_pages(pdf):
        on = on or any(l.startswith("INDEX ALPHABETIQUE") for l in lines)
        for s in lines:
            m = on and re.match(r".+?,\s*(msc|fém)\.?.*?,\s*(\d+)\s*$", s)
            if m:
                out.setdefault(int(m.group(2)), set()).add("masc." if m.group(1) == "msc" else "fém.")
    return {k: " et ".join(sorted(v, reverse=True)) for k, v in out.items()}


def build(pdf):
    raw = parse(pdf)
    idx_gender = index_genders(pdf)
    records, skipped, prev, last_no = [], [], None, 0
    for e in raw:
        no = e["no"]
        if no <= last_no:                       # « 0425- YUMER » entre 0724 et 0726
            no = last_no + 1
        last_no = no
        name = e["name"].translate(GREEK)
        regions, gender, rest = parse_desc(e["desc"])
        gender = gender or idx_gender.get(e["no"])
        rest = fix_quotes(rest)
        libyque = None
        if not VOWELS.search(name):             # nom libyque (consonnes seules)
            m = re.search(ALPRB + r"\s*([A-ZḌṬẒṢḤƔǦČƐ°()\-]{3,}(?![a-z])|[A-Z][a-zḍṭẓṣḥɣǧčɛ]{2,}\b)", rest)
            if not m:
                skipped.append((e["page"], e["name"], e["desc"][:60]))
                continue
            libyque, name = name, m.group(1).replace("(", "").replace(")", "")
        kab = cap_name(name)
        if not re.fullmatch(r"[A-ZḌṬẒṢḤƔǦČƐ][a-zčḍǧɣḥṛṣṭẓɛ°'’]*([ \-][A-ZḌṬẒṢḤƔǦČƐ][a-zčḍǧɣḥṛṣṭẓɛ°'’]*)*", kab):
            skipped.append((e["page"], e["name"], "nom suspect"))
            continue
        fr = expand(rest, prev, gender)
        fr = fr[0].upper() + fr[1:] if fr else fr
        if not fr:
            fr = {"masc.": "Prénom masculin", "fém.": "Prénom féminin"}.get(gender, "Prénom")
            meaning = False
        else:
            meaning = True
        rec = {"kab": kab, "fr": fr, "forms": [], "kind": "entry", "domain": DOMAIN,
               "page": e["page"], "source": SOURCE, "needs_review": True,
               "entry_no": no}
        if gender:
            rec["gender"] = gender
        if regions:
            rec["regions"] = regions
        if libyque:
            rec["libyque"] = libyque
        if not meaning:
            rec["no_meaning"] = True
        records.append(rec)
        prev = rec
    return records, skipped


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    pdf = args[0] if args else DEFAULT_PDF
    out = Path(args[1]) if len(args) > 1 else DEFAULT_OUT
    records, skipped = build(pdf)
    with open(out, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"{len(records)} prénoms → {out} ; {len(skipped)} écartés", file=sys.stderr)
    for s in skipped:
        print("  écarté p%s: %s | %s" % s, file=sys.stderr)
