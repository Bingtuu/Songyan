# Task 204 KG 图 diff spike

> generated_at: `2026-08-01T13:57:02.572713+00:00`
> source_manifest: `archive/v10/artifacts/204-kg-diff-sample-manifest.json`

## 边界

- offline report-only spike
- read-only SQLite access via mode=ro
- does not call LLMs or extract a full KG from prose
- does not write SQLite
- does not modify Writer or CreativeDirector prompts
- does not enter accept/reject gates
- does not change CED, five-gate, segment audit, or T9
- does not build a production KG system

## Summary

- report_only: `True`
- sample_count: `9`
- positive_samples: `6`
- negative_controls: `3`
- db_backed_samples: `9`
- document_truth_only_samples: `0`
- high_confidence_detections: `6`
- unique_gain_count: `6`
- decision: `defer`
- decision_reason: KG diff reproduces useful signals, but several cases require validity interval or alias policy before production use.
- next_route: Task 205 FactTrack validity interval spike

## Gain Matrix

| issue_type | samples | TP | FP | unclear | unique | segment | CED | human/doc | validity | storyline |
|------------|--------:|---:|---:|--------:|-------:|--------:|----:|----------:|---------:|----------:|
| `critical_orphan` | 1 | 1 | 0 | 0 | 1 | 1 | 0 | 1 | 1 | 0 |
| `foreshadowing_unresolved` | 3 | 3 | 0 | 0 | 3 | 1 | 0 | 3 | 3 | 0 |
| `negative_control` | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `setting_tracking_missing_refresh` | 1 | 1 | 0 | 0 | 1 | 1 | 0 | 1 | 1 | 0 |
| `stale_continuity_report` | 1 | 1 | 0 | 0 | 1 | 0 | 0 | 1 | 1 | 0 |

## Sample Results

| sample | genre | chapter | kind | expected | detected | confidence | unique | FP | notes |
|--------|-------|--------:|------|----------|----------|------------|--------|----|-------|
| `204-pos-xh-111-foreshadowing-overdue` | xuanhuan | 111 | positive | `unresolved_candidate` | True | `high` | True | False | expected signal reproduced with clearer graph-local evidence |
| `204-pos-xh-150-stale-continuity-report` | xuanhuan | 150 | positive | `stale_candidate` | True | `high` | True | False | expected signal reproduced with clearer graph-local evidence |
| `204-pos-wx-117-setting-refresh` | wuxia | 117 | positive | `missing_refresh_candidate` | True | `high` | True | False | expected signal reproduced with clearer graph-local evidence |
| `204-pos-wx-155-critical-orphan` | wuxia | 155 | positive | `missing_refresh_candidate` | True | `high` | True | False | expected signal reproduced with clearer graph-local evidence |
| `204-pos-urban-174-foreshadowing-overdue` | urban | 174 | positive | `unresolved_candidate` | True | `high` | True | False | expected signal reproduced with clearer graph-local evidence |
| `204-pos-urban-198-health-streak` | urban | 198 | positive | `unresolved_candidate` | True | `high` | True | False | expected signal reproduced with clearer graph-local evidence |
| `204-neg-xh-200-clean` | xuanhuan | 200 | negative_control | `none` | False | `none` | False | False | negative control produced no high-confidence candidate |
| `204-neg-wx-200-clean` | wuxia | 200 | negative_control | `none` | False | `none` | False | False | negative control produced no high-confidence candidate |
| `204-neg-urban-200-clean` | urban | 200 | negative_control | `none` | False | `none` | False | False | negative control produced no high-confidence candidate |

## Diff Evidence

