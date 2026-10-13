"""Conversion des anciennes polices kabyles (type « Tira » / HCA) vers
l'Unicode standard.

Beaucoup de documents HCA des années 2000 ont été saisis avec une police
qui affiche ɣ, ḍ, ṭ… à la place de caractères ordinaires ($, v, î…).
Une fois copiés, ces textes sont illisibles pour une machine. Ce module
rétablit les vraies lettres, uniquement dans les lignes en kabyle (les
lignes en français gardent leurs accents).
"""

import re

# Table tirée de la « Tafelwit n tira » du livre (p. 11).
LOWER = {
    "$": "ɣ", "γ": "ɣ",
    "v": "ḍ",
    "î": "ṭ",
    "é": "ẓ",
    "ô": "ṛ",
    "û": "ṣ",
    "ê": "ḥ",
    "ε": "ɛ",
    "o": "ǧ",
    "ç": "č",
}
UPPER = {
    "£": "Ɣ", "Γ": "Ɣ",
    "Ï": "Ṭ",
    "è": "Ẓ",  # majuscule de ẓ dans cette police
    "Ö": "Ṛ",
    "Ü": "Ṣ",
    "Ë": "Ḥ",
    "Σ": "Ɛ",
    "O": "Ǧ",
}
# Dans les racines notées entre parenthèses, (BLBV) = BLBḌ.
ROOT_EXTRA = {"V": "Ḍ"}

FRENCH_WORDS = {
    "le", "la", "les", "de", "des", "du", "et", "ou", "en", "pour", "par", "sur",
    "une", "un", "à", "au", "aux", "dans", "est", "qui", "que", "avec", "ed",
    "son", "sa", "ses", "il", "elle", "pas", "ne", "se", "ce", "cette",
}
KABYLE_HINTS = {
    "d", "n", "s", "di", "deg", "akked", "ad", "yesεa", "ur", "ara", "yettili",
    "maca", "acku", "yerna", "i", "$ef", "ne$", "seg", "armi", "am",
}

_PUA = re.compile(r"[-]")
_IPA_BRACKETS = re.compile(r"\[[^\]]*[-əөŧđ][^\]]*\]")
_SPLIT_HYPHEN = re.compile(r"(\w)- (d|s|t|tt|is|as|asen|sen|iyi|ak|am|k|m|ten|tent|it|at|ag|agi|nni|a|an)\b")


def is_french_line(line: str) -> bool:
    words = re.findall(r"[^\W\d_]+", line.lower())
    if not words:
        return False
    fr = sum(w in FRENCH_WORDS for w in words)
    kab = sum(w in KABYLE_HINTS for w in words) + line.count("$") + line.count("ε")
    return fr >= 2 and fr > kab


def _map_roots(text: str) -> str:
    def repl(m: re.Match) -> str:
        inner = m.group(1)
        for k, v in {**UPPER, **ROOT_EXTRA}.items():
            inner = inner.replace(k, v)
        return f"({inner})"
    return re.sub(r"\(([A-Z£ÏèÖÜËΣOVàçéêîôûεv$, ]{1,12})\)", repl, text)


def convert_line(line: str) -> str:
    """Convertit une ligne kabyle. Les lignes françaises sont renvoyées
    telles quelles (hors nettoyage des symboles de police)."""
    line = _IPA_BRACKETS.sub("", line)
    line = _PUA.sub("", line)
    if is_french_line(line):
        return line
    line = _map_roots(line)
    for table in (LOWER, UPPER):
        for k, v in table.items():
            line = line.replace(k, v)
    # « Yekka- d » → « Yekka-d » (artefact de mise en page)
    line = _SPLIT_HYPHEN.sub(r"\1-\2", line)
    return line


def convert_text(text: str) -> str:
    return "\n".join(convert_line(l) for l in text.splitlines())


if __name__ == "__main__":
    import sys
    print(convert_text(sys.stdin.read()))
