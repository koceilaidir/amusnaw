"""Parse le « Lexique des sciences de la terre » (Y. Ahmed Zayed) suivi du
« Lexique animal » (R. Kahlouche), HCA 2004, Kabyle → Français, en JSON Lines.

    python parse_amawal_akal.py [livre.pdf] [sortie.jsonl]

Comme pour parse_amawal_tatrart.py, le texte est relu depuis le PDF avec la
police de chaque caractère : la table « Tira » n'est appliquée qu'aux morceaux
en police amazighe, le français (Times New Roman) reste brut.

1re partie (sciences de la terre, p. 3-21) : entrées
   « Azaɣar, izuɣar, tazaɣart, tizuɣar : plaine, petite plaine. Commentaire… »
2e partie (animaux, p. 24-42) : le corps du lexique est très libre (vedette,
   « glose », variantes dialectales, proverbes) ; on part donc du récapitulatif
   « Champ lexical des animaux domestiques » (p. 39-42, « mot : sens ») et on
   rattache à chaque mot le passage correspondant du corps (dans le même ordre)
   comme note.
"""
import difflib
import json
import re
import sys
import unicodedata
from pathlib import Path

import pymupdf

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kabyle_fonts import SYMBOL, TIRA  # noqa: E402
from parse_amawal_tatrart import font_class, raw_text, strip_chars  # noqa: E402

PDF = "/mnt/user-data/uploads/pdf/2004/03-Amawal-lexique-de-sciences-de-la-terre-suivi-de-lexique-anim/livre.pdf"
OUT = "/home/claude/amusnaw/data/lexicon_terre_animaux.jsonl"
SOURCE = "A. Z. Yeddir, Lexique des sciences de la terre et lexique animal, HCA 2004"
EARTH_PAGES = range(3, 22)      # pages PDF (1-indexées)
ANIMAL_BODY = range(24, 39)
ANIMAL_SUMMARY = range(39, 43)
NOTE_MAX = 400


# ---------------------------------------------------------------- texte
def page_lines(page):
    lines = []
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            chars = []
            for s in line["spans"]:
                c = font_class(s["font"])
                chars.extend((ch, c) for ch in s["text"])
            chars = strip_chars(chars)
            if chars:
                lines.append(chars)
    if lines and raw_text(lines[0]).strip().isdigit():
        lines = lines[1:]
    return lines


def conv(chars) -> str:
    """Texte mixte : kabyle converti (police amazighe), français brut."""
    out = []
    for ch, c in chars:
        if c == "K":
            out.append(TIRA.get(ch, ch))
        elif c == "S":
            out.append(SYMBOL.get(ch, ch))
        else:
            out.append(ch)
    s = "".join(out).replace("", "ɛ").replace("ε", "ɛ")
    return s


def kab_word(chars) -> str:
    """Mot kabyle : on applique aussi la table aux caractères $ / ε tapés hors
    police amazighe."""
    s = conv(chars).replace("$", "ɣ").replace("°", "ʷ")
    return s


def norm_space(s: str) -> str:
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"\(\s+", "(", s)
    s = re.sub(r"\s+\)", ")", s)
    s = re.sub(r"\s+([,.;])", r"\1", s)
    return s


def lower_first(w: str) -> str:
    return w[:1].lower() + w[1:]


def cut(s: str, n: int) -> str:
    if len(s) <= n:
        return s
    s = s[:n].rsplit(" ", 1)[0].rstrip(" ,;:")
    return s + "…"


def record(kab, fr, forms, note, domain, page):
    rec = {"kab": kab, "fr": fr, "forms": forms}
    if note:
        rec["note"] = note
    rec.update({"kind": "entry", "domain": domain, "page": page,
                "source": SOURCE, "needs_review": True})
    return rec


def valid(kab: str, fr: str) -> bool:
    return bool(kab and fr and len(kab.split()) <= 6 and not re.search(r"\d", kab)
                and re.search(r"[a-zɣḍṭẓṛṣḥɛǧč]", kab, re.I))


# ---------------------------------------------------------------- 1re partie
FUNC_END = re.compile(r"(\b(de|du|des|la|le|les|à|en|et|ou|sur|dans|par|avec|un|une|l’|d’)|[,:–-])$", re.I)
LABEL = re.compile(
    r"^(?:(?:nom|substantif|adjectif|verbe|adj\.)\b[^;,:.]*?(?:\.\s*)?(?:[;,:]|\.(?=\s)|$)"
    r"|sans\s+plu(?:riel)?\s*\.?\s*[;,:]?)\s*", re.I)


