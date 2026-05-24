-- Songyan V1.0 SQLite Schema
-- 13 tables, JSON fields for complex structures, WAL mode, FK enforcement

PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

-- ============================================================
-- 1. projects — 小说项目主表
-- ============================================================
CREATE TABLE IF NOT EXISTS projects (
    project_id      TEXT PRIMARY KEY,
    title           TEXT,
    genre_id        TEXT NOT NULL,
    mode_id         TEXT DEFAULT 'webnovel',
    protagonist_name TEXT NOT NULL,
    protagonist_background TEXT DEFAULT '',
    core_hook       TEXT DEFAULT '',
    target_reader_expectation TEXT DEFAULT '',
    taboos          TEXT DEFAULT '[]',           -- JSON array
    target_word_count INTEGER DEFAULT 100000,
    tone            TEXT DEFAULT '热血',
    reference_works TEXT DEFAULT '[]',           -- JSON array
    created_at      TEXT DEFAULT (datetime('now'))
);

-- ============================================================
-- 2. characters — 角色档案
-- ============================================================
CREATE TABLE IF NOT EXISTS characters (
    character_id    TEXT PRIMARY KEY,
    project_id      TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    role_type       TEXT DEFAULT 'protagonist',  -- protagonist | supporting | antagonist
    background      TEXT DEFAULT '',
    personality_traits TEXT DEFAULT '[]',        -- JSON array
    goals           TEXT DEFAULT '[]',           -- JSON array
    relationships   TEXT DEFAULT '{}',           -- JSON object
    created_at      TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_characters_project ON characters(project_id);

-- ============================================================
-- 3. chapter_goals — 章节目标（GoalPlanner 输出）
-- ============================================================
CREATE TABLE IF NOT EXISTS chapter_goals (
    goal_id         TEXT PRIMARY KEY,
    project_id      TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    chapter_number  INTEGER NOT NULL,
    previous_summary TEXT DEFAULT '',
    target_events   TEXT DEFAULT '[]',           -- JSON array
    emotional_arc   TEXT DEFAULT '',
    hooks           TEXT DEFAULT '[]',           -- JSON array
    obligations     TEXT DEFAULT '[]',           -- JSON array
    word_count_target INTEGER DEFAULT 3000,
    chapter_type    TEXT DEFAULT '',
    created_at      TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_goals_project_chapter ON chapter_goals(project_id, chapter_number);

-- ============================================================
-- 4. creative_briefs — 创作简报（CreativeDirector 输出）⭐
-- ============================================================
CREATE TABLE IF NOT EXISTS creative_briefs (
    brief_id        TEXT PRIMARY KEY,
    project_id      TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    chapter_number  INTEGER NOT NULL,
    mode_id         TEXT NOT NULL,
    creative_intent TEXT DEFAULT '',
    required_tensions TEXT DEFAULT '[]',         -- JSON array of Tension
    forbidden_patterns TEXT DEFAULT '[]',        -- JSON array
    allowed_fissures TEXT DEFAULT '[]',          -- JSON array
    style_constraints TEXT DEFAULT '[]',         -- JSON array
    reader_contract TEXT DEFAULT '',
    polyphony_notes TEXT DEFAULT '[]',           -- JSON array
    chapter_goal    TEXT DEFAULT '{}',           -- JSON object (ChapterGoal snapshot)
    created_at      TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_briefs_project_chapter ON creative_briefs(project_id, chapter_number);

-- ============================================================
-- 5. chapter_versions — 章节版本链（永远 INSERT，禁止 UPDATE）
-- ============================================================
CREATE TABLE IF NOT EXISTS chapter_versions (
    version_id          TEXT PRIMARY KEY,
    project_id          TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    chapter_number      INTEGER NOT NULL,
    version_number      INTEGER NOT NULL DEFAULT 1,
    version_type        TEXT NOT NULL DEFAULT 'draft',  -- draft | revision | accepted | edited
    content             TEXT DEFAULT '',
    word_count          INTEGER DEFAULT 0,
    scenes              TEXT DEFAULT '[]',       -- JSON array of dict
    generation_metadata TEXT DEFAULT '{}',       -- JSON object (含 context_snapshot + creative_brief)
    creative_brief_id   TEXT REFERENCES creative_briefs(brief_id) ON DELETE SET NULL,
    parent_version_id   TEXT REFERENCES chapter_versions(version_id) ON DELETE SET NULL,
    created_at          TEXT DEFAULT (datetime('now')),

    UNIQUE(project_id, chapter_number, version_number)
);

CREATE INDEX IF NOT EXISTS idx_versions_project_chapter ON chapter_versions(project_id, chapter_number);
CREATE INDEX IF NOT EXISTS idx_versions_parent ON chapter_versions(parent_version_id);

-- ============================================================
-- 6. chapter_heads — 章节头（指向当前版本和 accepted 版本）
-- ============================================================
CREATE TABLE IF NOT EXISTS chapter_heads (
    project_id          TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    chapter_number      INTEGER NOT NULL,
    current_version_id  TEXT REFERENCES chapter_versions(version_id) ON DELETE SET NULL,
    accepted_version_id TEXT REFERENCES chapter_versions(version_id) ON DELETE SET NULL,
    status              TEXT DEFAULT 'draft',    -- draft | under_review | accepted
    updated_at          TEXT DEFAULT (datetime('now')),

    PRIMARY KEY(project_id, chapter_number)
);

-- ============================================================
-- 7. character_states — 角色状态快照（永远 INSERT，不 UPDATE）⭐
-- ============================================================
CREATE TABLE IF NOT EXISTS character_states (
    state_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    character_id    TEXT NOT NULL REFERENCES characters(character_id) ON DELETE CASCADE,
    field           TEXT NOT NULL,
    value           TEXT NOT NULL,
    source_version_id TEXT NOT NULL REFERENCES chapter_versions(version_id) ON DELETE CASCADE,
    created_at      TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_states_character ON character_states(character_id);
CREATE INDEX IF NOT EXISTS idx_states_version ON character_states(source_version_id);

-- ============================================================
-- 8. literary_observations — 文学性诊断结果（不阻塞流程）⭐
-- ============================================================
CREATE TABLE IF NOT EXISTS literary_observations (
    observation_id          TEXT PRIMARY KEY,
    version_id              TEXT NOT NULL REFERENCES chapter_versions(version_id) ON DELETE CASCADE,
    auditor_id              TEXT DEFAULT 'literary_auditor',
    observations            TEXT DEFAULT '[]',   -- JSON array of LiteraryObservation
    literary_quality_score  REAL DEFAULT 0,
    character_autonomy_score REAL DEFAULT 0,
    conceptual_grounding_score REAL DEFAULT 0,
    fissure_preservation_score REAL DEFAULT 0,
    summary                 TEXT DEFAULT '',
    duration_ms             INTEGER DEFAULT 0,
    created_at              TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_lit_obs_version ON literary_observations(version_id);

-- ============================================================
-- 9. review_reports — 合并审查报告（Rule + LLM）⭐
-- ============================================================
CREATE TABLE IF NOT EXISTS review_reports (
    report_id           TEXT PRIMARY KEY,
    chapter_version_id  TEXT NOT NULL REFERENCES chapter_versions(version_id) ON DELETE CASCADE,
    audit_type          TEXT DEFAULT 'merged',   -- rule | llm | merged
    rule_audit_result   TEXT DEFAULT '{}',       -- JSON object (RuleAuditResult)
    llm_audit_result    TEXT DEFAULT '{}',       -- JSON object (LLMAuditResult)
    issues              TEXT DEFAULT '[]',       -- JSON array of ReviewIssue
    overall_score       REAL DEFAULT 0,
    ai_tell_count       INTEGER DEFAULT 0,
    fatigue_word_count  INTEGER DEFAULT 0,
    has_opening_hook    INTEGER DEFAULT 0,       -- 0/1 boolean
    has_ending_hook     INTEGER DEFAULT 0,       -- 0/1 boolean
    dimension_scores    TEXT DEFAULT '{}',       -- JSON object
    summary             TEXT DEFAULT '',
    created_at          TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_reports_version ON review_reports(chapter_version_id);

-- ============================================================
-- 10. foreshadowings — 伏笔线索 ⭐
-- ============================================================
CREATE TABLE IF NOT EXISTS foreshadowings (
    foreshadowing_id        TEXT PRIMARY KEY,
    project_id              TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    description             TEXT NOT NULL,
    planted_in_chapter      INTEGER NOT NULL,
    expected_resolve_chapter INTEGER,
    status                  TEXT DEFAULT 'planted',  -- planted | due | overdue | resolved
    source_version_id       TEXT REFERENCES chapter_versions(version_id) ON DELETE SET NULL,  -- ⭐
    created_at              TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_foreshadowings_project ON foreshadowings(project_id);
CREATE INDEX IF NOT EXISTS idx_foreshadowings_status ON foreshadowings(project_id, status);

-- ============================================================
-- 11. setting_snapshots — 设定快照（追踪设定演变）⭐
-- ============================================================
CREATE TABLE IF NOT EXISTS setting_snapshots (
    setting_id      TEXT PRIMARY KEY,
    project_id      TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    setting_name    TEXT NOT NULL,
    description     TEXT DEFAULT '',
    source_quote    TEXT DEFAULT '',
    setting_key     TEXT DEFAULT '',             -- ⭐ 设定唯一标识符，用于追踪演变
    created_at      TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_settings_project ON setting_snapshots(project_id);
CREATE INDEX IF NOT EXISTS idx_settings_key ON setting_snapshots(project_id, setting_key);

-- ============================================================
-- 12. numerical_ledgers — 数值账本（玄幻专用）
-- ============================================================
CREATE TABLE IF NOT EXISTS numerical_ledgers (
    ledger_id       TEXT PRIMARY KEY,
    project_id      TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    character_id    TEXT NOT NULL REFERENCES characters(character_id) ON DELETE CASCADE,
    attribute_name  TEXT NOT NULL,               -- e.g. cultivation_level, spirit_stones
    chapter_number  INTEGER NOT NULL,
    opening_value   REAL NOT NULL,
    increments      TEXT DEFAULT '[]',           -- JSON array of Increment
    decrements      TEXT DEFAULT '[]',           -- JSON array of Decrement
    closing_value   REAL NOT NULL,
    created_at      TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_ledgers_character ON numerical_ledgers(character_id, attribute_name);
CREATE INDEX IF NOT EXISTS idx_ledgers_project ON numerical_ledgers(project_id, chapter_number);

-- ============================================================
-- 13. summaries — 章节摘要（Settlement 后生成）
-- ============================================================
CREATE TABLE IF NOT EXISTS summaries (
    summary_id          TEXT PRIMARY KEY,
    project_id          TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    chapter_number      INTEGER NOT NULL,
    plot_summary        TEXT DEFAULT '',
    key_events          TEXT DEFAULT '[]',       -- JSON array
    characters_appeared TEXT DEFAULT '[]',       -- JSON array
    emotional_tone      TEXT DEFAULT '',
    created_at          TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_summaries_project ON summaries(project_id, chapter_number);
