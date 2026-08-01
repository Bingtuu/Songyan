# Task 199 Style Card 离线报告

> generated_at: `2026-08-01T03:12:41.994120+00:00`
> sample_set: `tasks/196-excellence-sample-set.json`
> annotations: `tasks/196-excellence-annotations.json`
> excellence_report: `tasks/197-198-excellence-signals-report.json`

## 边界

- report-only / observe-only
- style card is an observed profile, not a prompt constraint
- does not modify Writer or CreativeDirector prompts
- does not enter accept/reject gates
- does not change CED, five-gate, segment audit, or T9
- does not create character voice anchors; Task 200 owns that scope

## 总览

| scope | chapters | rhythm | dialogue | exposition | tension | anti-patterns |
|-------|----------|--------|----------|------------|---------|---------------|
| all | 60 | short-pulse | short-exchange | mixed-exposition | flatline-risk | 12 |
| genre:scifi | 30 | short-pulse | short-exchange | mixed-exposition | flatline-risk | 10 |
| genre:xuanhuan | 30 | short-pulse | short-exchange | mixed-exposition | steady-escalation | 9 |

## Style Card: all

> 观察到的风格画像；V10 内不得默认注入 Writer / CreativeDirector prompt。

### Narrative Voice

- dominant_person: `third`
- pov_depth: `shallow`
- tone: `restrained-observational`
- evidence:
  - Ch1 `“我也觉得不可能，呃，但校准算法跑了三遍，结果一致。”`
  - Ch17 `“你不明白你在做什么。”指挥官的声音平稳，但林渊听出了其中的裂隙——那个停顿，那个本该是陈述句却微微上扬的尾音。`
  - Ch21 `他拼命抓住那段数据流，像溺水的人抓住浮木。意识被拖进记忆深处，时间在神经回路上倒流——回到七年前，回到那个他永远不想再面对的夜晚。`

### Sentence Rhythm

- avg_sentence_chars: `20.4`
- avg_paragraph_chars: `39.57`
- dialogue_ratio: `0.257`
- rhythm_label: `short-pulse`

### Imagery Lexicon

- top_terms: 方舟, 协议, 碎片, 神经, 像是, 意识, 共鸣, 开始, 手指, 表面
- genre_terms: 方舟, 共鸣, 协议, 坐标, 核心, 灵渊, 血脉, 令牌, 守门, 拳
- overused_terms: 陈曦, 协议, 意识, 神经, 老人, 渊老, 灵渊老, 渊老人, 观察, 察者
- evidence:
  - Ch1 `那是共鸣。`
  - Ch17 `那张脸林渊见过无数次——在方舟的每个关键节点，在每次危机会议的主席位上，在那些被记录进方舟日志的全息影像中。但现在，那双眼睛里有什么东西不一样了。不是敌意，是某种更复杂的东西，像是被困在玻璃罩里的人，透过透明的壁垒注视着外面的世界。`
  - Ch21 `共鸣过载像一把钝刀，正在一寸寸剜开他的神经回路。`

### Exposition Style

- exposition_density: `0.04`
- setting_patch_hits: `2`
- style_label: `mixed-exposition`
- risks: setting_patch_segment

### Tension Pattern

- average_tension: `0.189`
- peak_tension: `3.387`
- tension_stdev: `0.274`
- pattern: `flatline-risk`
- dominant_scene_functions: dialogue, combat, revelation, investigation

### Dialogue Style

- dialogue_ratio: `0.257`
- dialogue_line_count: `2340`
- avg_dialogue_sentence_chars: `16.07`
- style_label: `short-exchange`
- sample_lines:
  - `林工，B区深空探测阵列有点异常。`
  - `说具体。`
  - `就是那个……呃，冥王星轨道外侧二十三号节点的数据流，零点三秒内出现了连续十七次相位抖动。`
  - `不可能。`
  - `我也觉得不可能，呃，但校准算法跑了三遍，结果一致。`

### Anti Patterns

