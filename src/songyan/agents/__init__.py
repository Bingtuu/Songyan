"""Songyan Agents — 多 Agent 写作系统核心."""

from songyan.agents.context_manager import assemble_context_package
from songyan.agents.creative_director import generate_creative_brief
from songyan.agents.goal_planner import define_chapter_goal
from songyan.agents.literary_auditor import run_literary_audit, save_literary_audit
from songyan.agents.llm_auditor import run_llm_audit, save_llm_audit
from songyan.agents.revision_handler import run_revision, save_revision_output
from songyan.agents.rule_auditor import run_rule_audit, save_rule_audit
from songyan.agents.settlement_extractor import apply_settlement, extract_settlement
from songyan.agents.writer import write_chapter

__all__ = [
    "apply_settlement",
    "assemble_context_package",
    "define_chapter_goal",
    "extract_settlement",
    "generate_creative_brief",
    "run_literary_audit",
    "run_llm_audit",
    "run_revision",
    "run_rule_audit",
    "save_literary_audit",
    "save_llm_audit",
    "save_revision_output",
    "save_rule_audit",
    "write_chapter",
]
