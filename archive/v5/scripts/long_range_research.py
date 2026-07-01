"""100+ 章长程架构调研 — 四个候选方案的 MVP 实验脚本.

运行方式:
    python scripts/long_range_research.py

输出:
    docs/architecture/long_range_research_data.json
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
CHAPTERS_DIR = BASE_DIR / "projects" / "orbital_horror" / "chapters"
OUTPUT_PATH = BASE_DIR / "docs" / "architecture" / "long_range_research_data.json"

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------


def load_chapters() -> dict[int, str]:
    """加载 Ch2~Ch11 文本，返回 {chapter_number: content}."""
    contents: dict[int, str] = {}
    for path in sorted(CHAPTERS_DIR.glob("chapter_*.md")):
        match = re.search(r"chapter_(\d+)", path.name)
        if not match:
            continue
        ch_num = int(match.group(1))
        text = path.read_text(encoding="utf-8")
        # 移除 frontmatter
        if text.startswith("---"):
            parts = text.split("---", 2)
            if len(parts) >= 3:
                text = parts[2]
        contents[ch_num] = text.strip()
    return contents


def split_into_paragraphs(text: str) -> list[str]:
    """将文本切分为段落列表."""
    return [p.strip() for p in text.split("\n\n") if p.strip()]


def split_into_chunks(text: str, chunk_size: int = 500) -> list[str]:
    """将文本按 chunk_size 字切分（保持句子边界）."""
    chunks: list[str] = []
    current = ""
    for sentence in re.split(r"([。！？\n])", text):
        if not sentence:
            continue
        if len(current) + len(sentence) > chunk_size and current:
            chunks.append(current)
            current = sentence
        else:
            current += sentence
    if current:
        chunks.append(current)
    return chunks


# ---------------------------------------------------------------------------
# 方案 A: 叙事知识图谱 (Narrative Knowledge Graph)
# ---------------------------------------------------------------------------


def build_narrative_graph(
    chapters: dict[int, str], entities: list[str]
) -> dict[str, Any]:
    """用 networkx 构建共现图，返回实验结果."""
    try:
        import networkx as nx
    except ImportError:
        logger.error("networkx not installed")
        return {"error": "networkx not installed"}

    graph = nx.Graph()

    # 添加节点
    for entity in entities:
        graph.add_node(entity, type="entity")

    # 添加边（共现）
    edge_weights: dict[tuple[str, str], int] = {}
    for ch_num, text in chapters.items():
        paragraphs = split_into_paragraphs(text)
        for para in paragraphs:
            present = [e for e in entities if e in para]
            for i, e1 in enumerate(present):
                for e2 in present[i + 1 :]:
                    key = tuple(sorted((e1, e2)))
                    edge_weights[key] = edge_weights.get(key, 0) + 1

    for (e1, e2), weight in edge_weights.items():
        graph.add_edge(e1, e2, weight=weight)

    # 实验 1: 查询 "120Hz干扰器" 的关联实体
    query = "120Hz干扰器"
    results: dict[str, Any] = {
        "node_count": graph.number_of_nodes(),
        "edge_count": graph.number_of_edges(),
        "queries": [],
    }

    if query in graph:
        neighbors = sorted(
            graph.neighbors(query),
            key=lambda n: graph[query][n]["weight"],
            reverse=True,
        )
        results["queries"].append({
            "query": query,
            "top_neighbors": [
                {"entity": n, "weight": graph[query][n]["weight"]} for n in neighbors[:10]
            ],
            "neighbor_count": len(neighbors),
        })
    else:
        results["queries"].append({
            "query": query,
            "error": "Entity not in graph",
        })

    # 实验 2: 检查关键设定是否连通
    critical_pairs = [
        ("认知补丁", "林渊"),
        ("第7实验区", "异质"),
        ("守门人", "AI"),
    ]
    connectivity: list[dict[str, Any]] = []
    for a, b in critical_pairs:
        if a in graph and b in graph:
            try:
                path = nx.shortest_path(graph, a, b)
                connectivity.append({
                    "source": a,
                    "target": b,
                    "connected": True,
                    "path_length": len(path) - 1,
                    "path": path,
                })
            except nx.NetworkXNoPath:
                connectivity.append({
                    "source": a,
                    "target": b,
                    "connected": False,
                })
        else:
            connectivity.append({
                "source": a,
                "target": b,
                "connected": False,
                "reason": "missing_node",
            })

    results["connectivity"] = connectivity
    return results


# ---------------------------------------------------------------------------
# 方案 B: RAG + 分层摘要混合
# ---------------------------------------------------------------------------


def build_rag_index(
    chapters: dict[int, str]
) -> dict[str, Any]:
    """用 sentence-transformers 构建向量索引，返回实验结果."""
    try:
        import numpy as np
        from sentence_transformers import SentenceTransformer
    except ImportError:
        logger.error("sentence-transformers not installed")
        return {"error": "sentence-transformers not installed"}

    model = SentenceTransformer("all-MiniLM-L6-v2")

    # 构建 chunk 库
    chunks: list[dict[str, Any]] = []
    for ch_num, text in chapters.items():
        for idx, chunk_text in enumerate(split_into_chunks(text, 500)):
            chunks.append({
                "chapter": ch_num,
                "chunk_index": idx,
                "text": chunk_text[:200],  # 存储前 200 字作为摘要
            })

    if not chunks:
        return {"error": "No chunks generated"}

    # 生成向量
    texts = [c["text"] for c in chunks]
    embeddings = model.encode(texts, convert_to_numpy=True, show_progress_bar=False)

    # 实验: 查询
    queries = ["认知补丁", "第6代实验体", "120Hz干扰器", "守门人"]
    results: list[dict[str, Any]] = []

    for query in queries:
        q_emb = model.encode([query], convert_to_numpy=True)
        # 余弦相似度
        similarities = np.dot(embeddings, q_emb.T).flatten()
        top_indices = np.argsort(similarities)[::-1][:5]

        results.append({
            "query": query,
            "top_5": [
                {
                    "chapter": chunks[i]["chapter"],
                    "chunk_index": chunks[i]["chunk_index"],
                    "similarity": float(similarities[i]),
                    "text_preview": chunks[i]["text"][:80],
                }
                for i in top_indices
            ],
        })

    return {
        "chunk_count": len(chunks),
        "embedding_dim": int(embeddings.shape[1]),
        "queries": results,
    }


# ---------------------------------------------------------------------------
# 方案 C: 专用叙事记忆 LLM (模拟)
# ---------------------------------------------------------------------------


def simulate_narrative_memory(
    chapters: dict[int, str]
) -> dict[str, Any]:
    """模拟叙事记忆 Agent — 构造状态文档并评估信息保留率."""

    # 手工构造关键实体列表（从 seed 配置和文本中提炼）
    world_state = {
        "location": "盖亚环空间站",
        "key_factions": ["空间站管理层", "第7实验区研究团队", "守门人AI"],
        "critical_settings": [
            "异质", "认知补丁", "120Hz干扰器", "第7实验区",
            "守门人", "神经接口疤痕", "深空打捞队",
        ],
        "character_states": {
            "林渊": {"role": "主角", "location": "盖亚环", "mental": "压抑的警觉"},
            "陈知秋": {"role": "导师/反派", "status": "被感染"},
            "守门人": {"role": "AI", "knowledge": "知道一切"},
        },
    }

    # 模拟：每读 3 章更新一次状态文档
    update_interval = 3
    document_versions: list[dict[str, Any]] = []

    sorted_chapters = sorted(chapters.items())
    for i in range(0, len(sorted_chapters), update_interval):
        batch = sorted_chapters[i : i + update_interval]
        max_ch = batch[-1][0] if batch else 0

        # 统计本章提及的关键设定
        mentioned = set()
        for _, text in batch:
            for setting in world_state["critical_settings"]:
                if setting in text:
                    mentioned.add(setting)

        document_versions.append({
            "up_to_chapter": max_ch,
            "settings_mentioned_in_batch": sorted(mentioned),
            "world_state_keys": list(world_state.keys()),
        })

    # 评估：所有批次中提及的设定集合
    all_mentioned: set[str] = set()
    for doc in document_versions:
        all_mentioned.update(doc["settings_mentioned_in_batch"])

    coverage = len(all_mentioned) / len(world_state["critical_settings"])

    return {
        "document_versions": document_versions,
        "total_settings": len(world_state["critical_settings"]),
        "settings_ever_mentioned": len(all_mentioned),
        "coverage_rate": coverage,
        "assumption": (
            "Hand-crafted world_state; simulates Narrative Memory Agent "
            "updates every 3 chapters"
        ),
    }


# ---------------------------------------------------------------------------
# 方案 D: 人类辅助记忆 (原型设计)
# ---------------------------------------------------------------------------


def design_human_augmented_memory() -> dict[str, Any]:
    """设计人类辅助记忆系统的原型规格."""
    return {
        "schema": {
            "table": "human_marks",
            "columns": [
                "mark_id TEXT PRIMARY KEY",
                "project_id TEXT NOT NULL",
                "mark_type TEXT",  # setting | character | foreshadowing
                "target_key TEXT NOT NULL",
                "note TEXT",
                "priority INTEGER DEFAULT 5",  # 1~10
                "created_at TEXT",
            ],
        },
        "cli_commands": [
            "songyan mark-critical --project-id xxx --setting '120Hz干扰器' --note '核心道具'",
            "songyan mark-list --project-id xxx",
            "songyan mark-remove --mark-id xxx",
        ],
        "integration_points": [
            "ContextManager._assemble_context: 优先加载 priority>=8 的 marks",
            "SettlementExtractor: 人类确认后的 setting 自动 mark",
            "ContinuityAuditor: 未 mark 但 orphaned 的设定报告给人类",
        ],
        "prototype_status": (
            "Schema designed, CLI mocked, integration spec written. "
            "No runtime code."
        ),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    logger.info("research.starting")
    chapters = load_chapters()
    logger.info("research.chapters_loaded", count=len(chapters), chapters=sorted(chapters.keys()))

    if not chapters:
        logger.error("research.no_chapters_found")
        return

    # 定义实体列表（从已知文本 + seed 配置中提炼）
    entities = [
        "林渊", "陈知秋", "守门人", "老赵", "老雷",
        "盖亚环", "第7实验区", "异质", "认知补丁",
        "120Hz干扰器", "神经接口", "深空打捞队",
        "AI", "样本", "空间站", "D区", "C区",
    ]

    start_a = time.perf_counter()
    result_a = build_narrative_graph(chapters, entities)
    duration_a = time.perf_counter() - start_a

    start_b = time.perf_counter()
    result_b = build_rag_index(chapters)
    duration_b = time.perf_counter() - start_b

    start_c = time.perf_counter()
    result_c = simulate_narrative_memory(chapters)
    duration_c = time.perf_counter() - start_c

    result_d = design_human_augmented_memory()

    output = {
        "dataset": {
            "project": "轨道上的怪谈",
            "chapters": sorted(chapters.keys()),
            "total_words": sum(len(t) for t in chapters.values()),
        },
        "scheme_a_narrative_kg": {
            **result_a,
            "duration_ms": int(duration_a * 1000),
        },
        "scheme_b_rag": {
            **result_b,
            "duration_ms": int(duration_b * 1000),
        },
        "scheme_c_narrative_memory": {
            **result_c,
            "duration_ms": int(duration_c * 1000),
        },
        "scheme_d_human_augmented": result_d,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("research.complete", output_path=str(OUTPUT_PATH))


if __name__ == "__main__":
    main()
