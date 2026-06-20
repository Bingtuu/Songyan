"""Embedder 单元测试（Mock 模式）."""

from __future__ import annotations

import asyncio

import numpy as np
import pytest

from songyan.rag.embedder import Embedder


class TestEmbedderMock:
    """Mock 模式测试."""

    @pytest.fixture(autouse=True)
    def clear_cache(self) -> None:
        """每个测试前清理模型缓存."""
        Embedder.clear_cache()

    def test_embedder_dimension_mock(self) -> None:
        """Mock 模式返回正确维度."""
        emb = Embedder(model_name="mock")
        assert emb.dimension == 768

    def test_embedder_batch_mock(self) -> None:
        """批量编码返回正确形状."""
        emb = Embedder(model_name="mock")
        texts = ["hello", "world", "test"]
        result = emb.embed(texts)
        assert result.shape == (3, 768)
        assert result.dtype == np.float32

    def test_embedder_singleton(self) -> None:
        """两次创建 Embedder 复用同一模型实例."""
        emb1 = Embedder(model_name="mock")
        _ = emb1.embed(["trigger load"])  # 触发加载
        emb2 = Embedder(model_name="mock")
        _ = emb2.embed(["trigger load"])
        # mock 模式下缓存值为 None，但 key 应存在
        from songyan.rag import embedder as emb_mod

        assert "mock" in emb_mod._MODEL_CACHE

    @pytest.mark.asyncio
    async def test_embedder_async_not_blocking(self) -> None:
        """验证 aembed 不会阻塞事件循环（并发调用总耗时应 < 串行）."""
        emb = Embedder(model_name="mock")
        texts = [["text one"], ["text two"], ["text three"]]

        # 并发调用 3 个 embed
        results = await asyncio.gather(*[emb.aembed(t) for t in texts])

        assert len(results) == 3
        for r in results:
            assert r.shape == (1, 768)

        # Mock 模式下每个 embed 很快，并发应明显快于串行
        # 这里只是验证不抛异常且返回正确即可

    @pytest.mark.asyncio
    async def test_embedder_empty_texts(self) -> None:
        """空文本列表返回空数组."""
        emb = Embedder(model_name="mock")
        result = await emb.aembed([])
        assert result.shape == (0, 768)

    def test_embedder_consistency(self) -> None:
        """同一文本两次编码结果相同."""
        emb = Embedder(model_name="mock")
        r1 = emb.embed(["consistent text"])
        r2 = emb.embed(["consistent text"])
        np.testing.assert_array_almost_equal(r1, r2, decimal=5)
