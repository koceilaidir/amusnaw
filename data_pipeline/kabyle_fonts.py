"""Tables de conversion des anciennes polices kabyles → Unicode, choisies
selon le nom de la police de chaque morceau de texte du PDF.

Polices rencontrées dans les livres HCA :
  - AmazighBangle / AmazighTimesNewRoman / Bangle* : table « Tira »
  - Tayma-* : autre table (ô = ḍ, ê = ṛ, û = ḥ, î = ṣ…)
  - SymbolOOEnc / Symbol : ε et Σ tapés avec la police Symbol
"""

import re

TIRA = {
    "$": "ɣ", "ù": "ɣ", "£": "Ɣ",
    "v": "ḍ", "V": "Ḍ",
    "î": "ṭ", "§": "ṭ", "Ï": "Ṭ", "Î": "Ṭ",
    "é": "ẓ", "â": "ẓ", "è": "Ẓ", "È": "Ẓ", "É": "Ẓ",
    "ô": "ṛ", "Ö": "Ṛ",
    "û": "ṣ", "Ü": "Ṣ", "Û": "Ṣ",
    "ê": "ḥ", "Ë": "Ḥ", "Ê": "Ḥ",
    "ε": "ɛ", "µ": "ɛ", "Σ": "Ɛ", "∑": "Ɛ",
    "o": "ǧ", "O": "Ǧ",
    "ç": "č", "Ç": "Č",
}
TAYMA = {
    "ù": "ɣ", "$": "ɣ", "£": "Ɣ",
    "ô": "ḍ",
    "ê": "ṛ", "Ê": "Ṛ",
    "û": "ḥ", "Û": "Ḥ",
    "î": "ṣ", "Î": "Ṣ",
    "§": "ṭ",
    "µ": "ɛ", "∑": "Ɛ",
    "â": "ẓ", "Â": "Ẓ",
    "á": "č", "Á": "Č",
    "ú": "ǧ", "Ú": "Ǧ",
    "ñ": "tt",
}
SYMBOL = {"": "ɛ", "": "Ɛ", "": "Ɛ", "e": "ɛ", "S": "Ɛ"}

# Lettres « en gras simulé » : la même lettre tapée 2-3 fois en surimpression
# (ex. « ÊËessbe$ » = Ḥessbeɣ). On fusionne ces groupes en une seule lettre.
OVERSTRIKE = [
    ("ÊËëê", "Ḥ", "ḥ"),
    ("ÏÎî", "Ṭ", "ṭ"),
    ("ÈèÉé", "Ẓ", "ẓ"),
    ("ÛÜû¨", "Ṣ", "ṣ"),
]

FRENCH = {"le", "la", "les", "de", "des", "du", "et", "ou", "en", "pour", "par", "sur",
          "une", "un", "à", "au", "aux", "dans", "est", "avec", "compte", "auteur",
          "cet", "ouvrage", "été", "édité"}


try:  # dictionnaire français (pip install pyspellchecker)
    from spellchecker import SpellChecker
    _FR_DICT = SpellChecker(language="fr").word_frequency.dictionary
except Exception:  # pragma: no cover
    _FR_DICT = {}


def _looks_french(token: str) -> bool:
    """Vrai pour un mot français glissé dans le texte kabyle : on ne doit
    pas convertir ses accents (é, ô…) ni ses « o »."""
    core = re.sub(r"[^\w’'-]", "", token)
    w = core.lower().split("’")[-1].split("'")[-1]
    if not w:
        return False
    if w in FRENCH or w in _FR_DICT:
        return True
    # Nom propre français/étranger (« Hérodote », « Léon ») : majuscule + o simple
    return core[:1].isupper() and "o" in w and "oo" not in w


def _collapse_overstrike(tok: str) -> str:
    for group, upper, lower in OVERSTRIKE:
        def repl(m):
            run = m.group(0)
            return upper if any(c.isupper() for c in run) else lower
        tok = re.sub(f"[{re.escape(group)}]{{2,}}", repl, tok)
    return tok


def table_for(font: str):
    font = font.split("+", 1)[-1]  # « BBAZKR+AmazighTimesNewRoman » → nom réel
    if font.startswith("Tayma"):
        return TAYMA
    if font.startswith("Symbol"):
        return SYMBOL
    if "Bangle" in font or font.startswith("Amazigh"):
        return TIRA
    return None


def convert_span(text: str, font: str, stray_u_grave: bool = False) -> str:
    table = table_for(font)
    if table is None:
        return text
    if table is SYMBOL:
        return "".join(SYMBOL.get(ch, ch) for ch in text)
    out = []
    for tok in re.split(r"(\s+)", text):
        if tok.isspace() or not tok or _looks_french(tok):
            out.append(tok)
            continue
        if table is TAYMA and "é" in tok:  # dans Tayma, é = mots français
            out.append(tok)
            continue
        if stray_u_grave:  # « ù » parasite devant m dans certains livres
            tok = tok.replace("ùm", "m").replace("ùM", "M")
        if table is TIRA:
            tok = _collapse_overstrike(tok)
        out.append("".join(table.get(ch, ch) for ch in tok))
    return "".join(out)
