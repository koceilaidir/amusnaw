"""Lexiques externes sous licence libre → fichiers de la base.

    python import_lexicons_ext.py ../data

1. Correcteur orthographique kabyle (Hunspell, M. Belkacem, nettoyé par
   A. Mokraoui, licence MIT) : data/externes/kab.dic → data/hunspell_kab.jsonl
   21 800 mots bien orthographiés, avec leur nature (nom, verbe, adjectif…)
   et leur mot de base (« tisemsarin » → « tasemsart », pluriel). Pas de sens :
   sert au lemmatiseur (pluriels, féminins) et à la vérification d'orthographe.
2. Lexique de mathématiques Tafsut (agurzil, via KabLex, CC BY 4.0) :
   data/externes/kablex_lexicon.jsonl → data/lexicon_maths.jsonl (sens français).
"""
import json
import re
import sys
import unicodedata
from pathlib import Path

POS = {"isem": "nom", "amyag": "verbe", "arbib": "adjectif", "tazelɣa": "adverbe", "isem_n_umdan": "nom de personne",
       "isem_n_tigawt": "nom d'action", "amernu": "conjonction", "tanzeɣt": "préposition", "ameskan": "démonstratif",
       "aferdis_n_ubhat": "particule", "isem_amḍan": "numéral", "isem_n_tmurt": "nom de pays", "amqim": "pronom",
       "isem_n_umkan": "nom de lieu", "isem_uzzig": "nom", "isem_asinan": "nom"}
INFL = {"asget": "pluriel", "izri": "prétérit", "izri_ibaw": "prétérit négatif", "urmir_ussid": "aoriste intensif",
        "SF": "féminin singulier", "SG": "singulier", "NT": "annexion"}


def nfc(s):
    return unicodedata.normalize("NFC", s.strip())


def hunspell(ext: Path, out: Path):
    rows, pos_of = [], {}
    lines = [ln.rstrip("\n") for ln in open(ext / "kab.dic", encoding="utf-8")][1:]
    for ln in lines:
        word = nfc(ln.split()[0].split("/")[0]) if ln.strip() else ""
        po = re.search(r"po:(\S+)", ln)
        if word and po:
            pos_of[word] = POS.get(po.group(1), po.group(1))
    for ln in lines:
        if not ln.strip():
            continue
        word = nfc(ln.split()[0].split("/")[0])
        st = re.search(r"st:(\S+)", ln)
        lemma = nfc(st.group(1)) if st else word
        infl = [INFL.get(x, x) for x in re.findall(r"is:(\S+)", ln)]
        pos = pos_of.get(word) or pos_of.get(lemma) or ""
        if not re.fullmatch(r"[a-zɛɣḍṭẓṛṣḥčǧʷ'-]+", word.lower()):
            continue
        rows.append({"form": word, "lemma": lemma, "pos": pos, "infl": infl,
                     "source": "Hunspell kabyle (M. Belkacem ; nettoyage A. Mokraoui), MIT"})
    out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    print(f"Hunspell : {len(rows)} mots, dont {sum(1 for r in rows if r['lemma'] != r['form'])} liés à un mot de base")


def maths(ext: Path, out: Path):
    rows = []
    for ln in open(ext / "kablex_lexicon.jsonl", encoding="utf-8"):
        r = json.loads(ln)
        if "tafsut" not in r["source"] or not r.get("glosses"):
            continue
        fr = "; ".join(g["text"] for g in r["glosses"] if g["lang"] == "fra")
        if fr:
            rows.append({"kab": nfc(r["form"]), "fr": fr, "kind": "entry", "domain": "mathématiques",
                         "source": "Lexique de mathématiques Tafsut (agurzil, via KabLex), CC BY 4.0",
                         "needs_review": True})
    out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    print(f"Mathématiques : {len(rows)} termes")


if __name__ == "__main__":
    d = Path(sys.argv[1])
    hunspell(d / "externes", d / "hunspell_kab.jsonl")
    maths(d / "externes", d / "lexicon_maths.jsonl")