| signal | count | severity | examples |
|--------|------:|----------|----------|
| `template_rhetoric_density` | 53 | medium | scifi Ch1: 不是<br>scifi Ch17: 像是<br>scifi Ch21: 不是 |
| `beat_rhythm_repetition` | 40 | medium | scifi Ch1: D-D-D-D<br>scifi Ch17: D-D-D-D<br>scifi Ch23: R-I-R-R |
| `not_but_template` | 28 | medium | scifi Ch21: 不是钥匙本身，而是<br>scifi Ch50: 不是来自设备，而是<br>scifi Ch53: 不是文字，不是图像，而是 |
| `scene_function_homogeneity` | 26 | high | scifi Ch32: scifi segment 2<br>scifi Ch47: scifi segment 2<br>scifi Ch50: scifi segment 2 |
| `tension_flatline` | 21 | high | scifi Ch1: avg=0.12, peak=0.79, stdev=0.17<br>scifi Ch32: avg=0.16, peak=1.24, stdev=0.22<br>scifi Ch47: avg=0.17, peak=1.16, stdev=0.22 |
| `chapter_self_reference` | 13 | high | scifi Ch80: 会加深共鸣耦合。” “对。” 他想起第74章——不，他想起在方舟核心层的牢笼里，陈曦的半机械<br>scifi Ch84: 舟意志的反噬波形在第四秒到达。 林渊在第21章看到过这个协议的设计蓝图——观察者休眠舱上方的核<br>scifi Ch84: #0的结构表面扫过，协议骨架的编码模式与第83章中类人文明领袖的波形投影完全一致——它从来都不是 |
| `engineering_residue` | 12 | high | scifi Ch84: （停顿半秒）<br>scifi Ch84: （停顿半秒）<br>scifi Ch84: （停顿半秒） |
| `motif_reuse_density` | 12 | low | scifi Ch47: 观察, 察者, 一个, 观察者, 的声<br>scifi Ch53: 陈曦, 曦的, 陈曦的, 她的, 结构<br>scifi Ch84: 字段, 陈曦, 节点, 波形, 曦的 |
| `verbatim_sentence_repeat` | 5 | high | scifi Ch60: 但他们不知道——角膜后门不是用来观察我的，是用来观察他们的。<br>scifi Ch80: 你以为那是你破解方舟协议的工具。<br>scifi Ch80: 但共鸣频率是方舟用来筛选和操控容器的工具。 |
| `cross_chapter_verbatim_repeat` | 2 | medium | xuanhuan Ch50: 雾兽的口器突然张开，喷出一团浓稠的白雾。<br>xuanhuan Ch98: 雾兽的口器突然张开，喷出一团浓稠的白雾。 |

## Style Card: genre:scifi

> 观察到的风格画像；V10 内不得默认注入 Writer / CreativeDirector prompt。

### Narrative Voice

- dominant_person: `third`
- pov_depth: `shallow`
- tone: `dialogue-driven`
- evidence:
  - Ch1 `“我也觉得不可能，呃，但校准算法跑了三遍，结果一致。”`
  - Ch17 `“你不明白你在做什么。”指挥官的声音平稳，但林渊听出了其中的裂隙——那个停顿，那个本该是陈述句却微微上扬的尾音。`
  - Ch21 `他拼命抓住那段数据流，像溺水的人抓住浮木。意识被拖进记忆深处，时间在神经回路上倒流——回到七年前，回到那个他永远不想再面对的夜晚。`

### Sentence Rhythm

- avg_sentence_chars: `20.69`
- avg_paragraph_chars: `42.26`
- dialogue_ratio: `0.296`
- rhythm_label: `short-pulse`

### Imagery Lexicon

- top_terms: 方舟, 协议, 神经, 意识, 共鸣, 建造, 造者, 核心, 控制, 建造者
- genre_terms: 方舟, 共鸣, 协议, 坐标, 核心, 拳, 刀
- overused_terms: 陈曦, 协议, 意识, 神经, 观察, 察者, 观察者, 结构, 字段, 节点
- evidence:
  - Ch1 `“你的神经信号在共振，”他说，“观测站的生物监测系统在十五分钟前发出了警报。你的脑电波出现了异常波动，频率和——”`
  - Ch17 `那张脸林渊见过无数次——在方舟的每个关键节点，在每次危机会议的主席位上，在那些被记录进方舟日志的全息影像中。但现在，那双眼睛里有什么东西不一样了。不是敌意，是某种更复杂的东西，像是被困在玻璃罩里的人，透过透明的壁垒注视着外面的世界。`
  - Ch21 `共鸣过载像一把钝刀，正在一寸寸剜开他的神经回路。`

### Exposition Style

- exposition_density: `0.075`
- setting_patch_hits: `0`
- style_label: `mixed-exposition`
- risks: -

### Tension Pattern

- average_tension: `0.17`
- peak_tension: `2.314`
- tension_stdev: `0.241`
- pattern: `flatline-risk`
- dominant_scene_functions: dialogue, revelation, investigation

### Dialogue Style

- dialogue_ratio: `0.296`
- dialogue_line_count: `1367`
- avg_dialogue_sentence_chars: `16.93`
- style_label: `short-exchange`
- sample_lines:
  - `林工，B区深空探测阵列有点异常。`
  - `说具体。`
  - `就是那个……呃，冥王星轨道外侧二十三号节点的数据流，零点三秒内出现了连续十七次相位抖动。`
  - `不可能。`
  - `我也觉得不可能，呃，但校准算法跑了三遍，结果一致。`

