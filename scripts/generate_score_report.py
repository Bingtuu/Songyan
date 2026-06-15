import sqlite3, json, statistics, sys
sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect('evals/output/task_090a_scifi_webnovel_tightened/test.db')
c = conn.cursor()
pid = c.execute("SELECT project_id FROM projects LIMIT 1").fetchone()[0]

c.execute('''
SELECT cv.chapter_number, cv.version_id, cv.word_count, cv.scenes,
       rr.overall_score, rr.ai_tell_count, rr.fatigue_word_count,
       rr.has_opening_hook, rr.has_ending_hook, rr.dimension_scores,
       rr.issues, rr.rule_audit_result, rr.llm_audit_result,
       (SELECT word_count_target FROM chapter_goals 
        WHERE chapter_number = cv.chapter_number AND project_id = cv.project_id 
        ORDER BY created_at DESC LIMIT 1) as target_wc
FROM chapter_versions cv
JOIN chapter_heads ch ON cv.chapter_number = ch.chapter_number 
    AND cv.version_id = ch.current_version_id
LEFT JOIN review_reports rr ON cv.version_id = rr.chapter_version_id AND rr.audit_type = 'merged'
WHERE cv.project_id = ? AND cv.is_abandoned = 0
ORDER BY cv.chapter_number
''', (pid,))
rows = c.fetchall()

DIMENSIONS = [
    "world_consistency", "character_behavior", "timeline",
    "new_setting_unregistered", "narrative_pacing", "narrative_hook",
    "info_dump", "dialogue_distinctness", "dialogue_subtext",
    "description_sensory", "show_dont_tell", "genre_numerical"
]

results = []
seen_ch = set()
for r in rows:
    ch = r[0]
    if ch in seen_ch:
        continue
    seen_ch.add(ch)
    
    vid, wc, scenes, overall, ai_tell, fatigue, open_hook, end_hook, dim_scores_json, issues_json, rule_json, llm_json, target_wc = r[1:]
    
    dim_scores = json.loads(dim_scores_json) if dim_scores_json else {}
    issues = json.loads(issues_json) if issues_json else []
    rule = json.loads(rule_json) if rule_json else {}
    llm = json.loads(llm_json) if llm_json else {}
    
    critical = sum(1 for i in issues if i.get('severity') == 'critical')
    major = sum(1 for i in issues if i.get('severity') == 'major')
    minor = sum(1 for i in issues if i.get('severity') == 'minor')
    
    scenes_list = json.loads(scenes) if scenes else []
    scene_count = len(scenes_list)
    
    target_wc = target_wc or 3200
    budget = wc / target_wc if target_wc else 0
    word_count_pass = 0.8 <= budget <= 1.2
    
    dim_values = [dim_scores.get(d, 0) for d in DIMENSIONS if d in dim_scores]
    dim_avg = statistics.mean(dim_values) if dim_values else 0
    
    hook_open = 1 if open_hook else 0
    hook_close = 1 if end_hook else 0
    
    health = 0
    if word_count_pass: health += 2
    if hook_open: health += 1.5
    if hook_close: health += 1.5
    if ai_tell is not None and ai_tell < 2: health += 1.5
    if fatigue is not None and fatigue < 3: health += 1.5
    if critical == 0: health += 1
    if major <= 3: health += 1
    dim_bonus = min(dim_avg / 10 * 2, 2) if dim_avg else 0
    health += dim_bonus
    
    results.append({
        'ch': ch, 'wc': wc, 'target': target_wc, 'budget': budget,
        'scenes': scene_count, 'overall': overall or 0,
        'critical': critical, 'major': major, 'minor': minor,
        'ai_tell': ai_tell or 0, 'fatigue': fatigue or 0,
        'hook_open': hook_open, 'hook_close': hook_close,
        'dim_avg': dim_avg, 'health': health,
        'word_pass': word_count_pass,
        'dim_scores': dim_scores,
        'cliche': llm.get('cliche_risk_score', 0) or 0,
        'autonomy': llm.get('character_autonomy_score', 0) or 0,
        'idling': llm.get('conceptual_idling_score', 0) or 0,
        'rhythm': rule.get('paragraph_rhythm_score', 0) or 0,
    })

