#!/usr/bin/env bash
# RAG A/B 测试脚本 — 运行对照组与实验组对比
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# 参数解析
SEED_CONFIG="${1:-evals/seeds/xuanhuan_webnovel.json}"
SEED_CHAPTER="${2:-evals/seeds/chapters/xuanhuan_ch1.md}"
CHAPTER_RANGE="${3:-12-20}"
MODE_ID="${4:-webnovel}"
OUTPUT_DIR="${5:-evals/output}"
DRY_RUN="${6:-}"

echo "========================================"
echo "  RAG A/B 测试"
echo "========================================"
echo "种子配置:  $SEED_CONFIG"
echo "种子章节:  $SEED_CHAPTER"
echo "章节范围:  $CHAPTER_RANGE"
echo "创作模式:  $MODE_ID"
echo "输出目录:  $OUTPUT_DIR"
echo "========================================"

# 运行 A/B 测试
ARGS=(
  --seed-config "$SEED_CONFIG"
  --seed-chapter "$SEED_CHAPTER"
  --chapters "$CHAPTER_RANGE"
  --mode-id "$MODE_ID"
  --output-dir "$OUTPUT_DIR"
  --sample-count 20
)

if [ -n "$DRY_RUN" ]; then
  ARGS+=(--dry-run)
  echo "[DRY RUN 模式 — Mock 运行，不实际调用 LLM]"
fi

python -m evals.rag_ab_test "${ARGS[@]}"

echo "========================================"
echo "  A/B 测试完成"
echo "========================================"
