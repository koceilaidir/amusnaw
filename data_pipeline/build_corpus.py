"""Corpus kabyle monolingue à partir des livres HCA (romans, contes, poésie,
essais) : phrases authentiques, avec leur source, pour montrer au prof des
exemples d'emploi réels (RAG) et calculer la fréquence des mots.

  python build_corpus.py <dossier_pdf> ../data/corpus_hca.jsonl ../data/word_freq.tsv

Chaque livre : <dossier>/<année>/<nn-titre>/livre.pdf + infos.txt.
Seules les phrases reconnues comme kabyles sont gardées (mots-outils kabyles
fréquents, pas de mots français ni d'arabe).
"""
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

import pymupdf

from kabyle_fonts import convert_span

# Livres exclus : autres variétés (touareg, mozabite, chaoui, Ouargla, Blida),
# lexiques (traités à part), ouvrages en français ou en arabe.
EXCLUDE = (
    "Adlisfus", "tumzabt", "Wewras", "Wawras", "wawras", "At-Wargren", "tacawit", "Techelhit",
    "Aselmed-n-tantaliwin", "AMAWAL", "Amawal", "LEXIQUE", "RECUEIL", "ASEGZAWAL",
    "ACTES", "Actes", "Royaumes", "2011/02-livre", "patronymes",
)

KAB_WORDS = set("""
d n s i deg di ad ur ara yella tella llan ɣef ɣer seg akked yid yis-s anda
acu ayen wayen win wid tin tid maca acku yerna mi ma imi armi alamma ass ass-a
yiwen yiwet tura dɣa dɣen daɣen lemmer ula kan aṭas mliḥ ihi neɣ yal kra nnig ddaw
ines-is-iw-ik-im-nneɣ-nwen-nsen yeqqar teqqar nnan yenna tenna yessen
""".replace("-", " ").split())
FR_WORDS = set("""
le la les de des du et est une un pour par dans que qui sur avec pas plus son sa ses
au aux ce cette il elle nous vous ils elles été être avoir était sont
""".split())
ARABIC = re.compile(r"[؀-ۿ]")
TIFINAGH = re.compile(r"[ⴰ-⵿]")
SENT = re.compile(r"(?<=[.!?…»])\s+(?=[«\"“A-ZƐƔḌṬẒṚṢḤČǦ])")
WORD = re.compile(r"[a-zɛɣḍṭẓṛṣḥčǧA-ZƐƔḌṬẒṚṢḤČǦ]+(?:-[a-zɛɣḍṭẓṛṣḥčǧ]+)*")


GREEK = str.maketrans({"ε": "ɛ", "Ε": "Ɛ", "Σ": "Ɛ", "γ": "ɣ", "Γ": "Ɣ", "ğ": "ǧ", "Ğ": "Ǧ"})


def title_of(book: Path) -> str:
    info = book / "infos.txt"
    if info.exists():
        meta = dict(re.findall(r"^(\w[\w ]*?)\s*:\s*(.*)$", info.read_text(encoding="utf-8", errors="ignore"), re.M))
        t, a, y = meta.get("Titre", "").split("/")[0].strip(), meta.get("Auteur", "").strip(), meta.get("Année", "").strip()
        if t:
            return f"{t} ({a}, HCA {y})" if a and a != "—" else f"{t} (HCA {y})"
    return book.name


def page_text(page) -> str:
    lines = []
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            t = "".join(convert_span(s["text"], s["font"]) for s in line["spans"]).strip()
            if t and not re.fullmatch(r"[-–—\s\d]+", t):
                lines.append(t)
    text = " ".join(lines)
    text = re.sub(r"(\w)- (?=[a-zɣḍṭẓṛṣḥɛǧč])", r"\1", text)  # mots coupés en fin de ligne
    text = text.translate(GREEK)  # ε γ tapés en grec dans certains livres
    return unicodedata.normalize("NFC", re.sub(r"\s+", " ", text))


def is_kabyle(sentence: str) -> bool:
    if ARABIC.search(sentence) or TIFINAGH.search(sentence):
        return False
    words = [w.lower() for w in WORD.findall(sentence)]
    if not 4 <= len(words) <= 45:
        return False
    fr = sum(w in FR_WORDS for w in words)
    kab = sum(w in KAB_WORDS for w in words) + sum(1 for w in words if re.search(r"[ɛɣḍṭẓṛṣḥ]", w))
    return kab >= 2 and fr <= 1 and kab > fr * 3


def main(root: str, out_path: str, freq_path: str) -> None:
    root_p = Path(root)
    seen, rows, freq = set(), [], Counter()
    books = sorted(p.parent for p in root_p.glob("*/*/livre.pdf"))
    for book in books:
        rel = str(book.relative_to(root_p))
        if any(x in rel for x in EXCLUDE):
            continue
        source = title_of(book)
        doc = pymupdf.open(book / "livre.pdf")
        kept = 0
        for i, page in enumerate(doc):
            for s in SENT.split(page_text(page)):
                s = s.strip(" -–—")
                key = re.sub(r"\W+", "", s.lower())
                if key in seen or not is_kabyle(s):
                    continue
                seen.add(key)
                rows.append({"kab": s, "source": source, "page": i + 1, "book": rel})
                freq.update(w.lower() for w in WORD.findall(s))
                kept += 1
        print(f"{kept:6d}  {rel}")
    with open(out_path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(freq_path, "w", encoding="utf-8") as f:
        for w, n in freq.most_common():
            if n >= 2:
                f.write(f"{w}\t{n}\n")
    print(f"total {len(rows)} phrases, {len(freq)} formes")


if __name__ == "__main__":
    main(*sys.argv[1:4])