# Write report
out = open('evals/output/task_090a_scifi_webnovel_tightened/detailed_score_report.md', 'w', encoding='utf-8')
out.write("# Ch1-Ch20 详细评分报告\n\n")
out.write("> 评分标准：MetricsCollector 10项指标 + 综合 health_score\n\n")
out.write("## 评分维度说明\n\n")
out.write("| 维度 | 权重 | 达标标准 |\n")
out.write("|------|------|----------|\n")
out.write("| 字数达标 | 2.0 | budget in [0.8, 1.2] |\n")
out.write("| 首屏钩子 | 1.5 | has_opening_hook=True |\n")
out.write("| 章末钩子 | 1.5 | has_ending_hook=True |\n")
out.write("| AI腔控制 | 1.5 | ai_tell_count < 2 |\n")
out.write("| 疲劳词控制 | 1.5 | fatigue_word_count < 3 |\n")
out.write("| Critical问题 | 1.0 | critical == 0 |\n")
out.write("| Major问题 | 1.0 | major <= 3 |\n")
out.write("| 维度均分 | 2.0 | dim_avg/10 * 2 (max 2) |\n")
out.write("| **health_score 满分** | **13.0** | |\n\n")
out.write("| 状态 | 条件 |\n")
out.write("|------|------|\n")
out.write("| PASS | health >= 6.0 AND 字数达标 |\n")
out.write("| WARN | health >= 5.0 |\n")
out.write("| FAIL | health < 5.0 |\n\n")

out.write("## 逐章评分总表\n\n")
out.write("| Ch | 字数 | 目标 | budget | scenes | overall | crit | maj | min | AI腔 | 疲劳 | 首钩 | 末钩 | 维度均 | health | 字数达标 | 状态 |\n")
out.write("|----|------|------|--------|--------|---------|------|-----|-----|------|------|------|------|--------|--------|----------|------|\n")

fail_chapters = []
pass_count = 0
for r in results:
    if r['health'] >= 6.0 and r['word_pass']:
        status = "PASS"
        pass_count += 1
    elif r['health'] >= 5.0:
        status = "WARN"
    else:
        status = "FAIL"
    if status != "PASS":
        fail_chapters.append((r['ch'], status, r['health']))
    
    out.write(f"| {r['ch']} | {r['wc']} | {r['target']} | {r['budget']:.3f} | {r['scenes']} | {r['overall']:.2f} | {r['critical']} | {r['major']} | {r['minor']} | {r['ai_tell']} | {r['fatigue']} | {r['hook_open']} | {r['hook_close']} | {r['dim_avg']:.2f} | {r['health']:.2f} | {'Y' if r['word_pass'] else 'N'} | {status} |\n")

total = len(results)
warn_count = sum(1 for _,s,_ in fail_chapters if s=='WARN')
fail_count = sum(1 for _,s,_ in fail_chapters if s=='FAIL')
out.write(f"\n**总计**: {total}章 | PASS: {pass_count} | WARN: {warn_count} | FAIL: {fail_count}\n")
out.write(f"**综合达标率** (health>=6 + 字数达标): {pass_count}/{total} = {pass_count/total*100:.1f}%\n\n")

gen_results = [r for r in results if r['ch'] > 1]
gen_pass = sum(1 for r in gen_results if r['health'] >= 6.0 and r['word_pass'])
out.write(f"**生成章节 (Ch2-Ch20) 达标率**: {gen_pass}/{len(gen_results)} = {gen_pass/len(gen_results)*100:.1f}%\n\n")

