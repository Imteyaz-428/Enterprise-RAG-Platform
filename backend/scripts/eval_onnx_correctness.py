import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
from scipy.stats import spearmanr
from sentence_transformers import CrossEncoder
from tokenizers import Tokenizer
import onnxruntime as ort
from huggingface_hub import hf_hub_download
from dotenv import load_dotenv

load_dotenv()

from database.database import SessionLocal
from crud.document_chunk import search_hybrid_chunks

# 1. Load questions and cached embeddings
with open("eval/.embed_cache.json") as f:
    cache = json.load(f)

with open("eval/bench_org1.jsonl") as f:
    items = [json.loads(line) for line in f if line.strip() and not line.startswith("#")][:10]

# 2. Setup models
torch_model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

tok_path = hf_hub_download("cross-encoder/ms-marco-MiniLM-L-6-v2", "tokenizer.json")
model_path = hf_hub_download("cross-encoder/ms-marco-MiniLM-L-6-v2", "onnx/model_qint8_arm64.onnx")

tokenizer = Tokenizer.from_file(tok_path)
tokenizer.enable_truncation(max_length=512)
tokenizer.enable_padding(pad_id=0, pad_token="[PAD]")

sess_opts = ort.SessionOptions()
sess_opts.intra_op_num_threads = 1
onnx_sess = ort.InferenceSession(model_path, sess_opts, providers=["CPUExecutionProvider"])

db = SessionLocal()
spearman_corrs = []
top5_overlaps = []

print("Evaluating 10 questions from eval/bench_org1.jsonl:")
for idx, item in enumerate(items, 1):
    q = item["question"]
    qid = item["id"]
    emb = cache[q]
    results = search_hybrid_chunks(
        db=db,
        organization_id=1,
        query=q,
        query_embedding=emb,
        top_k=20,
        candidate_k=20,
        rrf_k=60,
    )
    chunks = [c for c, d, s in results]
    pairs = [(q, c.chunk_text) for c in chunks]
    assert len(pairs) == 20, f"Expected 20 pairs, got {len(pairs)}"

    # Torch scores
    torch_scores = torch_model.predict(pairs)

    # ONNX scores
    encs = tokenizer.encode_batch(pairs)
    input_ids = np.array([e.ids for e in encs], dtype=np.int64)
    attention_mask = np.array([e.attention_mask for e in encs], dtype=np.int64)
    token_type_ids = np.array([e.type_ids for e in encs], dtype=np.int64)

    out = onnx_sess.run(None, {
        "input_ids": input_ids,
        "attention_mask": attention_mask,
        "token_type_ids": token_type_ids,
    })
    onnx_scores = out[0].flatten()

    # Spearman
    corr, _ = spearmanr(torch_scores, onnx_scores)
    spearman_corrs.append(corr)

    # Top-5 overlap
    top5_torch_indices = set(np.argsort(torch_scores)[::-1][:5])
    top5_onnx_indices = set(np.argsort(onnx_scores)[::-1][:5])
    overlap = len(top5_torch_indices & top5_onnx_indices) / 5.0
    top5_overlaps.append(overlap)

    print(f"  Q{idx} [{qid}]: Spearman={corr:.4f}, Top-5 Overlap={overlap*100:.0f}%")

db.close()

mean_spearman = np.mean(spearman_corrs)
mean_top5 = np.mean(top5_overlaps)
print(f"\nSummary across 10 questions:")
print(f"Mean Spearman correlation: {mean_spearman:.4f}")
print(f"Mean Top-5 Overlap: {mean_top5*100:.1f}% ({mean_top5:.4f})")