### 204-pos-xh-111-foreshadowing-overdue
- `unresolved_candidate` / `high`: fs-d160a55a51de4a2bb82440ebc03ec23a-0b5a5f5e (foreshadowings:fs-d160a55a51de4a2bb82440ebc03ec23a-0b5a5f5e) - foreshadowing expected resolve before Ch111 but status is overdue
- `unresolved_candidate` / `high`: fs-d160a55a51de4a2bb82440ebc03ec23a-2448bd9c (foreshadowings:fs-d160a55a51de4a2bb82440ebc03ec23a-2448bd9c) - foreshadowing expected resolve before Ch111 but status is overdue
- `unresolved_candidate` / `high`: fs-d160a55a51de4a2bb82440ebc03ec23a-44315af7 (foreshadowings:fs-d160a55a51de4a2bb82440ebc03ec23a-44315af7) - foreshadowing expected resolve before Ch111 but status is overdue
- `unresolved_candidate` / `high`: fs-d160a55a51de4a2bb82440ebc03ec23a-4dc271e3 (foreshadowings:fs-d160a55a51de4a2bb82440ebc03ec23a-4dc271e3) - foreshadowing expected resolve before Ch111 but status is overdue
- `unresolved_candidate` / `high`: fs-d160a55a51de4a2bb82440ebc03ec23a-5850f886 (foreshadowings:fs-d160a55a51de4a2bb82440ebc03ec23a-5850f886) - foreshadowing expected resolve before Ch111 but status is overdue
- `unresolved_candidate` / `high`: fs-d160a55a51de4a2bb82440ebc03ec23a-652f49a1 (foreshadowings:fs-d160a55a51de4a2bb82440ebc03ec23a-652f49a1) - foreshadowing expected resolve before Ch111 but status is overdue
- `unresolved_candidate` / `high`: fs-d160a55a51de4a2bb82440ebc03ec23a-96471472 (foreshadowings:fs-d160a55a51de4a2bb82440ebc03ec23a-96471472) - foreshadowing expected resolve before Ch111 but status is overdue
- `unresolved_candidate` / `high`: fs-d160a55a51de4a2bb82440ebc03ec23a-c472f027 (foreshadowings:fs-d160a55a51de4a2bb82440ebc03ec23a-c472f027) - foreshadowing expected resolve before Ch111 but status is overdue

### 204-pos-xh-150-stale-continuity-report
- `stale_candidate` / `high`: continuity@Ch150 (continuity_reports:cont_fd2f0aa2) - multiple same-chapter continuity reports can make stale consumers pick the wrong report
- `added` / `low`: Ch150 accepted (chapter_heads:d160a55a51de4a2bb82440ebc03ec23a:150) - chapter_version node changed in after snapshot
- `added` / `low`: continuity@Ch150 (continuity_reports:cont_9cbf0a62) - continuity_report node changed in after snapshot
- `added` / `low`: continuity@Ch150 (continuity_reports:cont_fad57c16) - continuity_report node changed in after snapshot
- `added` / `low`: continuity@Ch150 (continuity_reports:cont_fd2f0aa2) - continuity_report node changed in after snapshot
- `added` / `low`: 玉简碎片中王铁柱跪在血色祭坛前献祭铜印黑血的画面触发后即被禁制切断，只允许看一次，暗示该记忆片段是母 (human_marks:cont-fs-fs-d160a55a51de4a2bb82440ebc03ec23a-09df5487) - human_mark node changed in after snapshot
- `added` / `low`: 母亲遗言‘渊眼之下还镇着……’被外力强行抹去最后几个字，手法极为精细，暗示有人在母亲死后动过玉简，且 (human_marks:cont-fs-fs-d160a55a51de4a2bb82440ebc03ec23a-1d544035) - human_mark node changed in after snapshot
- `added` / `low`: 母亲在忘川潭底留下的九幽镇狱诀第二层完整图谱石碑，陆沉需要拿到才能真正入门 (human_marks:cont-fs-fs-d160a55a51de4a2bb82440ebc03ec23a-86aa6a0d) - human_mark node changed in after snapshot

### 204-pos-wx-117-setting-refresh
- `missing_refresh_candidate` / `high`: broken_blade_sect_martial_arts.blood_abyss.reverse_practice (setting_tracking:track-273a8408be8e4caf8cbc1e91954da600-b622d5ab) - active critical setting last mentioned at Ch113; next audit Ch120 exceeds threshold 3
- `added` / `low`: Ch117 accepted (chapter_heads:273a8408be8e4caf8cbc1e91954da600:117) - chapter_version node changed in after snapshot
- `added` / `low`: continuity@Ch117 (continuity_reports:cont_a5fa5f32) - continuity_report node changed in after snapshot
- `added` / `low`: fs-273a8408be8e4caf8cbc1e91954da600-484fd10f (foreshadowings:fs-273a8408be8e4caf8cbc1e91954da600-484fd10f) - foreshadowing node changed in after snapshot
- `added` / `low`: fs-273a8408be8e4caf8cbc1e91954da600-4a6290f8 (foreshadowings:fs-273a8408be8e4caf8cbc1e91954da600-4a6290f8) - foreshadowing node changed in after snapshot
- `added` / `low`: fs-273a8408be8e4caf8cbc1e91954da600-75faf0b5 (foreshadowings:fs-273a8408be8e4caf8cbc1e91954da600-75faf0b5) - foreshadowing node changed in after snapshot
- `added` / `low`: 沈默将血信与追风堂令牌一起塞入刀鞘夹层，暗示刀鞘夹层可能成为后续关键证据的藏匿处 (human_marks:cont-fs-fs-273a8408be8e4caf8cbc1e91954da600-32be7e3a) - human_mark node changed in after snapshot
- `added` / `low`: 铁面判官声称盟主从沈默师父尸体上拿到断刀门残谱但练不出真正血色刀气，暗示盟主可能另有图谋或功法存在关 (human_marks:cont-fs-fs-273a8408be8e4caf8cbc1e91954da600-49d766ff) - human_mark node changed in after snapshot

