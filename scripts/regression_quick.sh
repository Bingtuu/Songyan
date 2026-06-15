#!/usr/bin/env bash
# 快速回归测试：运行 mock 全量测试 + 1 个种子真实 LLM 评测
# 用法: bash scripts/regression_quick.sh [xuanhuan|urban|scifi]

set -euo pipefail

SEED="${1:-xuanhuan}"
OUTPUT_DIR="evals/output/regression_$(date +%Y%m%d_%H%M%S)"

echo "=== Step 1: Mock 全量测试 ==="
# 使用重定向避免前台 I/O 阻塞
python -m pytest tests/ -q > /tmp/pytest_regression.txt 2>&1
if [ $? -ne 0 ]; then
    echo "❌ Mock 测试失败"
    cat /tmp/pytest_regression.txt | tail -20
    exit 1
fi
tail -3 /tmp/pytest_regression.txt

echo ""
echo "=== Step 2: 真实 LLM 评测 ($SEED) ==="
echo "   输出目录: $OUTPUT_DIR"
echo "   预估成本: ~¥0.11, 耗时: ~2-3 分钟"

PYTHONPATH=. python scripts/run_real_llm_scifi.py \
    --seed-config "evals/seeds/${SEED}_webnovel.json" \
    --seed-chapter "evals/seeds/chapters/${SEED}_ch1.md" \
    --output-dir "$OUTPUT_DIR"

echo ""
echo "=== 回归完成 ==="
echo "   报告: $OUTPUT_DIR/summary.txt"
