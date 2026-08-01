# Task 197/198 优秀度信号包第一批离线报告

> generated_at: `2026-08-01T01:41:56.971979+00:00`
> sample_set: `archive/v10/artifacts/196-excellence-sample-set.json`
> annotations: `archive/v10/artifacts/196-excellence-annotations.json`

## 边界

- report-only / observe-only
- does not modify Writer or CreativeDirector prompts
- does not enter accept/reject gates
- does not change CED, five-gate, segment audit, or T9
- Task 196 prelabel is comparison-only; anchor + spotcheck are calibration truth

## 总览

| Task | 章节命中 | hit 总数 | top signals |
|------|----------|----------|-------------|
| 197 | 54 | 99 | beat_rhythm_repetition=40, scene_function_homogeneity=26, tension_flatline=21, motif_reuse_density=12 |
| 198 | 57 | 117 | template_rhetoric_density=53, not_but_template=28, chapter_self_reference=13, engineering_residue=12, verbatim_sentence_repeat=5 |

## 校准摘要（agent-deep-read 24 章）

| Task | truth rule | evaluated | truth+ | detected+ | TP | FP | FN | precision | recall |
|------|------------|-----------|--------|-----------|----|----|----|-----------|--------|
| 197 | homogeneity<=2 or tension<=2 or overall<=2 | 24 | 10 | 20 | 8 | 12 | 2 | 0.40 | 0.80 |
| 198 | ai_tone<=2 or overall<=2 | 24 | 15 | 23 | 15 | 8 | 0 | 0.65 | 1.00 |

## 高风险命中样例

### Task 197
- **scifi Ch1** `beat_rhythm_repetition` (medium)：beat signature `D-D-D-D` 重复度偏高；chapter beat signature `D-D-D-D`
- **scifi Ch1** `tension_flatline` (high)：段落张力均值、峰值与波动均偏低；paragraph tension `avg=0.12, peak=0.79, stdev=0.17`
- **scifi Ch17** `beat_rhythm_repetition` (medium)：beat signature `D-D-D-D` 重复度偏高；chapter beat signature `D-D-D-D`
- **scifi Ch23** `beat_rhythm_repetition` (medium)：beat signature `R-I-R-R` 重复度偏高；chapter beat signature `R-I-R-R`
- **scifi Ch32** `scene_function_homogeneity` (medium)：弧段 2 内 `dialogue` 场景占比 75%；弧段统计 `scifi segment 2`
- **scifi Ch32** `beat_rhythm_repetition` (medium)：beat signature `D-D-D-D` 重复度偏高；chapter beat signature `D-D-D-D`
- **scifi Ch32** `tension_flatline` (high)：段落张力均值、峰值与波动均偏低；paragraph tension `avg=0.16, peak=1.24, stdev=0.22`
- **scifi Ch47** `scene_function_homogeneity` (medium)：弧段 2 内 `dialogue` 场景占比 75%；弧段统计 `scifi segment 2`
- **scifi Ch47** `beat_rhythm_repetition` (medium)：beat signature `D-D-D-D` 重复度偏高；chapter beat signature `D-D-D-D`
- **scifi Ch47** `tension_flatline` (high)：段落张力均值、峰值与波动均偏低；paragraph tension `avg=0.17, peak=1.16, stdev=0.22`
- **scifi Ch47** `motif_reuse_density` (low)：高频核心词：观察, 察者, 一个, 观察者, 的声；chapter lexical motifs `观察, 察者, 一个, 观察者, 的声`
- **scifi Ch50** `scene_function_homogeneity` (medium)：弧段 2 内 `dialogue` 场景占比 75%；弧段统计 `scifi segment 2`

### Task 198
- **scifi Ch1** `template_rhetoric_density` (low)：`不是` 等模板连接词密度偏高；第17段第1句 `不是`
- **scifi Ch17** `template_rhetoric_density` (medium)：`像是` 等模板连接词密度偏高；第4段第3句 `像是`
- **scifi Ch21** `template_rhetoric_density` (medium)：`不是` 等模板连接词密度偏高；第4段第1句 `不是`
- **scifi Ch21** `not_but_template` (medium)：`不是...而是...` 模板复用过多；第44段第1句 `不是钥匙本身，而是`
- **scifi Ch23** `template_rhetoric_density` (medium)：`不是` 等模板连接词密度偏高；第2段第1句 `不是`
- **scifi Ch32** `template_rhetoric_density` (medium)：`不是` 等模板连接词密度偏高；第3段第1句 `不是`
- **scifi Ch39** `template_rhetoric_density` (medium)：`不是` 等模板连接词密度偏高；第2段第1句 `不是`
- **scifi Ch47** `template_rhetoric_density` (medium)：`不是` 等模板连接词密度偏高；第14段第3句 `不是`
- **scifi Ch50** `template_rhetoric_density` (medium)：`不是` 等模板连接词密度偏高；第2段第1句 `不是`
- **scifi Ch50** `not_but_template` (medium)：`不是...而是...` 模板复用过多；第2段第1句 `不是来自设备，而是`
- **scifi Ch53** `template_rhetoric_density` (medium)：`不是` 等模板连接词密度偏高；第2段第1句 `不是`
- **scifi Ch53** `not_but_template` (medium)：`不是...而是...` 模板复用过多；第2段第1句 `不是文字，不是图像，而是`