### 204-pos-wx-155-critical-orphan
- `missing_refresh_candidate` / `high`: broken_blade_sect_location_cave_altar.blood_lock.tie_bloodline (setting_tracking:track-273a8408be8e4caf8cbc1e91954da600-5b381892) - active critical setting last mentioned at Ch152; next audit Ch156 exceeds threshold 3
- `added` / `low`: Ch155 accepted (chapter_heads:273a8408be8e4caf8cbc1e91954da600:155) - chapter_version node changed in after snapshot
- `added` / `low`: fs-273a8408be8e4caf8cbc1e91954da600-3f1ae200 (foreshadowings:fs-273a8408be8e4caf8cbc1e91954da600-3f1ae200) - foreshadowing node changed in after snapshot
- `added` / `low`: fs-273a8408be8e4caf8cbc1e91954da600-89a35fa5 (foreshadowings:fs-273a8408be8e4caf8cbc1e91954da600-89a35fa5) - foreshadowing node changed in after snapshot
- `added` / `low`: fs-273a8408be8e4caf8cbc1e91954da600-a6d0b97e (foreshadowings:fs-273a8408be8e4caf8cbc1e91954da600-a6d0b97e) - foreshadowing node changed in after snapshot
- `added` / `low`: broken_blade_sect_weapon.duan_nian_blade.blood_text_manifestation (setting_tracking:track-273a8408be8e4caf8cbc1e91954da600-1075d1bc) - setting node changed in after snapshot
- `added` / `low`: broken_blade_sect_weapon_duan_nian_blade.blood_pattern_host_invasion.hand (setting_tracking:track-273a8408be8e4caf8cbc1e91954da600-128148c4) - setting node changed in after snapshot
- `added` / `low`: broken_blade_sect_martial_arts.blood_sacrifice.complete_manual (setting_tracking:track-273a8408be8e4caf8cbc1e91954da600-2a138162) - setting node changed in after snapshot

### 204-pos-urban-174-foreshadowing-overdue
- `unresolved_candidate` / `high`: fs-81e345042b124ee2a73094b82e4be555-04318c3f (foreshadowings:fs-81e345042b124ee2a73094b82e4be555-04318c3f) - foreshadowing expected resolve before Ch174 but status is overdue
- `unresolved_candidate` / `high`: fs-81e345042b124ee2a73094b82e4be555-06b6ab33 (foreshadowings:fs-81e345042b124ee2a73094b82e4be555-06b6ab33) - foreshadowing expected resolve before Ch174 but status is overdue
- `unresolved_candidate` / `high`: fs-81e345042b124ee2a73094b82e4be555-07f28d27 (foreshadowings:fs-81e345042b124ee2a73094b82e4be555-07f28d27) - foreshadowing expected resolve before Ch174 but status is overdue
- `unresolved_candidate` / `high`: fs-81e345042b124ee2a73094b82e4be555-0853c834 (foreshadowings:fs-81e345042b124ee2a73094b82e4be555-0853c834) - foreshadowing expected resolve before Ch174 but status is overdue
- `unresolved_candidate` / `high`: fs-81e345042b124ee2a73094b82e4be555-0d93f0fa (foreshadowings:fs-81e345042b124ee2a73094b82e4be555-0d93f0fa) - foreshadowing expected resolve before Ch174 but status is overdue
- `unresolved_candidate` / `high`: fs-81e345042b124ee2a73094b82e4be555-131f5ce9 (foreshadowings:fs-81e345042b124ee2a73094b82e4be555-131f5ce9) - foreshadowing expected resolve before Ch174 but status is overdue
- `unresolved_candidate` / `high`: fs-81e345042b124ee2a73094b82e4be555-19e28032 (foreshadowings:fs-81e345042b124ee2a73094b82e4be555-19e28032) - foreshadowing expected resolve before Ch174 but status is overdue
- `unresolved_candidate` / `high`: fs-81e345042b124ee2a73094b82e4be555-1b0bab01 (foreshadowings:fs-81e345042b124ee2a73094b82e4be555-1b0bab01) - foreshadowing expected resolve before Ch174 but status is overdue

