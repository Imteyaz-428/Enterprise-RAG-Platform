import os
import threading
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np

from services.ai.config import (
    RERANKER_BACKEND,
    VOYAGE_RERANK_MODEL,
    ONNX_RERANKER_MODEL_PATH,
    ONNX_RERANKER_TOKENIZER_PATH,
)
from services.chat.retrieval_result import RetrievalResult
from utils.logger import logger

_onnx_lock = threading.Lock()
_onnx_session = None
_onnx_tokenizer = None


def get_optimal_device() -> str:
    try:
        import torch

        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"
        if torch.cuda.is_available():
            return "cuda"
    except ImportError:
        pass
    return "cpu"


class RerankingService:

    def __init__(
        self,
        backend: Optional[str] = None,
        device: Optional[str] = None,
    ):
        self._backend_override = backend
        self._device = device
        self._local_model = None

    @property
    def backend(self) -> str:
        if self._backend_override:
            return self._backend_override.lower()
        return os.getenv("RERANKER_BACKEND", RERANKER_BACKEND).lower()

    @property
    def device(self) -> str:
        if self._device is None:
            self._device = get_optimal_device()
        return self._device

    @device.setter
    def device(self, val: str):
        self._device = val

    def _get_local_model(self):
        if self._local_model is None:
            from sentence_transformers import CrossEncoder

            self._local_model = CrossEncoder(
                "cross-encoder/ms-marco-MiniLM-L-6-v2",
                device=self.device,
            )
        return self._local_model

    @property
    def model(self):
        """Lazy property for backward compatibility with existing callers/tests."""
        return self._get_local_model()

    def _rerank_local(
        self,
        query: str,
        results: List[RetrievalResult],
        top_k: int,
    ) -> List[RetrievalResult]:
        try:
            model = self._get_local_model()
            pairs = [
                (query, result.chunk.chunk_text)
                for result in results
            ]
            scores = model.predict(pairs)

            ranked_results = sorted(
                zip(results, scores),
                key=lambda item: float(item[1]),
                reverse=True,
            )
            return [
                result
                for result, score in ranked_results[:top_k]
            ]
        except Exception as e:
            logger.warning(f"Local reranker failed (failing open to fused order): {e}")
            return results[:top_k]

    def _rerank_voyage(
        self,
        query: str,
        results: List[RetrievalResult],
        top_k: int,
    ) -> List[RetrievalResult]:
        try:
            import voyageai

            api_key = os.getenv("VOYAGE_API_KEY")
            model = os.getenv("VOYAGE_RERANK_MODEL", VOYAGE_RERANK_MODEL)

            documents = [result.chunk.chunk_text for result in results]

            client = voyageai.Client(api_key=api_key, timeout=8.0)
            response = client.rerank(
                query=query,
                documents=documents,
                model=model,
                top_k=top_k,
            )

            if not response or not hasattr(response, "results") or response.results is None:
                logger.warning("Voyage rerank returned empty or invalid response; failing open to fused order")
                return results[:top_k]

            reranked: List[RetrievalResult] = []
            for item in response.results:
                if 0 <= item.index < len(results):
                    reranked.append(results[item.index])

            if not reranked:
                logger.warning("Voyage rerank returned no indexed results; failing open to fused order")
                return results[:top_k]

            return reranked[:top_k]
        except Exception as e:
            logger.warning(f"Voyage rerank failed (failing open to fused order): {e}")
            return results[:top_k]

    @staticmethod
    def _get_onnx_resources():
        global _onnx_session, _onnx_tokenizer
        if _onnx_session is not None and _onnx_tokenizer is not None:
            return _onnx_session, _onnx_tokenizer

        with _onnx_lock:
            if _onnx_session is None or _onnx_tokenizer is None:
                import onnxruntime as ort
                from tokenizers import Tokenizer

                m_path = ONNX_RERANKER_MODEL_PATH
                if not m_path or not os.path.exists(m_path):
                    default_m = Path(__file__).resolve().parent.parent.parent / "models" / "reranker" / "model.onnx"
                    if default_m.exists():
                        m_path = str(default_m)
                    else:
                        from huggingface_hub import hf_hub_download
                        m_path = hf_hub_download("cross-encoder/ms-marco-MiniLM-L-6-v2", "onnx/model_qint8_arm64.onnx")

                t_path = ONNX_RERANKER_TOKENIZER_PATH
                if not t_path or not os.path.exists(t_path):
                    default_t = Path(__file__).resolve().parent.parent.parent / "models" / "reranker" / "tokenizer.json"
                    if default_t.exists():
                        t_path = str(default_t)
                    else:
                        from huggingface_hub import hf_hub_download
                        t_path = hf_hub_download("cross-encoder/ms-marco-MiniLM-L-6-v2", "tokenizer.json")

                tokenizer = Tokenizer.from_file(str(t_path))
                tokenizer.enable_truncation(max_length=512)
                tokenizer.enable_padding(pad_id=0, pad_token="[PAD]")

                sess_opts = ort.SessionOptions()
                sess_opts.intra_op_num_threads = 1
                sess_opts.inter_op_num_threads = 1
                session = ort.InferenceSession(
                    str(m_path),
                    sess_opts,
                    providers=["CPUExecutionProvider"],
                )

                _onnx_tokenizer = tokenizer
                _onnx_session = session

        return _onnx_session, _onnx_tokenizer

    def _rerank_onnx(
        self,
        query: str,
        results: List[RetrievalResult],
        top_k: int,
    ) -> List[RetrievalResult]:
        try:
            if not results:
                return []

            session, tokenizer = self._get_onnx_resources()

            all_pairs = [
                (query, result.chunk.chunk_text)
                for result in results
            ]
            all_scores = []
            batch_size = 20

            for i in range(0, len(all_pairs), batch_size):
                batch_pairs = all_pairs[i : i + batch_size]
                encs = tokenizer.encode_batch(batch_pairs)
                input_ids = np.array([e.ids for e in encs], dtype=np.int64)
                attention_mask = np.array([e.attention_mask for e in encs], dtype=np.int64)
                token_type_ids = np.array([e.type_ids for e in encs], dtype=np.int64)

                outputs = session.run(
                    None,
                    {
                        "input_ids": input_ids,
                        "attention_mask": attention_mask,
                        "token_type_ids": token_type_ids,
                    },
                )
                scores = outputs[0].flatten().tolist()
                all_scores.extend(scores)

            ranked_results = sorted(
                zip(results, all_scores),
                key=lambda item: float(item[1]),
                reverse=True,
            )
            return [
                result
                for result, score in ranked_results[:top_k]
            ]
        except Exception as e:
            logger.warning(f"ONNX reranker failed (failing open to fused order): {e}")
            return results[:top_k]

    def rerank(
        self,
        query: str,
        results: List[RetrievalResult],
        top_k: int = 5,
    ) -> List[RetrievalResult]:
        if not results:
            return []

        active_backend = self.backend
        if active_backend == "none":
            return results[:top_k]
        elif active_backend == "onnx":
            return self._rerank_onnx(query=query, results=results, top_k=top_k)
        elif active_backend == "voyage":
            return self._rerank_voyage(query=query, results=results, top_k=top_k)
        elif active_backend == "local":
            return self._rerank_local(query=query, results=results, top_k=top_k)
        else:
            logger.warning(f"Unknown reranker backend '{active_backend}', failing open to fused order")
            return results[:top_k]