## 逐章明细

| genre | chapter | annotation | T197 hits | T198 hits | scene | beat | tension avg/peak |
|-------|---------|------------|-----------|-----------|-------|------|------------------|
| scifi | 1 | anchor: H5/T5/A4/O5 | 2 | 1 | dialogue | `D-D-D-D` | 0.12/0.79 |
| scifi | 17 | spotcheck: H3/T4/A3/O3 | 1 | 1 | dialogue | `D-D-D-D` | 0.19/1.17 |
| scifi | 21 | prelabel: H4/T5/A4/O4 | 0 | 2 | revelation | `D-R-D-R` | 0.24/1.55 |
| scifi | 23 | prelabel: H4/T5/A4/O4 | 1 | 1 | revelation | `R-I-R-R` | 0.24/1.55 |
| scifi | 32 | anchor: H1/T2/A2/O2 | 3 | 1 | dialogue | `D-D-D-D` | 0.16/1.24 |
| scifi | 39 | spotcheck: H2/T3/A2/O2 | 0 | 1 | investigation | `T-R-I-I` | 0.18/1.31 |
| scifi | 47 | prelabel: H4/T5/A4/O4 | 4 | 1 | dialogue | `D-D-D-D` | 0.17/1.16 |
| scifi | 50 | prelabel: H4/T5/A4/O4 | 2 | 2 | dialogue | `D-D-D-D` | 0.19/1.52 |
| scifi | 53 | spotcheck: H3/T4/A2/O3 | 2 | 2 | revelation | `R-R-R-D` | 0.23/1.58 |
| scifi | 60 | prelabel: H4/T5/A4/O4 | 2 | 3 | dialogue | `D-D-R-R` | 0.17/1.16 |
| scifi | 61 | prelabel: H4/T5/A4/O4 | 2 | 1 | dialogue | `D-D-I-R` | 0.13/1.18 |
| scifi | 71 | prelabel: H4/T5/A4/O4 | 3 | 1 | dialogue | `D-D-D-D` | 0.16/1.26 |
| scifi | 80 | spotcheck: H2/T3/A2/O2 | 3 | 4 | dialogue | `D-D-D-D` | 0.12/1.26 |
| scifi | 84 | anchor: H1/T2/A1/O2 | 3 | 12 | dialogue | `R-D-I-I` | 0.13/1.18 |
| scifi | 92 | prelabel: H4/T5/A4/O5 | 2 | 3 | dialogue | `I-D-D-D` | 0.19/1.22 |
| scifi | 98 | prelabel: H4/T5/A4/O4 | 3 | 3 | dialogue | `D-D-D-D` | 0.13/1.16 |
| scifi | 104 | anchor: H4/T5/A4/O4 | 3 | 1 | revelation | `R-R-R-R` | 0.16/0.83 |
| scifi | 105 | spotcheck: H3/T3/A2/O3 | 3 | 1 | revelation | `R-R-R-R` | 0.18/2.31 |
| scifi | 118 | prelabel: H4/T5/A5/O5 | 1 | 3 | dialogue | `D-R-D-D` | 0.20/1.19 |
| scifi | 120 | prelabel: H4/T5/A4/O4 | 1 | 2 | revelation | `R-D-R-D` | 0.20/1.17 |
| scifi | 134 | spotcheck: H3/T4/A2/O3 | 1 | 2 | investigation | `I-R-D-I` | 0.25/1.52 |
| scifi | 135 | prelabel: H4/T5/A4/O5 | 1 | 4 | dialogue | `I-I-D-D` | 0.14/1.54 |
| scifi | 145 | prelabel: H4/T5/A4/O5 | 2 | 1 | dialogue | `D-I-D-R` | 0.13/1.13 |
| scifi | 148 | prelabel: H4/T5/A4/O5 | 2 | 2 | revelation | `R-R-D-I` | 0.09/0.80 |
| scifi | 162 | prelabel: H3/T4/A4/O4 | 2 | 2 | dialogue | `D-D-D-R` | 0.22/1.13 |
| scifi | 164 | prelabel: H4/T5/A4/O4 | 3 | 3 | dialogue | `D-D-D-I` | 0.14/1.18 |
| scifi | 169 | prelabel: H4/T5/A4/O4 | 1 | 2 | dialogue | `D-D-I-I` | 0.28/1.54 |
| scifi | 178 | prelabel: H4/T5/A4/O4 | 1 | 1 | dialogue | `D-D-D-D` | 0.16/1.72 |
| scifi | 194 | anchor: H1/T3/A1/O2 | 2 | 5 | revelation | `R-R-D-I` | 0.13/1.17 |
| scifi | 199 | anchor: H4/T5/A4/O4 | 1 | 1 | dialogue | `R-D-I-I` | 0.09/0.87 |
| xuanhuan | 1 | anchor: H4/T5/A4/O5 | 0 | 1 | dialogue | `D-D-T-T` | 0.20/1.93 |
| xuanhuan | 17 | spotcheck: H3/T3/A2/O3 | 1 | 1 | dialogue | `D-C-D-D` | 0.17/1.18 |
| xuanhuan | 21 | prelabel: H3/T4/A4/O4 | 1 | 0 | combat | `C-C-C-C` | 0.36/1.95 |
| xuanhuan | 23 | prelabel: H4/T5/A4/O4 | 1 | 2 | combat | `D-C-C-C` | 0.18/1.54 |
| xuanhuan | 32 | spotcheck: H3/T4/A3/O3 | 2 | 1 | combat | `C-C-C-C` | 0.21/1.19 |
| xuanhuan | 39 | prelabel: H3/T4/A4/O4 | 1 | 1 | combat | `C-D-T-D` | 0.22/1.51 |
| xuanhuan | 47 | prelabel: H3/T4/A4/O4 | 1 | 0 | dialogue | `D-D-T-D` | 0.21/1.57 |
| xuanhuan | 50 | anchor: H2/T2/A1/O2 | 2 | 5 | combat | `C-C-D-C` | 0.24/1.35 |
| xuanhuan | 53 | spotcheck: H3/T4/A3/O3 | 2 | 0 | dialogue | `D-D-C-D` | 0.16/1.21 |
| xuanhuan | 60 | prelabel: H4/T5/A5/O5 | 3 | 2 | dialogue | `D-D-D-D` | 0.16/1.52 |
| xuanhuan | 61 | prelabel: H4/T5/A4/O4 | 4 | 1 | dialogue | `D-D-D-D` | 0.13/0.84 |
| xuanhuan | 71 | prelabel: H4/T5/A5/O5 | 2 | 2 | combat | `I-C-C-C` | 0.14/1.16 |
| xuanhuan | 80 | spotcheck: H3/T3/A2/O3 | 2 | 2 | combat | `C-C-C-C` | 0.19/1.54 |
| xuanhuan | 84 | prelabel: H3/T5/A4/O4 | 2 | 1 | combat | `C-C-C-D` | 0.23/1.55 |
| xuanhuan | 92 | prelabel: H3/T4/A4/O4 | 3 | 1 | combat | `C-C-C-D` | 0.14/1.28 |
| xuanhuan | 98 | prelabel: H4/T5/A4/O4 | 2 | 1 | combat | `C-C-C-D` | 0.21/1.15 |
| xuanhuan | 104 | anchor: H4/T4/A4/O4 | 0 | 2 | combat | `D-C-C-I` | 0.22/1.22 |
| xuanhuan | 105 | spotcheck: H3/T3/A2/O2 | 0 | 2 | dialogue | `C-D-C-D` | 0.18/2.01 |
| xuanhuan | 118 | anchor: H2/T3/A2/O2 | 1 | 2 | combat | `C-C-D-C` | 0.21/1.87 |
| xuanhuan | 120 | prelabel: H4/T5/A4/O5 | 1 | 2 | dialogue | `D-D-D-D` | 0.23/1.59 |
| xuanhuan | 134 | spotcheck: H3/T3/A2/O2 | 1 | 3 | dialogue | `D-D-D-C` | 0.27/3.39 |
| xuanhuan | 135 | prelabel: H4/T5/A4/O4 | 0 | 1 | combat | `C-C-D-D` | 0.30/2.96 |
| xuanhuan | 145 | prelabel: H3/T4/A4/O4 | 1 | 2 | combat | `D-C-I-C` | 0.12/1.16 |
| xuanhuan | 148 | prelabel: H4/T5/A4/O4 | 2 | 2 | dialogue | `D-D-D-D` | 0.16/1.20 |
| xuanhuan | 162 | prelabel: H4/T5/A4/O4 | 1 | 2 | combat | `D-C-C-C` | 0.37/2.25 |
| xuanhuan | 164 | prelabel: H4/T5/A5/O5 | 1 | 2 | dialogue | `D-C-D-C` | 0.17/1.21 |
| xuanhuan | 169 | anchor: H4/T5/A4/O4 | 1 | 1 | dialogue | `D-D-D-C` | 0.20/2.61 |
| xuanhuan | 178 | prelabel: H4/T5/A5/O5 | 1 | 2 | combat | `C-C-C-C` | 0.26/1.52 |
| xuanhuan | 194 | anchor: H2/T2/A1/O2 | 1 | 2 | dialogue | `C-D-D-D` | 0.17/1.26 |
| xuanhuan | 199 | prelabel: H4/T5/A5/O5 | 2 | 2 | dialogue | `D-D-D-C` | 0.21/1.14 |

## 局限

- 本报告只覆盖 Task 196 的 xuanhuan + sci-fi 60 章样本，不能外推到全部体裁。
- anchor + spotcheck 共 24 章，只支撑方向性校准，不支撑 hard gate 阈值。
- prelabel 仅用于对照，未作为真值参与 precision / recall 计算。
- 所有信号均为 report-only；任何进入 prompt 或 gate 的尝试必须另立任务并回归。
