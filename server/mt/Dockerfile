# Moteur de traduction NLLB-200 (Meta, licence CC BY-NC 4.0 : usage non commercial).
# Étape 1 : télécharge le modèle et le convertit en int8 (CTranslate2) — rapide sur processeur.
# Demande ~4 Go de mémoire libre pendant la construction (arrêter Ollama si besoin).
FROM python:3.11-slim AS convert
RUN pip install --no-cache-dir torch==2.4.1 --index-url https://download.pytorch.org/whl/cpu \
 && pip install --no-cache-dir transformers==4.44.2 ctranslate2==4.4.0 sentencepiece==0.2.0 protobuf==5.28.3
ARG MODEL=facebook/nllb-200-distilled-600M
RUN ct2-transformers-converter --model ${MODEL} --output_dir /models/nllb --quantization int8 \
 && python -c "from transformers import AutoTokenizer; AutoTokenizer.from_pretrained('${MODEL}').save_pretrained('/models/nllb')" \
 && rm -rf /root/.cache/huggingface

# Étape 2 : le service, sans PyTorch (~1 Go de mémoire en marche)
FROM python:3.11-slim
RUN pip install --no-cache-dir ctranslate2==4.4.0 transformers==4.44.2 sentencepiece==0.2.0 \
    fastapi==0.115.6 uvicorn==0.32.1
COPY --from=convert /models /models
COPY app.py /app/app.py
WORKDIR /app
ENV OMP_NUM_THREADS=2
EXPOSE 8100
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8100"]
