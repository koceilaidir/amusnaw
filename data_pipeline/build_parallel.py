"""Construit le corpus parallèle français ↔ kabyle à partir des livres
traduits, chapitre par chapitre, puis phrase par phrase (align_parallel).

Usage :
  python build_parallel.py feraoun  <fr.pdf> ../data/feraoun_kab.txt       ../data/parallel_feraoun.jsonl
  python build_parallel.py petit_prince <fr.pdf> ../data/petit_prince_kab.txt ../data/parallel_petit_prince.jsonl
"""

import json
import re
import sys

import pymupdf

from align_parallel import align, split_sentences

SOURCES = {
    "feraoun": "Feraoun, Le fils du pauvre / trad. M. Ould Taleb, Mmis n igellil (HCA 2004)",
    "petit_prince": "Saint-Exupéry, Le Petit Prince / trad. H.-A. Mansouri, Ageldun amecṭuḥ (HCA 2004)",
    "camus": "Camus, Misère de la Kabylie / trad. H. Hadid, Lḥif n tmurt n Leqbayel (HCA 2013)",
}


def pdf_text(path: str) -> str:
    return "\n".join(p.get_text() for p in pymupdf.open(path))


# ---------- Le fils du pauvre (extrait FR : partie II, chapitres 1-4…) ----------

def feraoun(fr_pdf: str, kab_txt: str):
    fr = pdf_text(fr_pdf).split("Chapitre 1", 1)[1]
    fr_ch = [split_sentences(c) for c in re.split(r"\n\s*Chapitre \d+\s*\n", fr)]

    kab = open(kab_txt, encoding="utf-8").read()
    kab = kab.split("### IXF 2", 1)[1].split("Amawal :", 1)[0]
    i2 = kab.index("\n## 2\n")
    kab = kab[kab.rfind("\n## 1\n", 0, i2) + 6:]
    parts = re.split(r"\n## \d+\n", kab)
    n = len(fr_ch) - 1  # le dernier bloc FR couvre le reste de la partie
    kab_ch = [split_sentences(c) for c in parts[:n]] + [split_sentences("\n".join(parts[n:]))]
    return fr_ch, kab_ch


# ---------- Le Petit Prince (27 chapitres des deux côtés) ----------
# Ici on a les paragraphes des deux côtés : on aligne d'abord les
# paragraphes, puis les phrases à l'intérieur de chaque paire de paragraphes.

def petit_prince(fr_pdf: str, kab_txt: str):
    doc = pymupdf.open(fr_pdf)
    blocks = [re.sub(r"\s+", " ", b[4]).strip() for p in doc for b in p.get_text("blocks")]
    blocks = [b for b in blocks if b]
    start = blocks.index("PREMIER CHAPITRE")
    fr_ch, cur = [], []
    for b in blocks[start + 1:]:
        if re.fullmatch(r"CHAPITRE [IVXL]+", b):
            fr_ch.append(cur); cur = []
        else:
            cur.append(b)
    fr_ch.append(cur)

    kab = open(kab_txt, encoding="utf-8").read()
    kab = kab.split("\n## 1\n", 1)[1]
    kab = re.split(r"\n\* \* \*", kab)[0]  # avant le glossaire final
    kab_ch = [[p.strip() for p in c.split("\n\n") if p.strip()]
              for c in re.split(r"\n## \d+\n", kab)]
    return fr_ch, kab_ch


# ---------- Misère de la Kabylie (Camus) / Lḥif n tmurt n Leqbayel ----------
# Kabyle en Unicode (2013) : pas de conversion de police. 13 sections.

CAMUS_FR_HEADS = [
    r"Présentation", r"I - La Grèce en haillons", r"II\. DENUEMENT", r"III\. LE DENUEMENT",
    r"IV\. LES SALAIRES INSULTANTS", r"V\. L’HABITAT", r"VI\. L’ASSISTANCE",
    r"VII\. L'ENSEIGNEMENT", r"VIII\. DEUX ASPECTS DE LA VIE ÉCONOMIQUE KABYLE[^\n]*?L’USURE",
    r"IX\. L’AVENIR POLITIQUE DES CENTRES COMMUNAUX", r"POUR VIVRE LA KABYLIE RÉCLAME !",
    r"CONCLUSION", r"Annexe :",
]
CAMUS_KAB_HEADS = [
    r"TAZWART", r"## 1", r"## 2", r"## 3", r"## 4", r"## 5", r"## 6", r"## 7", r"## 8",
    r"Tudert tasertit i nettraǧu di tɣiwanin", r"Akken ad tεic, Tamurt n Leqbayel teṭṭalab :",
    r"Lxatima", r"Timerna",
]


