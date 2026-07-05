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
    arc_boundaries  TEXT DEFAULT '[]',           -- JSON array of int
    volume_boundaries TEXT DEFAULT '[]',         -- JSON array of int
    -- Phase 8a: 项目种子配置增强
    estimated_chapters INTEGER DEFAULT 30,
    words_per_chapter INTEGER DEFAULT 3000,
    story_structure TEXT DEFAULT 'free',
    sub_genre_id TEXT,
    arc_boundaries_auto INTEGER DEFAULT 0,
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
    dialogue_style_card TEXT DEFAULT '{}',       -- JSON of DialogueStyleCard (Task 074)
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
    punch_points    TEXT DEFAULT '[]',           -- JSON array of PunchPoint
    emotion_arc     TEXT DEFAULT '[]',           -- JSON array of EmotionArcItem
    created_at      TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_briefs_project_chapter ON creative_briefs(project_id, chapter_number);

-- ============================================================
-- 4.5 setting_tracking — 设定生命周期追踪
-- ============================================================
CREATE TABLE IF NOT EXISTS setting_tracking (
    tracking_id             TEXT PRIMARY KEY,
    project_id              TEXT NOT NULL,
    setting_key             TEXT NOT NULL,
    setting_name            TEXT,
    description             TEXT,
    introduced_in_chapter   INTEGER,
    last_mentioned_chapter  INTEGER,
    expected_resolve_chapter INTEGER,
    status                  TEXT DEFAULT 'active',
    recovery_required       INTEGER DEFAULT 0,
    source_version_id       TEXT,
    resolved_chapter        INTEGER,
    resolved_version_id     TEXT,
    abandoned_chapter       INTEGER,
    abandoned_reason        TEXT,
    category                TEXT DEFAULT 'background' CHECK(category IN ('critical', 'recurring', 'background', 'technical', 'historical'))
);
CREATE INDEX IF NOT EXISTS idx_tracking_project ON setting_tracking(project_id);
CREATE INDEX IF NOT EXISTS idx_tracking_status ON setting_tracking(project_id, status);

-- ============================================================
-- 4.6 inventory_tracker — 道具/物品追踪
-- ============================================================
CREATE TABLE IF NOT EXISTS inventory_tracker (
    track_id            TEXT PRIMARY KEY,
    project_id          TEXT NOT NULL,
    character_id        TEXT,
    item_name           TEXT NOT NULL,
    item_description    TEXT,
    acquired_in_chapter INTEGER,
    last_used_chapter   INTEGER,
    status              TEXT DEFAULT 'held',
    expected_usage_chapter INTEGER
);
CREATE INDEX IF NOT EXISTS idx_inventory_project ON inventory_tracker(project_id);

-- ============================================================
-- 4.7 location_tracker — 角色位置追踪
-- ============================================================
CREATE TABLE IF NOT EXISTS location_tracker (
    track_id            TEXT PRIMARY KEY,
    project_id          TEXT NOT NULL,
    character_id        TEXT NOT NULL,
    location            TEXT NOT NULL,
    entered_in_chapter  INTEGER,
    last_confirmed_chapter INTEGER
);
CREATE INDEX IF NOT EXISTS idx_location_project ON location_tracker(project_id);