### Anti Patterns

| signal | count | severity | examples |
|--------|------:|----------|----------|
| `template_rhetoric_density` | 30 | medium | scifi Ch1: 不是<br>scifi Ch17: 像是<br>scifi Ch21: 不是 |
| `beat_rhythm_repetition` | 17 | medium | scifi Ch1: D-D-D-D<br>scifi Ch17: D-D-D-D<br>scifi Ch23: R-I-R-R |
| `scene_function_homogeneity` | 16 | high | scifi Ch32: scifi segment 2<br>scifi Ch47: scifi segment 2<br>scifi Ch50: scifi segment 2 |
| `tension_flatline` | 15 | high | scifi Ch1: avg=0.12, peak=0.79, stdev=0.17<br>scifi Ch32: avg=0.16, peak=1.24, stdev=0.22<br>scifi Ch47: avg=0.17, peak=1.16, stdev=0.22 |
| `chapter_self_reference` | 13 | high | scifi Ch80: 会加深共鸣耦合。” “对。” 他想起第74章——不，他想起在方舟核心层的牢笼里，陈曦的半机械<br>scifi Ch84: 舟意志的反噬波形在第四秒到达。 林渊在第21章看到过这个协议的设计蓝图——观察者休眠舱上方的核<br>scifi Ch84: #0的结构表面扫过，协议骨架的编码模式与第83章中类人文明领袖的波形投影完全一致——它从来都不是 |
| `not_but_template` | 11 | medium | scifi Ch21: 不是钥匙本身，而是<br>scifi Ch50: 不是来自设备，而是<br>scifi Ch53: 不是文字，不是图像，而是 |
| `motif_reuse_density` | 9 | low | scifi Ch47: 观察, 察者, 一个, 观察者, 的声<br>scifi Ch53: 陈曦, 曦的, 陈曦的, 她的, 结构<br>scifi Ch84: 字段, 陈曦, 节点, 波形, 曦的 |
| `engineering_residue` | 8 | high | scifi Ch84: （停顿半秒）<br>scifi Ch84: （停顿半秒）<br>scifi Ch84: （停顿半秒） |
| `verbatim_sentence_repeat` | 5 | high | scifi Ch60: 但他们不知道——角膜后门不是用来观察我的，是用来观察他们的。<br>scifi Ch80: 你以为那是你破解方舟协议的工具。<br>scifi Ch80: 但共鸣频率是方舟用来筛选和操控容器的工具。 |
| `legacy_ai_tell` | 2 | low | scifi Ch118: 突然意识到——我已经想<br>scifi Ch118: 一瞬间扩散到 |

## Style Card: genre:xuanhuan

> 观察到的风格画像；V10 内不得默认注入 Writer / CreativeDirector prompt。

### Narrative Voice

- dominant_person: `third`
- pov_depth: `shallow`
- tone: `high-pressure`
- evidence:
  - Ch1 `他想说的是，这世上能做的事太少。灵气枯竭，修士们像秋天的蝗虫一样往大城里挤，小地方的灵脉早就干成了筛子。青岩镇这破地方，连最次的灵火都引不起来，铁匠铺全靠地火残温撑着。凡人想修炼？拿什么修？灵丹买不起，灵脉被大族占着，功法都在宗门手里攥着…`
  - Ch17 `陆沉脚下一空，整个人仿佛坠入无底深渊。阴源珠炼化后那股牵引力根本没有给他反应的时间，视线被浓稠的灰白雾气填满，耳边只剩下自己越来越急促的心跳声。`
  - Ch21 `小队长拔出腰间弯刀，刀身上血气缭绕，“闻到你的味儿了，新鲜得很，不是我们的人。怎么，想捡便宜？”`

### Sentence Rhythm

- avg_sentence_chars: `20.07`
- avg_paragraph_chars: `36.83`
- dialogue_ratio: `0.211`
- rhythm_label: `short-pulse`

### Imagery Lexicon