def _split_on_heads(text: str, heads: list[str]) -> list[str]:
    pos = []
    start = 0
    for h in heads:
        m = re.compile(h).search(text, start)
        if not m:
            raise ValueError(f"titre introuvable : {h}")
        pos.append((m.start(), m.end()))
        start = m.end()
    return [text[e: (pos[i + 1][0] if i + 1 < len(pos) else len(text))]
            for i, (_, e) in enumerate(pos)]


def camus(fr_pdf: str, kab_txt: str):
    from extract_kabyle_pdf import extract
    fr = extract(fr_pdf)
    fr = fr[fr.index("Présentation Dans"):]  # après la table des matières
    fr_secs = _split_on_heads(fr, CAMUS_FR_HEADS)
    kab = open(kab_txt, encoding="utf-8").read().replace("ε", "ɛ").replace("Г", "Ɣ")
    kab = kab[kab.index("TAZWART"):]
    kab_secs = _split_on_heads(kab, [h.replace("ε", "ɛ") for h in CAMUS_KAB_HEADS])
    # Fin du discours de Stockholm : on coupe la postface FR et le catalogue HCA.
    fr_secs[-1] = fr_secs[-1].split("dans le silence.", 1)[0] + "dans le silence."
    kab_secs[-1] = kab_secs[-1].split("Tiẓrigin n Usqamu", 1)[0]
    return [split_sentences(s) for s in fr_secs], [split_sentences(s) for s in kab_secs]


def align_two_levels(fr_paras: list[str], kab_paras: list[str]):
    """Paragraphes d'abord, phrases ensuite."""
    for fr_p, kb_p, d_p, bead_p in align(fr_paras, kab_paras):
        if not fr_p or not kb_p:
            continue
        fs, ks = split_sentences(fr_p), split_sentences(kb_p)
        if len(fs) == len(ks) == 1:
            yield fr_p, kb_p, d_p, (1, 1), bead_p
            continue
        for fr_s, kb_s, d, bead in align(fs, ks):
            yield fr_s, kb_s, d, bead, bead_p


def main(book: str, fr_pdf: str, kab_txt: str, out: str) -> None:
    fr_ch, kab_ch = {"feraoun": feraoun, "petit_prince": petit_prince, "camus": camus}[book](fr_pdf, kab_txt)
    assert len(fr_ch) == len(kab_ch), f"chapitres FR={len(fr_ch)} KAB={len(kab_ch)}"
    rows, kept = [], 0
    for ch, (f, k) in enumerate(zip(fr_ch, kab_ch), start=1):
        if book == "petit_prince":
            pairs = align_two_levels(f, k)
        else:
            pairs = ((a, b, d, bead, None) for a, b, d, bead in align(f, k))
        for fr_s, kb_s, d, bead, bead_p in pairs:
            if not fr_s or not kb_s:
                continue
            ratio = len(kb_s) / max(len(fr_s), 1)
            confident = d < 3.0 and 0.6 < ratio < 1.8 and max(bead) <= 2
            if bead_p is not None:  # le paragraphe lui-même doit être bien apparié
                confident = confident and tuple(bead_p) == (1, 1)
            kept += confident
            rows.append({"fr": fr_s, "kab": kb_s, "book": book, "chapter": ch,
                         "bead": list(bead), "cost": round(d, 2), "confident": confident,
                         "source": SOURCES[book], "needs_review": True})
    with open(out, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"{book}: {len(fr_ch)} chapitres, {len(rows)} paires, dont {kept} probablement justes")


if __name__ == "__main__":
    main(*sys.argv[1:5])
