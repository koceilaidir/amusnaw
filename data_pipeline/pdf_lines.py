"""Texte d'un PDF ligne par ligne, anciennes polices kabyles converties.

  python pdf_lines.py livre.pdf sortie.txt [--from N] [--to M]
Chaque page commence par « ==== p N ».
"""
import argparse

import pymupdf

from kabyle_fonts import convert_span


def page_lines(page, raw: bool = False) -> list[str]:
    out = []
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            t = "".join(s["text"] if raw else convert_span(s["text"], s["font"])
                        for s in line["spans"]).strip()
            if t:
                out.append(t)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf"); ap.add_argument("out")
    ap.add_argument("--from", dest="start", type=int, default=1)
    ap.add_argument("--to", dest="end", type=int, default=0)
    ap.add_argument("--raw", action="store_true", help="sans conversion des polices")
    a = ap.parse_args()
    doc = pymupdf.open(a.pdf)
    end = a.end or doc.page_count
    with open(a.out, "w", encoding="utf-8") as f:
        for i in range(a.start - 1, end):
            f.write(f"==== p {i + 1}\n")
            f.write("\n".join(page_lines(doc[i], a.raw)) + "\n")
