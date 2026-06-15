"""Embedding 基准测试查询集 — 《轨道上的怪谈》Ch2~Ch11."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class BenchmarkQuery:
    """单个查询定义."""

    query: str
    expected_chapters: list[int]
    query_type: Literal["entity", "relationship", "semantic"]
    description: str = ""


# =============================================================================
# 核心查询集（10 个查询）
# =============================================================================

DEFAULT_QUERIES: list[BenchmarkQuery] = [
    # --- Task 039 复用（4 个）---
    BenchmarkQuery(
        query="认知补丁",
        expected_chapters=[3, 4],
        query_type="entity",
        description="Ch3 首次出现的精神稳定装置，Ch4 后几乎完全消失",
    ),
    BenchmarkQuery(
        query="第6代实验体",
        expected_chapters=[7, 10],
        query_type="entity",
        description="Ch7 Scene 2 唤醒的男人，Ch10 克隆体阵列中提及",
    ),
    BenchmarkQuery(
        query="120Hz干扰器",
        expected_chapters=[8],
        query_type="entity",
        description="Ch8 发现电磁干扰器+120赫兹可逼退异质生态",
    ),
    BenchmarkQuery(
        query="守门人",
        expected_chapters=[2, 4, 6, 9, 11],
        query_type="entity",
        description="贯穿全篇的 AI 监管者，身份从助手演进为灭绝协议",
    ),
    # --- 扩展查询（6 个）---
    BenchmarkQuery(
        query="钥匙碎片",
        expected_chapters=[5, 6, 7, 9, 11],
        query_type="entity",
        description="从 Ch5 金属碎片到 Ch11 改写第零条款的接口",
    ),
    BenchmarkQuery(
        query="方远舟",
        expected_chapters=[6, 7, 9, 10, 11],
        query_type="entity",
        description="核心配角，全息投影→死亡真相→身份反转",
    ),
    BenchmarkQuery(
        query="共生协议",
        expected_chapters=[9, 10, 11],
        query_type="relationship",
        description="Ch9 揭示的核心设定，涉及第零条款和轨道打击",
    ),
    BenchmarkQuery(
        query="第7实验区",
        expected_chapters=[2, 3, 7, 8],
        query_type="semantic",
        description="故事核心场景，封锁区域，异质生态源头",
    ),
    BenchmarkQuery(
        query="林渊断臂",
        expected_chapters=[11],
        query_type="relationship",
        description="Ch11 关键情节，切断左臂后共生体再生",
    ),
    BenchmarkQuery(
        query="异质生态",
        expected_chapters=[6, 7, 8, 11],
        query_type="semantic",
        description="外星生命形式，从 Ch6 首次正面接触到 Ch11 共生",
    ),
]
