"""A. At Weḥmana, « Tinfaliyin n Tmaziɣt-Taqbaylit » (HCA 2025) : expressions kabyles
avec traduction française → JSON Lines.

    python parse_tinfaliyin.py livre.pdf ../data/tinfaliyin.jsonl

Mise en page : mot d'entrée en gras (retrait ~128 pt) + sens en italique entre
parenthèses ; exemples « - <kabyle en gras> (<français en italique>) ».
On suit la POLICE (gras = kabyle, italique = français), pas la position des
lignes : une traduction peut commencer sur une ligne et finir sur la suivante,
ou passer à la page suivante.
L'auteur a son orthographe (préfixes séparés : « I nna-yas », « i tt ru ») :
les phrases sont gardées telles quelles avec orthography = "auteur".
"""
import json
import re
import sys
import unicodedata

import pymupdf

SRC = "A. At Weḥmana, Tinfaliyin n Tmaziɣt-Taqbaylit (expressions kabyles), HCA 2025"
GREEK = str.maketrans({"ε": "ɛ", "Ε": "Ɛ", "γ": "ɣ", "Γ": "Ɣ", "ğ": "ǧ", "’": "'"})


def spans(doc, start, end):
    for pno in range(start, end):
        for b in doc[pno].get_text("dict")["blocks"]:
            for ln in b.get("lines", []):
                y = ln["bbox"][1]
                if y < 45 or y > doc[pno].rect.height - 45:
                    continue  # en-tête « Abdereḥman At Weḥmana », numéro de page
                first = True
                for s in ln["spans"]:
                    t = s["text"]
                    if not t.strip():
                        continue
                    bold = bool(s["flags"] & 16) or "Bold" in s["font"]
                    yield {"t": t, "bold": bold, "x": ln["bbox"][0], "nl": first, "page": pno}
                    first = False


def clean(s):
    s = unicodedata.normalize("NFC", s.translate(GREEK))
    return re.sub(r"\s+", " ", s).strip(" -–")


def main(pdf, out):
    doc = pymupdf.open(pdf)
    # le corps commence à la première entrée (page « albab ») et finit avant la bibliographie
    start = next(i for i in range(len(doc)) if re.search(r"\(Escalader", doc[i].get_text())) - 1
    end = next((i for i in range(len(doc) - 1, start, -1) if re.search(r"Bibliograph|Tadlisant", doc[i].get_text())),
               len(doc))
    rows, head, gloss, heads = [], None, "", []
    cur = None  # exemple en cours : {"kab", "fr", "depth"}
    mode = None  # "head" | "gloss" | "kab" | "fr"
    depth = 0
    for sp in spans(doc, max(start, 0), end):
        t = sp["t"]
        if re.fullmatch(r"\s*\d+\s*|\s*Abdereḥman At Weḥmana\s*|\s*Tinfaliyin n Tmaziɣt-Taqbaylit\s*", t):
            continue  # numéro de page, en-têtes
        # Une parenthèse non refermée ne doit pas avaler la suite : une nouvelle ligne
        # en gras ou qui commence par « - » termine le français en cours.
        if mode == "fr" and sp["nl"] and (sp["bold"] or re.match(r"^\s*-\s", t)):
            mode = "after"
        # Nouvel exemple : ligne qui commence par « - »
        if sp["nl"] and re.match(r"^\s*-\s*", t) and mode != "fr":
            cur = {"kab": "", "fr": "", "head": head, "page": sp["page"]}
            rows.append(cur)
            t = re.sub(r"^\s*-\s*", "", t)
            mode = "kab"
            if not t.strip():
                continue
        # Nouveau mot d'entrée : gras en début de ligne, en retrait, hors exemple
        if sp["bold"] and sp["nl"] and sp["x"] > 110 and mode != "fr" and not t.lstrip().startswith("-"):
            if head and gloss:
                heads.append((head, gloss, sp["page"]))
            head = clean(t).rstrip(" :")
            gloss, mode, depth, cur = "", "head", 0, None
            continue
        if mode in ("head", "gloss") and not sp["bold"]:
            gloss += t
            mode = "gloss"
            continue
        if mode == "kab" and cur is not None:
            if not sp["bold"] and t.lstrip().startswith("("):
                mode, depth = "fr", 0
            else:
                cur["kab"] += t
                continue
        if mode == "fr" and cur is not None:
            for ch in t:
                if ch == "(":
                    depth += 1
                    if depth == 1:
                        continue
                elif ch == ")":
                    depth -= 1
                    if depth == 0:
                        mode = "after"
                        break
                cur["fr"] += ch
            continue
    out_rows = []
    for r in rows:
        kab, fr = clean(r["kab"]), clean(r["fr"]).rstrip(" .")
        if not kab or not fr or len(kab) > 200 or re.search(r"[a-zéèàç]{3,} (le|la|les|de|des|un|une) ", kab):
            continue
        out_rows.append({"kab": kab, "fr": fr + ".", "head": r["head"], "page": r["page"] + 1,
                         "source": SRC, "orthography": "auteur", "needs_review": True})
    with open(out, "w", encoding="utf-8") as f:
        for r in out_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    words = []
    for h, g, pg in heads:
        m = re.match(r"\s*\(([^()]*(?:\([^()]*\)[^()]*)*)\)", g)
        g = clean(m.group(1) if m else g).strip(" .")
        h = re.sub(r"\s*\(.*?\)", "", h).strip(" :")
        if h and g and len(h.split()) <= 2 and len(g) <= 120:
            words.append({"kab": h.lower(), "fr": g[0].lower() + g[1:], "kind": "entry", "domain": "expressions",
                          "page": pg + 1, "source": SRC, "needs_review": True})
    with open(out.replace("tinfaliyin.jsonl", "lexicon_tinfaliyin.jsonl"), "w", encoding="utf-8") as f:
        for w in words:
            f.write(json.dumps(w, ensure_ascii=False) + "\n")
    print(f"{len(words)} mots d'entrée ; {len(out_rows)} expressions (sur {len(rows)} exemples), pages {start}-{end}")


if __name__ == "__main__":
    main(*sys.argv[1:3])