-- ============================================================
-- 4.8 continuity_reports — 连续性审计报告
-- ============================================================
CREATE TABLE IF NOT EXISTS continuity_reports (
    report_id               TEXT PRIMARY KEY,
    project_id              TEXT NOT NULL,
    checked_up_to_chapter   INTEGER,
    orphaned_settings       TEXT DEFAULT '[]',
    forgotten_items         TEXT DEFAULT '[]',
    state_mismatches        TEXT DEFAULT '[]',
    overdue_foreshadowings  TEXT DEFAULT '[]',
    overall_health_score    REAL DEFAULT 0,
    created_at              TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_continuity_project ON continuity_reports(project_id);

-- ============================================================
-- 4.5 human_instructions — 人类指令（HITL）
-- ============================================================
CREATE TABLE IF NOT EXISTS human_instructions (
    instruction_id  TEXT PRIMARY KEY,
    project_id      TEXT NOT NULL,
    chapter_number  INTEGER NOT NULL,
    gate_type       TEXT NOT NULL,
    action          TEXT NOT NULL,
    target_field    TEXT,
    content         TEXT NOT NULL,
    created_at      TEXT DEFAULT (datetime('now'))
);

-- ============================================================
-- 5. chapter_versions — 章节版本链（永远 INSERT，禁止 UPDATE）
-- ============================================================
CREATE TABLE IF NOT EXISTS chapter_versions (
    version_id          TEXT PRIMARY KEY,
    project_id          TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    chapter_number      INTEGER NOT NULL,
    version_number      INTEGER NOT NULL DEFAULT 1,
    version_type        TEXT NOT NULL DEFAULT 'draft',  -- draft | revision | accepted | edited
    is_abandoned        INTEGER NOT NULL DEFAULT 0,      -- 0 = active, 1 = abandoned (revision rebound)
    content             TEXT DEFAULT '',
    word_count          INTEGER DEFAULT 0,
    scenes              TEXT DEFAULT '[]',       -- JSON array of dict
    generation_metadata TEXT DEFAULT '{}',       -- JSON object (含 context_snapshot + creative_brief)
    score_card          TEXT DEFAULT '{}',       -- JSON object (ChapterScoreCard)
    creative_brief_id   TEXT REFERENCES creative_briefs(brief_id) ON DELETE SET NULL,
    parent_version_id   TEXT REFERENCES chapter_versions(version_id) ON DELETE SET NULL,
    created_at          TEXT DEFAULT (datetime('now')),

    UNIQUE(project_id, chapter_number, version_number)
);

CREATE INDEX IF NOT EXISTS idx_versions_project_chapter ON chapter_versions(project_id, chapter_number);
CREATE INDEX IF NOT EXISTS idx_versions_parent ON chapter_versions(parent_version_id);

-- ============================================================
-- 5.5 context_snapshots — 裁剪后上下文快照（Prompt 可回放）
-- ============================================================
CREATE TABLE IF NOT EXISTS context_snapshots (
    snapshot_id                   TEXT PRIMARY KEY,
    project_id                    TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    chapter_number                INTEGER NOT NULL,
    chapter_goal_id               TEXT,
    creative_brief_id             TEXT REFERENCES creative_briefs(brief_id) ON DELETE SET NULL,
    budget_used                   REAL,
    context_emergency             INTEGER DEFAULT 0,
    context_emergency_level       INTEGER DEFAULT 0,
    budget_used_before_emergency  REAL,
    payload                       TEXT DEFAULT '{}',
    created_at                    TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_context_snapshots_project_chapter
ON context_snapshots(project_id, chapter_number);

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
    lifecycle_status TEXT DEFAULT 'active' CHECK(lifecycle_status IN ('active', 'dormant', 'archived')),
    created_at      TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_states_character ON character_states(character_id);
CREATE INDEX IF NOT EXISTS idx_states_version ON character_states(source_version_id);
CREATE INDEX IF NOT EXISTS idx_states_lifecycle ON character_states(lifecycle_status);

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
    lifecycle_status        TEXT DEFAULT 'active' CHECK(lifecycle_status IN ('active', 'dormant', 'archived')),
    source_version_id       TEXT REFERENCES chapter_versions(version_id) ON DELETE SET NULL,  -- ⭐
    created_at              TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_foreshadowings_project ON foreshadowings(project_id);
CREATE INDEX IF NOT EXISTS idx_foreshadowings_status ON foreshadowings(project_id, status);
CREATE INDEX IF NOT EXISTS idx_foreshadowings_lifecycle ON foreshadowings(project_id, lifecycle_status);

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
    lifecycle_status TEXT DEFAULT 'active' CHECK(lifecycle_status IN ('active', 'dormant', 'archived')),
    created_at      TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_settings_project ON setting_snapshots(project_id);
CREATE INDEX IF NOT EXISTS idx_settings_key ON setting_snapshots(project_id, setting_key);
CREATE INDEX IF NOT EXISTS idx_settings_lifecycle ON setting_snapshots(project_id, lifecycle_status);

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
-- 14. project_runs — 项目级多章运行状态
-- ============================================================
CREATE TABLE IF NOT EXISTS project_runs (
    run_id              TEXT PRIMARY KEY,
    project_id          TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    chapter_range_start INTEGER NOT NULL,
    chapter_range_end   INTEGER NOT NULL,
    current_chapter     INTEGER DEFAULT 0,
    completed_chapters  TEXT DEFAULT '[]',
    failed_chapters     TEXT DEFAULT '[]',
    accumulated_summary TEXT DEFAULT '',
    total_cost          REAL DEFAULT 0.0,
    status              TEXT DEFAULT 'running',
    created_at          TEXT DEFAULT (datetime('now')),
    updated_at          TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_project_runs_project ON project_runs(project_id);

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
    impact_score        REAL DEFAULT 0,          -- Phase 4: 章节影响力评分
    created_at          TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_summaries_project ON summaries(project_id, chapter_number);

-- ============================================================
-- 15. arc_summaries — Arc 摘要（分层上下文）
-- ============================================================
CREATE TABLE IF NOT EXISTS arc_summaries (
    arc_id          TEXT PRIMARY KEY,
    project_id      TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    start_chapter   INTEGER NOT NULL,
    end_chapter     INTEGER NOT NULL,
    arc_title       TEXT DEFAULT '',
    arc_summary     TEXT DEFAULT '',
    key_events      TEXT DEFAULT '[]',
    resolved_threads TEXT DEFAULT '[]',
    new_threads     TEXT DEFAULT '[]',
    character_arcs  TEXT DEFAULT '{}',
    created_at      TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_arc_project ON arc_summaries(project_id);

-- ============================================================
-- 16. volume_summaries — 卷摘要（分层上下文）
-- ============================================================
CREATE TABLE IF NOT EXISTS volume_summaries (
    volume_id       TEXT PRIMARY KEY,
    project_id      TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    start_chapter   INTEGER NOT NULL,
    end_chapter     INTEGER NOT NULL,
    volume_title    TEXT DEFAULT '',
    volume_summary  TEXT DEFAULT '',
    major_revelations TEXT DEFAULT '[]',
    world_state     TEXT DEFAULT '',
    created_at      TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_volume_project ON volume_summaries(project_id);

-- ============================================================
-- 17. permanent_scenes — 关键场景永久保留
-- ============================================================
CREATE TABLE IF NOT EXISTS permanent_scenes (
    scene_id        TEXT PRIMARY KEY,
    project_id      TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    chapter_number  INTEGER NOT NULL,
    scene_number    INTEGER NOT NULL DEFAULT 1,
    excerpt         TEXT DEFAULT '',
    impact_tags     TEXT DEFAULT '[]',
    referenced_by   TEXT DEFAULT '[]',
    created_at      TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_permanent_project ON permanent_scenes(project_id);
CREATE INDEX IF NOT EXISTS idx_permanent_chapter ON permanent_scenes(project_id, chapter_number);

-- ============================================================
-- 18. human_marks — 人类辅助记忆标记（Phase 7）
-- ============================================================
CREATE TABLE IF NOT EXISTS human_marks (
    mark_id             TEXT PRIMARY KEY,
    project_id          TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    mark_type           TEXT NOT NULL,           -- setting | character | foreshadowing | item | custom
    target_key          TEXT NOT NULL,
    note                TEXT DEFAULT '',
    priority            INTEGER DEFAULT 5,       -- 1~10
    created_at_chapter  INTEGER,
    resolved_at         TEXT,
    lifecycle_status    TEXT DEFAULT 'active' CHECK(lifecycle_status IN ('active', 'dormant', 'archived')),
    created_at          TEXT DEFAULT (datetime('now')),
    source              TEXT DEFAULT 'human'     -- human | continuity_auditor
);
CREATE INDEX IF NOT EXISTS idx_human_marks_project ON human_marks(project_id);
CREATE INDEX IF NOT EXISTS idx_human_marks_project_priority ON human_marks(project_id, priority);
CREATE INDEX IF NOT EXISTS idx_human_marks_lifecycle ON human_marks(project_id, lifecycle_status);

-- ============================================================
-- 19. chapter_chunks — RAG 向量切片（Phase 8b）
-- ============================================================
CREATE TABLE IF NOT EXISTS chapter_chunks (
    chunk_id        TEXT PRIMARY KEY,
    project_id      TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    chapter_number  INTEGER NOT NULL,
    version_id      TEXT NOT NULL REFERENCES chapter_versions(version_id) ON DELETE CASCADE,
    chunk_index     INTEGER NOT NULL,
    text            TEXT NOT NULL,
    metadata_json   TEXT DEFAULT '{}',
    embedding_blob  BLOB,          -- numpy float32 向量二进制
    lifecycle_status TEXT DEFAULT 'active' CHECK(lifecycle_status IN ('active', 'dormant', 'archived')),
    created_at      TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_chunks_project ON chapter_chunks(project_id, chapter_number);
CREATE INDEX IF NOT EXISTS idx_chunks_lifecycle ON chapter_chunks(project_id, lifecycle_status);

-- ============================================================
-- 23. run_db_metrics — 运行中 DB 维护遥测（V6 Task 156）
-- ============================================================
CREATE TABLE IF NOT EXISTS run_db_metrics (
    sample_id         TEXT PRIMARY KEY,
    run_id            TEXT NOT NULL,
    project_id        TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    chapter_number    INTEGER NOT NULL,
    db_size_bytes     INTEGER NOT NULL,
    wal_size_bytes    INTEGER NOT NULL,
    page_count        INTEGER NOT NULL,
    page_size         INTEGER NOT NULL,
    scan_latency_ms   REAL NOT NULL,
    created_at        TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_run_db_metrics_run ON run_db_metrics(run_id);
CREATE INDEX IF NOT EXISTS idx_run_db_metrics_project_chapter
    ON run_db_metrics(project_id, chapter_number);

-- ============================================================
-- 24. text_cleanliness_metrics — 文本洁净度逐章度量（V7 Task 164）
-- ============================================================
CREATE TABLE IF NOT EXISTS text_cleanliness_metrics (
    project_id                 TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    chapter_number             INTEGER NOT NULL,
    version_id                 TEXT NOT NULL REFERENCES chapter_versions(version_id) ON DELETE CASCADE,
    meta_tag_leak_count        INTEGER NOT NULL DEFAULT 0,
    duplicate_paragraph_count  INTEGER NOT NULL DEFAULT 0,
    timeline_conflict_count    INTEGER NOT NULL DEFAULT 0,
    details_json               TEXT DEFAULT '{}',
    updated_at                 TEXT DEFAULT (datetime('now')),
    PRIMARY KEY(project_id, chapter_number)
);
CREATE INDEX IF NOT EXISTS idx_text_cleanliness_project_chapter
    ON text_cleanliness_metrics(project_id, chapter_number);

-- ============================================================
-- 25. replan_proposals / replan_actions — 重规划提案（V7 Task 166a）
-- ============================================================
CREATE TABLE IF NOT EXISTS replan_proposals (
    proposal_id          TEXT PRIMARY KEY,
    project_id           TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    source_arc_index     INTEGER,
    source_start_chapter INTEGER,
    source_end_chapter   INTEGER,
    status               TEXT NOT NULL DEFAULT 'draft'
                         CHECK(status IN ('draft', 'approved', 'rejected', 'applied')),
    summary              TEXT DEFAULT '',
    evidence_json        TEXT DEFAULT '{}',
    created_at           TEXT DEFAULT (datetime('now')),
    updated_at           TEXT DEFAULT (datetime('now')),
    approved_at          TEXT,
    approved_by          TEXT,
    rejected_at          TEXT,
    rejected_reason      TEXT,
    applied_at           TEXT,
    applied_by           TEXT
);
CREATE INDEX IF NOT EXISTS idx_replan_proposals_project
    ON replan_proposals(project_id, created_at);
CREATE INDEX IF NOT EXISTS idx_replan_proposals_status
    ON replan_proposals(project_id, status);

CREATE TABLE IF NOT EXISTS replan_actions (
    action_id      TEXT PRIMARY KEY,
    proposal_id    TEXT NOT NULL REFERENCES replan_proposals(proposal_id) ON DELETE CASCADE,
    project_id     TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    action_order   INTEGER NOT NULL DEFAULT 0,
    target_type    TEXT NOT NULL,
    target_id      TEXT DEFAULT '',
    field          TEXT NOT NULL,
    old_value_json TEXT DEFAULT 'null',
    new_value_json TEXT DEFAULT 'null',
    reason         TEXT DEFAULT '',
    evidence_json  TEXT DEFAULT '{}',
    created_at     TEXT DEFAULT (datetime('now')),
    UNIQUE(proposal_id, action_order)
);
CREATE INDEX IF NOT EXISTS idx_replan_actions_proposal
    ON replan_actions(proposal_id, action_order);
CREATE INDEX IF NOT EXISTS idx_replan_actions_project
    ON replan_actions(project_id);

CREATE TABLE IF NOT EXISTS planning_constraints (
    constraint_id       TEXT PRIMARY KEY,
    project_id          TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    source_proposal_id  TEXT NOT NULL REFERENCES replan_proposals(proposal_id) ON DELETE CASCADE,
    source_action_id    TEXT NOT NULL REFERENCES replan_actions(action_id) ON DELETE CASCADE,
    target_id           TEXT DEFAULT '',
    constraint_type     TEXT NOT NULL,
    content             TEXT NOT NULL,
    reason              TEXT DEFAULT '',
    status              TEXT NOT NULL DEFAULT 'active'
                        CHECK(status IN ('active', 'archived')),
    created_at          TEXT DEFAULT (datetime('now')),
    UNIQUE(source_action_id)
);
CREATE INDEX IF NOT EXISTS idx_planning_constraints_project
    ON planning_constraints(project_id, status);
CREATE INDEX IF NOT EXISTS idx_planning_constraints_source
    ON planning_constraints(source_proposal_id);

-- ============================================================
-- 26. foreshadowing_schedule_* — 主动伏笔调度（V7 Task 167a）
-- ============================================================
CREATE TABLE IF NOT EXISTS foreshadowing_schedule_plans (
    plan_id            TEXT PRIMARY KEY,
    project_id         TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    target_chapter     INTEGER NOT NULL,
    current_arc_index  INTEGER,
    horizon_chapters   INTEGER NOT NULL DEFAULT 5,
    max_items          INTEGER NOT NULL DEFAULT 3,
    status             TEXT NOT NULL DEFAULT 'draft'
                       CHECK(status IN (
                           'draft', 'active', 'injected',
                           'satisfied', 'missed', 'cancelled'
                       )),
    summary            TEXT DEFAULT '',
    evidence_json      TEXT DEFAULT '{}',
    created_at         TEXT DEFAULT (datetime('now')),
    updated_at         TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_foreshadowing_schedule_plans_project
    ON foreshadowing_schedule_plans(project_id, target_chapter);
CREATE INDEX IF NOT EXISTS idx_foreshadowing_schedule_plans_status
    ON foreshadowing_schedule_plans(project_id, status);

CREATE TABLE IF NOT EXISTS foreshadowing_schedule_items (
    item_id        TEXT PRIMARY KEY,
    plan_id        TEXT NOT NULL REFERENCES foreshadowing_schedule_plans(plan_id)
                   ON DELETE CASCADE,
    project_id     TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    item_order     INTEGER NOT NULL DEFAULT 0,
    target_chapter INTEGER NOT NULL,
    source_type    TEXT NOT NULL,
    source_id      TEXT NOT NULL,
    title          TEXT DEFAULT '',
    description    TEXT DEFAULT '',
    priority_score REAL NOT NULL DEFAULT 0,
    reason_codes   TEXT DEFAULT '[]',
    rationale      TEXT DEFAULT '',
    status         TEXT NOT NULL DEFAULT 'draft'
                   CHECK(status IN (
                       'draft', 'active', 'injected',
                       'satisfied', 'missed', 'cancelled'
                   )),
    evidence_json  TEXT DEFAULT '{}',
    created_at     TEXT DEFAULT (datetime('now')),
    UNIQUE(plan_id, item_order)
);
CREATE INDEX IF NOT EXISTS idx_foreshadowing_schedule_items_plan
    ON foreshadowing_schedule_items(plan_id, item_order);
CREATE INDEX IF NOT EXISTS idx_foreshadowing_schedule_items_project_source
    ON foreshadowing_schedule_items(project_id, source_type, source_id, target_chapter);
CREATE INDEX IF NOT EXISTS idx_foreshadowing_schedule_items_status
    ON foreshadowing_schedule_items(project_id, status);

-- ============================================================
-- 27. adaptive_gate_signal_snapshots — 自适应门禁信号快照（V7 Task 168a）
-- ============================================================
CREATE TABLE IF NOT EXISTS adaptive_gate_signal_snapshots (
    snapshot_id         TEXT PRIMARY KEY,
    project_id          TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    run_id              TEXT NOT NULL DEFAULT '',
    chapter_number      INTEGER NOT NULL,
    source_status_json  TEXT NOT NULL DEFAULT '{}',
    continuity_json     TEXT NOT NULL DEFAULT '{}',
    quality_json        TEXT NOT NULL DEFAULT '{}',
    literary_json       TEXT NOT NULL DEFAULT '{}',
    cleanliness_json    TEXT NOT NULL DEFAULT '{}',
    context_json        TEXT NOT NULL DEFAULT '{}',
    narrative_json      TEXT NOT NULL DEFAULT '{}',
    created_at          TEXT DEFAULT (datetime('now')),
    updated_at          TEXT DEFAULT (datetime('now')),
    UNIQUE(project_id, run_id, chapter_number)
);
CREATE INDEX IF NOT EXISTS idx_adaptive_gate_snapshots_project_range
    ON adaptive_gate_signal_snapshots(project_id, run_id, chapter_number);

-- ============================================================
-- 28. adaptive_halt_decisions — 自适应 halt 判定账本（V7 Task 169a）
-- ============================================================
CREATE TABLE IF NOT EXISTS adaptive_halt_decisions (
    decision_id           TEXT PRIMARY KEY,
    project_id            TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    run_id                TEXT NOT NULL DEFAULT '',
    chapter_start         INTEGER NOT NULL,
    chapter_end           INTEGER NOT NULL,
    evaluated_at_chapter  INTEGER NOT NULL,
    status                TEXT NOT NULL DEFAULT 'continue'
                          CHECK(status IN (
                              'continue', 'observe', 'warn',
                              'halt_candidate', 'halt'
                          )),
    reasons_json          TEXT NOT NULL DEFAULT '[]',
    evidence_json         TEXT NOT NULL DEFAULT '{}',
    policy_id             TEXT NOT NULL DEFAULT 'v7-adaptive-halt-mvp',
    policy_version        TEXT NOT NULL DEFAULT '1.0',
    created_at            TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_adaptive_halt_decisions_project
    ON adaptive_halt_decisions(project_id, run_id, evaluated_at_chapter);
CREATE INDEX IF NOT EXISTS idx_adaptive_halt_decisions_status
    ON adaptive_halt_decisions(project_id, status);