- top_terms: 像是, 灵渊, 碎片, 母亲, 封印, 符文, 东西, 纹路, 灵力, 金色
- genre_terms: 共鸣, 坐标, 核心, 灵渊, 血脉, 令牌, 守门, 拳, 刀, 剑
- overused_terms: 老人, 渊老, 灵渊老, 渊老人, 灵渊老人, 封印, 符文, 母亲, 金色, 父亲
- evidence:
  - Ch1 `锤头落在铁胚上的一瞬间，陆沉感觉不对。力道是平时的力道，角度也是平时的角度，但锤头触及铁面的那一刻，他手掌传来一阵细微的震颤——像是铁砧内部有什么东西在回应这一锤。`
  - Ch17 `九座青铜祭坛错落在灰雾空间里，每一座都有三丈高，坛身爬满暗绿色的铜锈，上面刻着密密麻麻的上古符文。陆沉扫过那些符文——有些和灵渊封印中的纹路相似，有些则完全陌生，笔画圆润扭曲，像是某种活物留下的痕迹。`
  - Ch21 `灵力丝与血丝的末端接触，在接触的瞬间注入阴煞之气。红芒黯淡了一息，随即恢复，但那一息足够让陆沉判断出阵法的核心节点位置——丝线蔓延的速度在接触阴煞之气时出现了一处明显的迟滞。`

### Exposition Style

- exposition_density: `0.001`
- setting_patch_hits: `2`
- style_label: `mixed-exposition`
- risks: setting_patch_segment

### Tension Pattern

- average_tension: `0.207`
- peak_tension: `3.387`
- tension_stdev: `0.307`
- pattern: `steady-escalation`
- dominant_scene_functions: combat, dialogue

### Dialogue Style

- dialogue_ratio: `0.211`
- dialogue_line_count: `973`
- avg_dialogue_sentence_chars: `14.86`
- style_label: `short-exchange`
- sample_lines:
  - `愣着干啥？`
  - `又废了一块？你小子今天手抖得厉害，昨晚没睡好？`
  - `喂，问你话呢。`
  - `嗯。`
  - `嗯个屁。`

### Anti Patterns

| signal | count | severity | examples |
|--------|------:|----------|----------|
| `beat_rhythm_repetition` | 23 | medium | xuanhuan Ch17: D-C-D-D<br>xuanhuan Ch21: C-C-C-C<br>xuanhuan Ch23: D-C-C-C |
| `template_rhetoric_density` | 23 | medium | xuanhuan Ch1: 像是<br>xuanhuan Ch17: 像是<br>xuanhuan Ch23: 像是 |
| `not_but_template` | 17 | medium | xuanhuan Ch23: 不是恐惧，而是<br>xuanhuan Ch32: 不是上方坠落的溪流，而是<br>xuanhuan Ch39: 不是强行使灵力与令牌共振，而是 |
| `scene_function_homogeneity` | 10 | high | xuanhuan Ch32: xuanhuan segment 2<br>xuanhuan Ch39: xuanhuan segment 2<br>xuanhuan Ch50: xuanhuan segment 2 |
| `tension_flatline` | 6 | high | xuanhuan Ch61: avg=0.13, peak=0.84, stdev=0.21<br>xuanhuan Ch71: avg=0.14, peak=1.16, stdev=0.21<br>xuanhuan Ch92: avg=0.14, peak=1.28, stdev=0.24 |
| `engineering_residue` | 4 | high | xuanhuan Ch50: ## 二<br>xuanhuan Ch50: ## 三<br>xuanhuan Ch50: ## 四 |
| `motif_reuse_density` | 3 | low | xuanhuan Ch60: 老人, 渊老, 灵渊老, 渊老人, 灵渊老人<br>xuanhuan Ch61: 封印, 老人, 渊老, 灵渊老, 渊老人<br>xuanhuan Ch199: 符文, 母亲, 亲的, 金色, 父亲 |
| `cross_chapter_verbatim_repeat` | 2 | medium | xuanhuan Ch50: 雾兽的口器突然张开，喷出一团浓稠的白雾。<br>xuanhuan Ch98: 雾兽的口器突然张开，喷出一团浓稠的白雾。 |
| `setting_patch_segment` | 2 | medium | xuanhuan Ch118: 那些记忆碎片终于拼成更清楚的轮廓：灵渊核心令牌本该一分为二，一半被母亲在他出生夜嵌入丹…<br>xuanhuan Ch134: 父亲留下的金色徽记、灵渊令牌这把核心钥匙，以及灵渊老人气息与陆沉血气之间的牵连，都被母… |

## Sanity Check

| scope | strong | strong traits | weak | weak explained | weak unexplained |
|-------|--------|---------------|------|----------------|------------------|
| all | 6 | 6 | 15 | 15 | - |
| genre:scifi | 3 | 3 | 8 | 8 | - |
| genre:xuanhuan | 3 | 3 | 7 | 7 | - |

## 局限

- 本报告只覆盖 Task 196 的 xuanhuan + sci-fi 60 章样本。
- style card 是观察画像，不是 Writer / CreativeDirector 约束。
- 角色声纹锚点不在本任务内，归 Task 200。
- prelabel 仅作对照；sanity check 使用 agent-deep-read 标注。
