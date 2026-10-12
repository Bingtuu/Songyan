"""Canon loop (exp/canon-loop prototype): authoritative cross-chapter fact store.

store    — SQLite-backed canon entries; add-only, conflicts recorded & blocked.
extract  — LLM extractor turning an accepted chapter into canon facts.
verify   — deterministic + LLM checks of a draft against canon.
"""
