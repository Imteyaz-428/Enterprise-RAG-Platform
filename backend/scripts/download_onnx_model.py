"""
Downloads the quantized int8 ONNX model and tokenizer for cross-encoder/ms-marco-MiniLM-L-6-v2.
Executed during Docker build time to bake the files into /app/models/reranker/.
"""
import os
import shutil
import sys
from pathlib import Path
from huggingface_hub import hf_hub_download

TARGET_DIR = Path(__file__).resolve().parent.parent / "models" / "reranker"
TARGET_DIR.mkdir(parents=True, exist_ok=True)

MODEL_TARGET = TARGET_DIR / "model.onnx"
TOKENIZER_TARGET = TARGET_DIR / "tokenizer.json"

REPO_ID = "cross-encoder/ms-marco-MiniLM-L-6-v2"
ONNX_FILENAME = "onnx/model_qint8_arm64.onnx"
TOKENIZER_FILENAME = "tokenizer.json"


def download():
    if MODEL_TARGET.exists() and MODEL_TARGET.stat().st_size > 1000:
        print(f"Model already present at {MODEL_TARGET} ({MODEL_TARGET.stat().st_size} bytes)")
    else:
        print(f"Downloading {ONNX_FILENAME} from {REPO_ID}...")
        downloaded = hf_hub_download(repo_id=REPO_ID, filename=ONNX_FILENAME)
        shutil.copyfile(downloaded, MODEL_TARGET)
        print(f"Saved model to {MODEL_TARGET} ({MODEL_TARGET.stat().st_size} bytes)")

    if TOKENIZER_TARGET.exists() and TOKENIZER_TARGET.stat().st_size > 1000:
        print(f"Tokenizer already present at {TOKENIZER_TARGET} ({TOKENIZER_TARGET.stat().st_size} bytes)")
    else:
        print(f"Downloading {TOKENIZER_FILENAME} from {REPO_ID}...")
        downloaded = hf_hub_download(repo_id=REPO_ID, filename=TOKENIZER_FILENAME)
        shutil.copyfile(downloaded, TOKENIZER_TARGET)
        print(f"Saved tokenizer to {TOKENIZER_TARGET} ({TOKENIZER_TARGET.stat().st_size} bytes)")


if __name__ == "__main__":
    download()
