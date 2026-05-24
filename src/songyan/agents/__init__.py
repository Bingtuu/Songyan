"""Songyan Agents — 多 Agent 写作系统核心."""

from songyan.agents.context_manager import assemble_context_package
from songyan.agents.creative_director import generate_creative_brief
from songyan.agents.goal_planner import define_chapter_goal
from songyan.agents.llm_auditor import run_llm_audit, save_llm_audit
from songyan.agents.rule_auditor import run_rule_audit, save_rule_audit
from songyan.agents.writer import write_chapter

__all__ = [
    "assemble_context_package",
    "define_chapter_goal",
    "generate_creative_brief",
    "run_llm_audit",
    "run_rule_audit",
    "save_llm_audit",
    "save_rule_audit",
    "write_chapter",
]