### 204-pos-urban-198-health-streak
- `unresolved_candidate` / `high`: fs-81e345042b124ee2a73094b82e4be555-04318c3f (foreshadowings:fs-81e345042b124ee2a73094b82e4be555-04318c3f) - foreshadowing expected resolve before Ch198 but status is overdue
- `unresolved_candidate` / `high`: fs-81e345042b124ee2a73094b82e4be555-06b6ab33 (foreshadowings:fs-81e345042b124ee2a73094b82e4be555-06b6ab33) - foreshadowing expected resolve before Ch198 but status is overdue
- `unresolved_candidate` / `high`: fs-81e345042b124ee2a73094b82e4be555-07f28d27 (foreshadowings:fs-81e345042b124ee2a73094b82e4be555-07f28d27) - foreshadowing expected resolve before Ch198 but status is overdue
- `unresolved_candidate` / `high`: fs-81e345042b124ee2a73094b82e4be555-0853c834 (foreshadowings:fs-81e345042b124ee2a73094b82e4be555-0853c834) - foreshadowing expected resolve before Ch198 but status is overdue
- `unresolved_candidate` / `high`: fs-81e345042b124ee2a73094b82e4be555-0d93f0fa (foreshadowings:fs-81e345042b124ee2a73094b82e4be555-0d93f0fa) - foreshadowing expected resolve before Ch198 but status is overdue
- `unresolved_candidate` / `high`: fs-81e345042b124ee2a73094b82e4be555-131f5ce9 (foreshadowings:fs-81e345042b124ee2a73094b82e4be555-131f5ce9) - foreshadowing expected resolve before Ch198 but status is overdue
- `unresolved_candidate` / `high`: fs-81e345042b124ee2a73094b82e4be555-169dc311 (foreshadowings:fs-81e345042b124ee2a73094b82e4be555-169dc311) - foreshadowing expected resolve before Ch198 but status is overdue
- `unresolved_candidate` / `high`: fs-81e345042b124ee2a73094b82e4be555-19e28032 (foreshadowings:fs-81e345042b124ee2a73094b82e4be555-19e28032) - foreshadowing expected resolve before Ch198 but status is overdue

### 204-neg-xh-200-clean
- `added` / `low`: Ch200 accepted (chapter_heads:d160a55a51de4a2bb82440ebc03ec23a:200) - chapter_version node changed in after snapshot
- `added` / `low`: continuity@Ch200 (continuity_reports:cont_b75b3a02) - continuity_report node changed in after snapshot
- `added` / `low`: fs-d160a55a51de4a2bb82440ebc03ec23a-8f8f6642 (foreshadowings:fs-d160a55a51de4a2bb82440ebc03ec23a-8f8f6642) - foreshadowing node changed in after snapshot
- `added` / `low`: 母亲体内的碎片封印太深，必须先用三道封印钥匙斩断母亲的血脉联系才能安全取出，而钥匙被父亲锁在祭坛的体 (human_marks:cont-fs-fs-d160a55a51de4a2bb82440ebc03ec23a-05d9ea23) - human_mark node changed in after snapshot
- `added` / `low`: 守门者意志警告陆沉‘三天内不入融灵，血引引爆，一切全碎’。三天倒计时成为核心悬念，陆沉必须在时间耗尽 (human_marks:cont-fs-fs-d160a55a51de4a2bb82440ebc03ec23a-35b70634) - human_mark node changed in after snapshot
- `added` / `low`: 血灵宗会在六个时辰内来收尸，陆沉的行踪将再次暴露，后续会有追兵 (human_marks:cont-fs-fs-d160a55a51de4a2bb82440ebc03ec23a-5610b52f) - human_mark node changed in after snapshot
- `added` / `low`: 陆沉选择了‘第三个选择’——顺着黑色结晶的脉络强行沟通裂缝核心（渊眼所在位置）而非退入裂缝更深层或借 (human_marks:cont-fs-fs-d160a55a51de4a2bb82440ebc03ec23a-7c53f049) - human_mark node changed in after snapshot
- `added` / `low`: 黑影分头追踪：一股追踪陆沉已在洞穴中被消灭，另一股原路返回，可能会向渊水或其他猎渊者传递消息/带回骨 (human_marks:cont-fs-fs-d160a55a51de4a2bb82440ebc03ec23a-8cdde9d9) - human_mark node changed in after snapshot

