"""Reject new test modules that revive numbered task filenames.

The allowlist is the set that already existed when the V1.0 assist
queue was opened. Keep those files green. Do not add a name here
to admit a new test. If a legacy file is renamed or removed, delete
its allowlist entry in the same change.
"""

from __future__ import annotations

import re
from pathlib import Path

_TESTS = Path(__file__).resolve().parent
_LEGACY = re.compile(r"(^test_(?:task\d+|v\d+|\d+)|task\d+)")

# Frozen legacy filenames. Not a menu of patterns to copy.
_ALLOW = frozenset(
    {
        "test_058d_integration.py",
        "test_076_word_count_truncation.py",
        "test_077a_setting_library.py",
        "test_077b_budget_hard_enforcement.py",
        "test_078_foreshadowing_lifecycle.py",
        "test_079_segmented_revision.py",
        "test_080_character_appearance_window.py",
        "test_086_dynamic_budget.py",
        "test_087_lifecycle_integration.py",
        "test_088_revision_word_limit.py",
        "test_100b_quality_gate.py",
        "test_100c_context_pressure.py",
        "test_104_budget_hard_ceiling.py",
        "test_105_streaming_validation.py",
        "test_106_scoring_system.py",
        "test_107_convergence_guardrail.py",
        "test_108_core_nodes.py",
        "test_119_reporting_wrapper.py",
        "test_122b_pipeline_scenarios.py",
        "test_122d_long_sequence_stability.py",
        "test_123_gates.py",
        "test_125_gate_thresholds.py",
        "test_127_gate_score_halt.py",
        "test_130_gate_mode.py",
        "test_139a_enforce_gate_audit.py",
        "test_141_narrative_skeleton.py",
        "test_142_project_outline.py",
        "test_143_goal_planner_topdown.py",
        "test_144_thread_economy.py",
        "test_145_stage_a_metrics.py",
        "test_146_quality_debt.py",
        "test_147_literary_trend.py",
        "test_148_foreshadowing_metrics.py",
        "test_149_input_side_demotion.py",
        "test_150_infer_category_tightening.py",
        "test_151_mr_adaptive_cap_and_relevance.py",
        "test_152_critical_resolve_abandon.py",
        "test_153_run_level_resume.py",
        "test_154_llm_rate_limit_and_budget.py",
        "test_155_failure_isolation.py",
        "test_156_in_run_db_maintenance.py",
        "test_157_v6_acceptance.py",
        "test_158_long_run_smoke.py",
        "test_158_t5_freeze.py",
        "test_158r_kill_resume_drill_smoke.py",
        "test_159_replication_smoke.py",
        "test_160_meta_tag_eradication.py",
        "test_161_paragraph_dedup.py",
        "test_162_timeline_consistency.py",
        "test_163_concept_budget.py",
        "test_164_text_cleanliness.py",
        "test_165_stage_w_smoke.py",
        "test_166a_replan_evaluation.py",
        "test_166b_replan_application.py",
        "test_167a_foreshadowing_schedule.py",
        "test_167b_schedule_injection.py",
        "test_168a_adaptive_gate_signal_snapshot.py",
        "test_168b_adaptive_gate_window_reporting.py",
        "test_169a_adaptive_halt_decision_engine.py",
        "test_169b_adaptive_halt_workflow_integration.py",
        "test_170_adaptive_gate_validation.py",
        "test_170c_near_duplicate.py",
        "test_170d_auditor_calibration.py",
        "test_170e_ensure_protagonist.py",
        "test_170j_experiment_harness.py",
        "test_170p_new_character_seeding.py",
        "test_171a_literary_keyword_wiring.py",
        "test_171d_three_tier_contract.py",
        "test_171p_state_mismatch_construct.py",
        "test_171t_text_cleanliness_final_sweep.py",
        "test_171u_d1_clean_application.py",
        "test_171v_literary_guardrails.py",
        "test_171w_guardrail_persistence.py",
        "test_171w_text_guardrail_observe.py",
        "test_172a3_runtime_profile_injection.py",
        "test_172a5_gate_threshold_profile.py",
        "test_172a6_character_decay_profile.py",
        "test_172a_genre_runtime_profile.py",
        "test_172ap_foreshadowing_horizon_floor.py",
        "test_172bq_consistency_ced.py",
        "test_172cp_inventory_tracking.py",
        "test_172cq_inventory_identity.py",
        "test_172cr_foreshadowing_resolve.py",
        "test_172cs_wuxia_health_calibration.py",
        "test_172ct_wuxia_health_overdue_weight.py",
        "test_172d_cross_genre_guardrails.py",
        "test_172e_context_manager_profile_wiring.py",
        "test_172f_evaporation_profile_wiring.py",
        "test_172g_character_decay_profile_wiring.py",
        "test_172h_continuity_profile_wiring.py",
        "test_172j_pruner_max_shadowing_fix.py",
        "test_173_llm_client_cleanup.py",
        "test_173_pipeline_cleanup.py",
        "test_174_logging_setup.py",
        "test_175_budget_pause_propagation.py",
        "test_175_cost_tracking.py",
        "test_177_export_service.py",
        "test_178_resource_loading.py",
        "test_182_five_gate_tools.py",
        "test_183_profile_cli.py",
        "test_184_resource_json_schema.py",
        "test_185_t9_precision_fixes.py",
        "test_185_urban_calibration_harness.py",
        "test_191_ch200_harness.py",
        "test_193r_eval_caliber_fixes.py",
        "test_193t_overdue_actionable.py",
        "test_193v_setting_reference_terms.py",
        "test_193w_segment_audit_verdict.py",
        "test_196_excellence_sampling.py",
        "test_197_198_excellence_signals.py",
        "test_199_style_card_extraction.py",
        "test_200_voice_anchor_extraction.py",
        "test_201_judge_bias_analysis.py",
        "test_202_readability_feasibility.py",
        "test_203_excellence_report_integration.py",
        "test_204_kg_diff_spike.py",
        "test_205_facttrack_validity_interval.py",
        "test_206_storyline_tree_spike.py",
        "test_211_backup_restore.py",
        "test_213_run_bundle.py",
        "test_225_duplicate_content_guard.py",
        "test_235_import_segment.py",
        "test_236_import_replay.py",
        "test_237_import_lifecycle.py",
        "test_238_replay_observations.py",
        "test_239_settlement_sqlite_error.py",
        "test_241_foreshadowing_resolved_trace.py",
        "test_242_settlement_savepoint_isolation.py",
        "test_settlement_extractor_task134.py",
        "test_task135_continuity_governance.py",
        "test_task137_setting_recycling.py",
        "test_task138n_mandatory_reference_revision.py",
        "test_task138p_character_id_alias.py",
        "test_v12_beat_sheet_writer.py",
        "test_v12_plan_review_flow.py",
        "test_v12_startup_runtime_validation.py",
        "test_v12_startup_smoke_harness.py",
        "test_v12_supervision_spec.py",
        "test_v14_llm_role_routing.py",
    }
)


def test_no_new_legacy_numbered_test_files() -> None:
    """New tests use tests/<area>/test_<behavior>.py, not task numbers."""
    found = sorted(
        path.name
        for path in _TESTS.rglob('test_*.py')
        if _LEGACY.search(path.name)
    )
    extra = sorted(set(found) - _ALLOW)
    missing = sorted(_ALLOW - set(found))
    assert extra == [], "new legacy-style test names: " + ", ".join(extra)
    assert missing == [], (
        "allowlist names a removed file; delete that name instead of "
        "reusing it: " + ", ".join(missing)
    )
