"""Task 136: 从已完成的验证项目重新采集指标并生成报告.

用法:
    python scripts/_task136_recollect_metrics.py <project_id>
"""

from __future__ import annotations

import asyncio
import sys

from run_136_v52_enforce_validation import (
    _collect_metrics,
    _evaluate,
    _generate_report,
    _load_baseline_metrics,
)


async def main(project_id: str) -> None:
    print(f"Recollecting metrics for project {project_id}...")
    metrics = await _collect_metrics(project_id)
    baseline = await _load_baseline_metrics()
    evaluation = _evaluate(metrics, baseline)
    _generate_report(metrics, baseline, evaluation, halt_reason=None)
    print("\n=== Evaluation summary ===")
    print(f"Completion rate: {evaluation['completion_rate']:.2%}")
    print(f"Multi-scene ratio: {evaluation['multi_scene_ratio']:.2%}")
    print(f"Settlement record ratio: {evaluation['settlement_record_ratio']:.2%}")
    print(f"Orphan rate Ch9-12: {evaluation['orphan_rate_9_12']}")
    print(f"Orphan rate Ch12-15: {evaluation['orphan_rate_12_15']}")
    print(f"Health Ch12: {evaluation['health_ch12']}, Ch15: {evaluation['health_ch15']}")
    print(f"Pass all criteria: {evaluation['pass_all']}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: python {sys.argv[0]} <project_id>")
        sys.exit(1)
    asyncio.run(main(sys.argv[1]))
