"""Extraction d'un livre kabyle en PDF (anciennes polices HCA) vers un texte
Unicode propre, avec repères de parties et de chapitres :
  ### IXF <n>     partie
  ## <n>          chapitre
et une ligne vide entre paragraphes.

Usage :
  python extract_kabyle_pdf.py livre.pdf sortie.txt [--stray-u] [--stop "Amawal"]
"""

import argparse
import re

import pymupdf

from kabyle_fonts import convert_span

RUNNING = re.compile(r"^(Mmis n igellil|Mouloud Feraoun|Ageldun [Aa]mecṭuḥ|\d{1,3})$")
PART = re.compile(r"^Ixf\s+([IVX]+)$")
CHAPTER = re.compile(r"^-?\s*([IVXL]+)\s*-?$")


def roman(s: str) -> int:
    vals = {"I": 1, "V": 5, "X": 10, "L": 50}
    total = 0
    for i, c in enumerate(s):
        v = vals[c]
        total += -v if i + 1 < len(s) and vals[s[i + 1]] > v else v
    return total


def extract(pdf_path: str, stray_u: bool = False, stop: str | None = None) -> str:
    doc = pymupdf.open(pdf_path)
    paras, current = [], []

    def flush():
        if current:
            paras.append(" ".join(current).strip())
            current.clear()

    for page in doc:
        blocks = page.get_text("dict")["blocks"]
        xs = [l["bbox"][0] for b in blocks for l in b.get("lines", [])]
        left = min(xs) if xs else 0
        for block in blocks:
            for line in block.get("lines", []):
                text = "".join(convert_span(s["text"], s["font"], stray_u) for s in line["spans"]).strip()
                if not text or RUNNING.match(text):
                    continue
                if stop and text.startswith(stop) and len(paras) > 50:
                    flush()
                    return _finish(paras)
                m_part = PART.match(text)
                m_ch = CHAPTER.match(text.replace(" ", ""))
                if m_part:
                    flush(); paras.append(f"### IXF {roman(m_part.group(1))}"); continue
                if m_ch:
                    flush(); paras.append(f"## {roman(m_ch.group(1))}"); continue
                if line["bbox"][0] - left > 12 or text.startswith(("-", "–")):
                    flush()  # alinéa ou réplique
                current.append(text)
    flush()
    return _finish(paras)


def _finish(paras: list[str]) -> str:
    merged = []
    for p in paras:
        if (merged and not merged[-1].startswith("#") and not p.startswith("#")
                and not re.search(r"[.!?:»”\"…]$", merged[-1]) and p[:1].islower()):
            merged[-1] += " " + p
        else:
            merged.append(p)
    text = "\n\n".join(merged)
    text = re.sub(r"(\w)- (?=[a-zɣḍṭẓṛṣḥɛǧč])", r"\1", text)  # mots coupés
    # Mot en majuscule laissé tel quel (« Weroin ») alors que sa forme
    # convertie existe ailleurs dans le livre (« werǧin ») : on le corrige.
    vocab = set(re.findall(r"\b\w+\b", text.lower()))

    def fix(m: re.Match) -> str:
        w = m.group(0)
        cand = w.replace("o", "ǧ").replace("O", "Ǧ")
        return cand if cand.lower() in vocab else w
    return re.sub(r"\b[A-Z]\w*o\w*\b", fix, text)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("out")
    ap.add_argument("--stray-u", action="store_true", help="retire le « ù » parasite devant m")
    ap.add_argument("--stop", help="arrête l'extraction à la ligne qui commence par ce texte")
    a = ap.parse_args()
    out = extract(a.pdf, a.stray_u, a.stop)
    with open(a.out, "w", encoding="utf-8") as f:
        f.write(out)
    print(f"{len(out)} caractères, {out.count(chr(10) + '## ')} chapitres")
