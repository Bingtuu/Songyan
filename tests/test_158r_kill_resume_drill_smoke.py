"""Task 158r Layer 2 冒烟测试：kill→resume 演练脚本.

不调用真实 LLM；只验证脚本常量隔离、报告渲染断言逻辑、in-flight kill 钩子行为。
真正的 §1.3-R 命令级证据由 Layer 3 实跑（docs/reports/task-158r-kill-resume-drill-report.md）背书。
"""

from __future__ import annotations

import pytest

import scripts.run_158r_kill_resume_drill as drill


class TestConstantsIsolation:
    def test_default_range_is_1_to_5(self) -> None:
        assert drill.START_CHAPTER == 1
        assert drill.END_CHAPTER == 5
        assert drill.KILL_CHAPTER_DEFAULT == 3

    def test_paths_use_task158r_prefix(self) -> None:
        assert "task158r_kill_resume" in str(drill.DB_PATH)
        assert "task158r" in str(drill.EVIDENCE_PATH)
        assert "task158r_project" in str(drill.PROJECT_FILE)
        assert "task-158r" in str(drill.REPORT_PATH)

    def test_does_not_touch_task158_artifacts(self) -> None:
        # 绝不能覆盖已冻结的 Task 158 证据
        for path in (
            drill.DB_PATH,
            drill.EVIDENCE_PATH,
            drill.PROJECT_FILE,
            drill.REPORT_PATH,
        ):
            assert "task158_ch1_ch100" not in str(path)
            assert "task-158-ch1-ch100" not in str(path)

    def test_reuses_base_builders(self) -> None:
        # 复用 158 的项目/大纲构造器，保证同口径
        assert drill.base._project_setting is not None
        assert drill.base._build_outline is not None


class TestReportRendering:
    def _all_pass_outcomes(self) -> tuple[dict, dict]:
        kill = {
            "kill_at_chapter": 3,
            "interrupted": True,
            "interrupt_msg": "simulated in-flight kill at chapter 3",
            "accepted_before": [],
            "accepted_after": [1, 2],
            "run_id": "run-abc",
            "run_status": "running",
            "current_chapter": 3,
            "checkpoint_threads_after": 3,
        }
        resume = {
            "resume": True,
            "run_id": "run-abc",
            "run_status": "completed",
            "final_status": "completed",
            "accepted_before": [1, 2],
            "accepted_after": [1, 2, 3, 4, 5],
            "chapters_completed": [1, 2, 3, 4, 5],
            "chapters_failed": [],
            "checkpoint_threads_before": 3,
            "checkpoint_threads_after": 3,
            "chapter_heads": [
                {"chapter_number": c, "status": "accepted", "has_accepted": 1}
                for c in range(1, 6)
            ],
        }
        return kill, resume

    def test_all_pass_report(self, tmp_path, monkeypatch) -> None:
        report_path = tmp_path / "report.md"
        monkeypatch.setattr(drill, "REPORT_PATH", report_path)
        kill, resume = self._all_pass_outcomes()
        drill._write_report("proj-x", kill, resume)
        text = report_path.read_text(encoding="utf-8")
        # 五项断言全 ✅，无 🔴
        assert "🔴" not in text
        assert text.count("✅") >= 5
        assert "取得**真实命令级证据**" in text
        assert "run-abc" in text

    def test_run_id_mismatch_flags_failure(self, tmp_path, monkeypatch) -> None:
        report_path = tmp_path / "report.md"
        monkeypatch.setattr(drill, "REPORT_PATH", report_path)
        kill, resume = self._all_pass_outcomes()
        resume["run_id"] = "run-different"  # run_id 不复用 → 断言失败
        drill._write_report("proj-x", kill, resume)
        text = report_path.read_text(encoding="utf-8")
        assert "🔴" in text
        assert "未完全满足断言" in text

    def test_inflight_not_recomputed_flags_failure(
        self, tmp_path, monkeypatch
    ) -> None:
        report_path = tmp_path / "report.md"
        monkeypatch.setattr(drill, "REPORT_PATH", report_path)
        kill, resume = self._all_pass_outcomes()
        # Ch3 未进入最终 accepted 集合 → in-flight 未重算，断言失败
        resume["accepted_after"] = [1, 2, 4, 5]
        drill._write_report("proj-x", kill, resume)
        text = report_path.read_text(encoding="utf-8")
        assert "🔴" in text

    def test_not_interrupted_flags_failure(self, tmp_path, monkeypatch) -> None:
        report_path = tmp_path / "report.md"
        monkeypatch.setattr(drill, "REPORT_PATH", report_path)
        kill, resume = self._all_pass_outcomes()
        kill["interrupted"] = False  # 未被打断 → 非 in-flight kill
        drill._write_report("proj-x", kill, resume)
        text = report_path.read_text(encoding="utf-8")
        assert "🔴" in text


class TestInflightKillHook:
    async def test_hook_raises_only_at_target_chapter(self) -> None:
        calls: list[int] = []

        async def _fake_run(**kwargs):
            calls.append(kwargs["chapter_number"])
            return {"thread_id": f"thread-{kwargs['chapter_number']}"}

        drill.phase2_graph.run_chapter_pipeline = _fake_run
        try:
            drill._install_inflight_kill_hook(3)
            wrapped = drill.phase2_graph.run_chapter_pipeline

            # 非目标章正常返回
            state = await wrapped(chapter_number=2)
            assert state["thread_id"] == "thread-2"

            # 目标章：生成后（_fake_run 已被调用）抛 KeyboardInterrupt
            with pytest.raises(KeyboardInterrupt):
                await wrapped(chapter_number=3)
            assert 3 in calls  # 证明是"生成完成后"才打断
        finally:
            drill.phase2_graph.run_chapter_pipeline = _fake_run