### 204-neg-wx-200-clean
- `added` / `low`: Ch200 accepted (chapter_heads:273a8408be8e4caf8cbc1e91954da600:200) - chapter_version node changed in after snapshot
- `added` / `low`: continuity@Ch200 (continuity_reports:cont_b2bc955f) - continuity_report node changed in after snapshot
- `added` / `low`: fs-273a8408be8e4caf8cbc1e91954da600-5872ca54 (foreshadowings:fs-273a8408be8e4caf8cbc1e91954da600-5872ca54) - foreshadowing node changed in after snapshot
- `added` / `low`: fs-273a8408be8e4caf8cbc1e91954da600-8622cfed (foreshadowings:fs-273a8408be8e4caf8cbc1e91954da600-8622cfed) - foreshadowing node changed in after snapshot
- `added` / `low`: broken_blade_sect_weapon_duan_nian_blade.blood_pattern_host_invasion.hand (setting_tracking:track-273a8408be8e4caf8cbc1e91954da600-128148c4) - setting node changed in after snapshot
- `added` / `low`: character.tie_xin_lan.real_identity_lin_he (setting_tracking:track-273a8408be8e4caf8cbc1e91954da600-148f3770) - setting node changed in after snapshot
- `added` / `low`: broken_blade_sect.relics.seventeenth_leader_skeleton (setting_tracking:track-273a8408be8e4caf8cbc1e91954da600-154b57cf) - setting node changed in after snapshot
- `added` / `low`: broken_blade_sect.seal_art.blood_unlock_only (setting_tracking:track-273a8408be8e4caf8cbc1e91954da600-157f2386) - setting node changed in after snapshot

### 204-neg-urban-200-clean
- `added` / `low`: Ch200 accepted (chapter_heads:81e345042b124ee2a73094b82e4be555:200) - chapter_version node changed in after snapshot
- `added` / `low`: continuity@Ch200 (continuity_reports:cont_777a4697) - continuity_report node changed in after snapshot
- `added` / `low`: fs-81e345042b124ee2a73094b82e4be555-096d9f17 (foreshadowings:fs-81e345042b124ee2a73094b82e4be555-096d9f17) - foreshadowing node changed in after snapshot
- `added` / `low`: fs-81e345042b124ee2a73094b82e4be555-16ed534d (foreshadowings:fs-81e345042b124ee2a73094b82e4be555-16ed534d) - foreshadowing node changed in after snapshot
- `added` / `low`: fs-81e345042b124ee2a73094b82e4be555-8648e6df (foreshadowings:fs-81e345042b124ee2a73094b82e4be555-8648e6df) - foreshadowing node changed in after snapshot
- `added` / `low`: fs-81e345042b124ee2a73094b82e4be555-cf963b97 (foreshadowings:fs-81e345042b124ee2a73094b82e4be555-cf963b97) - foreshadowing node changed in after snapshot
- `added` / `low`: fs-81e345042b124ee2a73094b82e4be555-f8626b3b (foreshadowings:fs-81e345042b124ee2a73094b82e4be555-f8626b3b) - foreshadowing node changed in after snapshot
- `added` / `low`: 影子实例日志中的第二段备注“小心女声”暗示一个女性声音相关的陷阱或威胁，身份待揭示 (human_marks:cont-fs-fs-81e345042b124ee2a73094b82e4be555-3d809e31) - human_mark node changed in after snapshot

## 后续路由

- Task 205: FactTrack validity interval spike，用于验证 stale / unresolved 判断是否需要有效期建模。
- Task 206: Storyline Tree spike，仍只处理主线/支线结构，不在 Task 204 展开。
- Task 204 输出保持 report-only，不进入 hard gate。