def is_head_prefix(chars) -> bool:
    depth, letters = 0, []
    for ch, c in chars:  # lettres hors parenthèses
        depth += ch == "("
        depth -= ch == ")" and depth > 0
        if ch.isalpha() and not depth:
            letters.append((ch, c))
    if not letters or letters[0][1] not in "KB":
        return False
    kb = sum(1 for _, c in letters if c in "KBS")
    if kb / len(letters) < 0.8:
        return False
    items = [x.strip() for x in re.split(r",|\bou\b", re.sub(r"\(.*?\)", " ", raw_text(chars)))
             if x.strip()]
    return 1 <= len(items) <= 6 and all(len(x.split()) <= 2 for x in items)


def find_head(lines, i):
    """Si une entrée commence à la ligne i, renvoie (fin, chars de la vedette,
    chars après « : »)."""
    head = []
    for j in range(i, min(i + 4, len(lines))):
        line = lines[j]
        t = raw_text(line)
        k = t.find(":")
        if k >= 0:
            head += line[:k]
            return (j, head, line[k + 1:]) if is_head_prefix(head) else None
        head += line + [(" ", "R")]
        if not re.search(r"(,|\bou)$", t.rstrip()):
            return None
    return None


def split_gloss(body: str):
    """→ (glose courte, étiquettes grammaticales, reste du commentaire)."""
    labels = []
    while True:
        m = LABEL.match(body)
        if not m or not m.group(0).strip():
            break
        labels.append(m.group(0).strip(" ;,:"))
        body = body[m.end():]
    m = re.search(r"[.?!](?=\s+[«A-ZÀ-Ý(]|\s*$)", body)
    end = m.end() if m else len(body)
    gloss, rest = body[:end], body[end:].strip()
    gloss = gloss.rstrip(" .")
    d = re.search(r"\bdésigne(?: également)?\s+(.*)", gloss)
    if d and len(gloss) > 60:
        gloss = d.group(1)
    if len(gloss) > 90 and ";" in gloss:
        head, tail = gloss.split(";", 1)
        gloss, rest = head.strip(), (tail.strip() + ". " + rest).strip()
    gloss = cut(gloss.strip(" ,;:"), 90)
    if not gloss and labels:  # « nom féminin diminutif du précédent. »
        gloss, labels = labels[-1], labels[:-1]
    return gloss, labels, rest


def parse_earth(doc):
    lines, pages = [], []
    for p in EARTH_PAGES:
        for line in page_lines(doc[p - 1]):
            t = raw_text(line).strip()
            if t.startswith(("Lexique des sciences", "Par :")):
                continue
            if t.startswith("Bibliographie"):
                break
            lines.append(line)
            pages.append(p)
    # repérage des débuts d'entrées
    starts = []
    i = 0
    while i < len(lines):
        prev = raw_text(lines[i - 1]).rstrip() if i else "."
        h = None if FUNC_END.search(prev) else find_head(lines, i)
        if h:
            starts.append((i, h))
            i = h[0] + 1
        else:
            i += 1
    recs = []
    for n, (i, (j, head, after)) in enumerate(starts):
        nxt = starts[n + 1][0] if n + 1 < len(starts) else len(lines)
        body_chars = list(after)
        for line in lines[j + 1:nxt]:
            body_chars += [(" ", "R")] + line
        body = norm_space(conv(body_chars))
        items = [norm_space(re.sub(r"\(.*?\)", " ", x)) for x in
                 re.split(r",|\bou\b", kab_word(head))]
        items = [x for x in items if x]
        if not items:
            continue
        kab = lower_first(items[0])
        forms = items[1:]
        gloss, labels, rest = split_gloss(body)
        gloss = gloss.rstrip(" .")
        note = "; ".join(labels)
        if rest:
            note = (note + ". " if note else "") + rest
        # « nom féminin diminutif du précédent » → on reprend le sens précédent
        ref = re.search(r"(même sens qu[e’]|diminutif d[ue]|féminin d[ue])\s*(?:l[e’]\s*)?(précédent|premier)\s*$", gloss)
        if ref and recs:
            prev = recs[-1]
            note = f"{gloss} ({prev['kab']}). " + note
            kind = ref.group(1)
            gloss = prev["fr"] + (" (diminutif)" if kind.startswith("diminutif")
                                  else " (féminin)" if kind.startswith("féminin") else "")
        m = re.match(r"(diminutif|féminin) d[ue] (?:premier|précédent),\s*(.+)", gloss)
        if m:  # « diminutif du premier, colline »
            note = (gloss[:m.start(2)].rstrip(" ,") + ". " + note).strip()
            gloss = f"{m.group(2)} ({m.group(1)})"
        note = norm_space(note).strip(" .;") + ("." if note.rstrip().endswith(".") else "")
        recs.append(record(kab, gloss, forms, cut(note, NOTE_MAX), "sciences de la terre", pages[i]))
    return recs


