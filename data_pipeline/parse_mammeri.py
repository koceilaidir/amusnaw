"""M. Mammeri, Tajerrumt n tmaziɣt (tantala taqbaylit), Maspero 1976 — grammaire écrite en kabyle.
Le PDF est une image : texte lu par OCR (tesseract, data/externes/ocr/mammeri_*.txt), puis chaque
mot est restauré à partir du kabyle attesté (kab_vocab.py). On ne garde que les phrases dont
presque tous les mots sont retrouvés : kabyle humain, utilisable pour la rétro-traduction.
Autorisation obtenue par le HCA (oct. 2026) pour améliorer l'IA d'Amusnaw.

  python parse_mammeri.py ../data
"""
import json
import re
import sys
from pathlib import Path

from kab_vocab import Vocab, WORD

SRC = "M. Mammeri, Tajerrumt n tmaziɣt (tantala taqbaylit), Maspero, 1976"


def main(data: Path):
    vocab = Vocab.load(data)
    text = ""
    for p in sorted((data / "externes" / "ocr").glob("mammeri_*.txt")):
        text += "\n" + p.read_text(encoding="utf-8")
    text = re.sub(r"-\n(?=[a-zɛɣ])", "", text)
    text = re.sub(r"\s+", " ", text)
    out, seen = [], set()
    for s in re.split(r"(?<=[.;:!?])\s+", text):
        s = s.strip(" ,-«»")
        words = WORD.findall(s)
        if not 4 <= len(words) <= 30 or re.search(r"\d|[A-Z]{3,}|[{}|\[\]@#*=]", s):
            continue
        fixed, ok = s, 0
        for w in words:
            r, good = vocab.restore(w)
            ok += good
            if good and r != w.lower():
                fixed = re.sub(rf"(?<![^\W\d_]){re.escape(w)}(?![^\W\d_])", r if w.islower() else r.capitalize(), fixed, 1)
        if ok / len(words) >= 0.9 and fixed.lower() not in seen:
            seen.add(fixed.lower())
            out.append({"kab": fixed, "source": SRC, "ocr": True})
    with (data / "mammeri_tajerrumt.jsonl").open("w", encoding="utf-8") as f:
        for r in out:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"{len(out)} phrases kabyles gardées")


if __name__ == "__main__":
    main(Path(sys.argv[1] if len(sys.argv) > 1 else "../data"))
