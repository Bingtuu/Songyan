"""Embedding 模型封装 — 懒加载、单例、异步线程池."""

from __future__ import annotations

import asyncio
from typing import Any

import numpy as np

# 模型单例缓存（进程内复用）
_MODEL_CACHE: dict[str, Any] = {}


class Embedder:
    """Embedding 模型封装.

    支持真实 sentence-transformers 模型和 Mock 模式（测试用）。
    模型首次调用时懒加载，并通过模块级缓存实现单例复用。
    """

    def __init__(
        self,
        model_name: str = "shibing624/text2vec-base-chinese",
        device: str = "cpu",
    ) -> None:
        self.model_name = model_name
        self.device = device
        self._dimension: int | None = None

    def _load_model(self) -> None:
        """懒加载模型（线程安全由 GIL 保证）."""
        if self.model_name in _MODEL_CACHE:
            self._model = _MODEL_CACHE[self.model_name]
            return

        if self.model_name == "mock":
            self._dimension = 768
            _MODEL_CACHE[self.model_name] = None
            return

        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError(
                "sentence-transformers is not installed. "
                "Install it with: pip install sentence-transformers"
            ) from exc

        model = SentenceTransformer(self.model_name, device=self.device)
        _MODEL_CACHE[self.model_name] = model
        self._model = model

    @property
    def dimension(self) -> int:
        """返回模型输出维度."""
        if self._dimension is not None:
            return self._dimension
        if self.model_name == "mock":
            self._dimension = 768
            return 768
        self._load_model()
        dim = self._model.get_sentence_embedding_dimension()
        self._dimension = dim
        return dim

    @classmethod
    def warm_up(cls, model_name: str = "shibing624/text2vec-base-chinese",
                device: str = "cpu") -> Embedder:
        """Preload Embedder model to avoid 5-20s lazy load delay."""
        emb = cls(model_name=model_name, device=device)
        emb._load_model()
        _ = emb.dimension
        return emb


    def embed(self, texts: list[str]) -> np.ndarray:
        """同步编码 — 调用方负责线程池包装.

        Returns:
            (N, D) float32 数组，L2 归一化
        """
        if not texts:
            return np.zeros((0, self.dimension), dtype=np.float32)

        if self.model_name == "mock":
            self._dimension = 768
            _MODEL_CACHE[self.model_name] = None
            rng = np.random.default_rng(seed=42)
            base = rng.random((len(texts), self.dimension)).astype(np.float32)
            for i, text in enumerate(texts):
                base[i] += hash(text) % 1000 / 10000
            norms = np.linalg.norm(base, axis=1, keepdims=True)
            return base / np.maximum(norms, 1e-9)

        try:
            self._load_model()
            embeddings = self._model.encode(
                texts,
                convert_to_numpy=True,
                normalize_embeddings=True,
            )
            return embeddings.astype(np.float32)
        except Exception as exc:
            import structlog

            _logger = structlog.get_logger(__name__)
            _logger.warning(
                "embedder.encode_failed",
                error=str(exc),
                model_name=self.model_name,
                text_count=len(texts),
            )
            return np.zeros((len(texts), self.dimension), dtype=np.float32)

    async def aembed(self, texts: list[str]) -> np.ndarray:
        """异步编码 — 在线程池中执行同步 encode.

        避免阻塞 asyncio 事件循环。
        """
        loop = asyncio.get_event_loop()
        return await asyncio.wait_for(
            loop.run_in_executor(None, self.embed, texts),
            timeout=120.0
        )

    @classmethod
    def clear_cache(cls) -> None:
        """清除模型缓存（主要用于测试）."""
        _MODEL_CACHE.clear()