out.write("## 不符合预期章节清单\n\n")
out.write("| 章节 | 状态 | health | 核心问题 |\n")
out.write("|------|------|--------|----------|\n")
for ch, st, h in fail_chapters:
    r = next(x for x in results if x['ch'] == ch)
    problems = []
    if not r['word_pass']:
        problems.append(f"budget={r['budget']:.2f}")
    if r['critical'] > 0:
        problems.append(f"Critical:{r['critical']}")
    if r['major'] > 5:
        problems.append(f"Major:{r['major']}")
    if r['ai_tell'] >= 2:
        problems.append(f"AI腔:{r['ai_tell']}")
    if r['fatigue'] >= 3:
        problems.append(f"疲劳:{r['fatigue']}")
    if not r['hook_open']:
        problems.append("首钩缺失")
    if not r['hook_close']:
        problems.append("末钩缺失")
    out.write(f"| Ch{ch} | {st} | {h:.2f} | {', '.join(problems) if problems else 'health偏低'} |\n")

out.write("\n## 详细诊断\n\n")
for r in results:
    if r['ch'] in [x[0] for x in fail_chapters]:
        out.write(f"### Ch{r['ch']}: {r['wc']}字 / 目标{r['target']} | health={r['health']:.2f} | overall={r['overall']:.2f}\n\n")
        issues = []
        if not r['word_pass']:
            issues.append(f"字数不达标 (budget={r['budget']:.3f}, 目标区间[0.8,1.2])")
        if r['critical'] > 0:
            issues.append(f"Critical issues: {r['critical']}")
        if r['major'] > 5:
            issues.append(f"Major issues过多: {r['major']}")
        if r['ai_tell'] >= 2:
            issues.append(f"AI腔检测失败: {r['ai_tell']}处")
        if r['fatigue'] >= 3:
            issues.append(f"疲劳词过多: {r['fatigue']}处")
        if not r['hook_open']:
            issues.append("首屏钩子缺失")
        if not r['hook_close']:
            issues.append("章末钩子缺失")
        if r['cliche'] >= 5:
            issues.append(f"套路风险高: {r['cliche']}")
        if r['idling'] >= 5:
            issues.append(f"概念空转: {r['idling']}")
        
        for issue in issues:
            out.write(f"- [x] {issue}\n")
        
        if r['dim_scores']:
            weak_dims = [(k, v) for k, v in r['dim_scores'].items() if v < 7.0]
            if weak_dims:
                out.write(f"- 弱项维度: {', '.join(f'{k}={v:.1f}' for k,v in sorted(weak_dims, key=lambda x: x[1]))}\n")
            strong_dims = [(k, v) for k, v in r['dim_scores'].items() if v >= 8.5]
            if strong_dims:
                out.write(f"- 强项维度: {', '.join(f'{k}={v:.1f}' for k,v in sorted(strong_dims, key=lambda x: -x[1])[:3])}\n")
        out.write("\n")

out.write("## 统计摘要\n\n")
budgets = [r['budget'] for r in gen_results]
out.write(f"- 平均 budget: {statistics.mean(budgets):.3f}\n")
out.write(f"- budget 范围: [{min(budgets):.3f}, {max(budgets):.3f}]\n")
out.write(f"- 平均 health_score: {statistics.mean([r['health'] for r in gen_results]):.2f}\n")
out.write(f"- 平均 overall_score: {statistics.mean([r['overall'] for r in gen_results]):.2f}\n")
dim_avgs = [r['dim_avg'] for r in gen_results if r['dim_avg'] > 0]
if dim_avgs:
    out.write(f"- 平均维度均分: {statistics.mean(dim_avgs):.2f}\n")

dim_all = {}
for r in gen_results:
    for k, v in r['dim_scores'].items():
        dim_all.setdefault(k, []).append(v)
out.write("\n### 各维度平均分\n\n")
out.write("| 维度 | 平均分 |\n")
out.write("|------|--------|\n")
for dim in DIMENSIONS:
    if dim in dim_all:
        avg = statistics.mean(dim_all[dim])
        out.write(f"| {dim} | {avg:.2f} |\n")

out.close()
print("Report saved to: evals/output/task_090a_scifi_webnovel_tightened/detailed_score_report.md")
