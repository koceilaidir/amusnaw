"""Service de traduction NLLB-200 (CTranslate2, int8, processeur).

POST /translate {"sentences": [...], "src": "fra_Latn", "tgt": "kab_Latn"}
  → {"translations": [...]}
Le modèle peut être remplacé par notre version réentraînée (amusnaw-mt) : même format,
dossier MODEL_DIR.
"""
import os
import threading

import ctranslate2
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from transformers import AutoTokenizer

MODEL_DIR = os.environ.get("MODEL_DIR", "/models/nllb")
LANGS = {"fra_Latn", "kab_Latn", "eng_Latn"}

# Le découpage en mots ne change pas pendant notre entraînement (vocabulaire figé) :
# on prend toujours celui de NLLB de base, livré avec l'image.
tokenizer = AutoTokenizer.from_pretrained(os.environ.get("TOKENIZER_DIR", "/models/nllb"))
translator = ctranslate2.Translator(MODEL_DIR, device="cpu", compute_type="int8",
                                    intra_threads=int(os.environ.get("OMP_NUM_THREADS", "2")))
_lock = threading.Lock()  # le tokenizer change de langue source : une requête à la fois

app = FastAPI(title="Amusnaw MT")


class Job(BaseModel):
    sentences: list[str] = Field(min_length=1, max_length=64)
    src: str
    tgt: str
    beam: int = Field(4, ge=1, le=8)


@app.get("/health")
def health():
    return {"ok": True, "model": MODEL_DIR}


@app.post("/translate")
def translate(job: Job):
    if job.src not in LANGS or job.tgt not in LANGS:
        raise HTTPException(400, "Langue non prise en charge.")
    sents = [s.strip()[:1000] for s in job.sentences]
    with _lock:
        tokenizer.src_lang = job.src
        toks = [tokenizer.convert_ids_to_tokens(tokenizer.encode(s)) for s in sents]
        res = translator.translate_batch(toks, target_prefix=[[job.tgt]] * len(toks), beam_size=job.beam,
                                         max_decoding_length=256, repetition_penalty=1.1)
    out = []
    for r in res:
        hyp = r.hypotheses[0][1:]  # sans le code de langue
        out.append(tokenizer.decode(tokenizer.convert_tokens_to_ids(hyp), skip_special_tokens=True))
    return {"translations": out}