# ---------------------------------------------------------------- 2e partie
FR_FIX = {"brebris": "brebis", "oeuf": "œuf", "boeuf": "bœuf", "boeufs": "bœufs"}
BASE = str.maketrans("ɣḍṭẓṛṣḥɛǧčʷ", "gdtzrshejc ")


def key(w: str) -> str:
    w = unicodedata.normalize("NFD", w.lower().translate(BASE))
    return re.sub(r"[^a-z]", "", w)


def fix_fr(s: str) -> str:
    s = norm_space(s).strip(" .,;:")
    return " ".join(FR_FIX.get(w, w) for w in s.split(" ")).replace("( ", "(")


def parse_summary(doc):
    items, cat = [], ""
    for p in ANIMAL_SUMMARY:
        for line in page_lines(doc[p - 1]):
            t = raw_text(line).strip()
            if t.startswith("Bibliographie"):
                return items
            if re.match(r"(Substantifs|Adjectifs|Verbes)\s*:", t):
                cat = t.split()[0].lower()
                continue
            if t.startswith("Champ lexical"):
                continue
            k = t.find(":")
            if k <= 0:
                continue
            kab = norm_space(kab_word(line[:k]))
            fr = fix_fr(t[k + 1:])
            if kab and fr:
                items.append({"kab": kab, "fr": fr, "cat": cat, "page": p})
    return items


def body_head(text: str):
    """Vedette en début de ligne du corps : « Mot « glose » » ou « Mot : glose »
    ou un mot seul sur sa ligne → (mot, glose)."""
    m = re.match(r"^([^\s«:“\"(,-][^\s«:“\"(,]*)\s*(?:[«“:]\s*([^»”:]*)|,|$)", text)
    if not m:
        return None
    return m.group(1), (m.group(2) or "").strip()


def parse_animals(doc):
    summary = parse_summary(doc)
    body, bpages = [], []
    for p in ANIMAL_BODY:
        for line in page_lines(doc[p - 1]):
            t = raw_text(line).strip()
            if t.startswith(("Lexique animal", "Par :")):
                continue
            body.append(norm_space(kab_word(line)))
            bpages.append(p)
    # alignement séquentiel récapitulatif ↔ corps
    pos, matches = 0, []
    for it in summary:
        found = None
        for i in range(pos, min(pos + 70, len(body))):
            h = body_head(body[i])
            if not h:
                continue
            word, gl = h
            sim = difflib.SequenceMatcher(None, key(word), key(it["kab"])).ratio()
            gl_ok = gl and key(gl.split()[0]) == key(it["fr"].split()[0]) \
                and len(body[i].split()) <= 12
            if sim >= 0.7 or (gl_ok and sim >= 0.3) or (gl_ok and i - pos < 6):
                found = (i, word)
                break
        matches.append(found)
        if found:
            pos = found[0] + 1
    starts = sorted(m[0] for m in matches if m)
    recs = []
    for it, m in zip(summary, matches):
        kab, note, page = it["kab"], "", it["page"]
        if m:
            i, word = m
            nxt = next((s for s in starts if s > i), len(body))
            seg = " ".join(body[i:nxt])
            seg = norm_space(seg[len(word):]).lstrip(" ,:")
            # la glose « … » répète le récapitulatif : on la retire de la note
            seg = re.sub(r"^[«“\"][^»”\"]*[»”\"]\s*[,.]?\s*", "", seg)
            if seg.lower().startswith(it["fr"].lower()):
                seg = seg[len(it["fr"]):].lstrip(" .,:")
            if key(word) != key(kab):
                seg = f"[récapitulatif p. {it['page']} : {kab}] " + seg
            kab, note, page = word, cut(seg, NOTE_MAX), bpages[i]
        kab = lower_first(kab.strip(" ,.:"))
        if it["cat"] and it["cat"] != "substantifs":
            note = (it["cat"][:-1] + ". " + note).strip()
        recs.append(record(kab, it["fr"], [], note, "animaux", page))
    return recs


def main(pdf=PDF, out=OUT):
    doc = pymupdf.open(pdf)
    recs = [r for r in parse_earth(doc) + parse_animals(doc) if valid(r["kab"], r["fr"])]
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    n_e = sum(r["domain"] == "sciences de la terre" for r in recs)
    print(f"{len(recs)} enregistrements ({n_e} terre, {len(recs) - n_e} animaux) → {out}")


if __name__ == "__main__":
    main(*sys.argv[1:3])
