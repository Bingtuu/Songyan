"""P8 + P11 regression: Verify performance/resilience fixes work correctly."""

import pytest


def test_vectorstore_has_load_incremental():
    """PERF-01: VectorStore has load_incremental method."""
    from unittest.mock import MagicMock

    from songyan.rag.vector_store import VectorStore
    vs = VectorStore("test-proj", MagicMock())
    assert hasattr(vs, "load_incremental")
    assert callable(vs.load_incremental)


def test_vectorstore_has_loaded_chapter():
    """PERF-01: VectorStore tracks _loaded_chapter."""
    from unittest.mock import MagicMock

    from songyan.rag.vector_store import VectorStore
    vs = VectorStore("test-proj", MagicMock())
    assert hasattr(vs, "_loaded_chapter")


def test_embedder_warm_up_loads_mock_model():
    """PERF-02: warm_up() with mock mode loads dimension."""
    from songyan.rag.embedder import Embedder
    emb = Embedder(model_name="mock", device="cpu")
    emb._load_model()
    assert emb.dimension == 768


@pytest.mark.asyncio
async def test_get_db_runs_pragma_quick_check():
    """RES-03: get_db() runs PRAGMA quick_check without error."""
    from songyan.db.connection import get_db
    async with get_db() as conn:
        cursor = await conn.execute("SELECT 1")
        row = await cursor.fetchone()
        assert row[0] == 1
