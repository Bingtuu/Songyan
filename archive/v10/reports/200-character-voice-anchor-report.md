# Task 200 角色声纹锚点离线报告

> generated_at: `2026-08-01T04:34:26.522743+00:00`
> sample_set: `archive/v10/artifacts/196-excellence-sample-set.json`
> annotations: `archive/v10/artifacts/196-excellence-annotations.json`
> excellence_report: `archive/v10/artifacts/197-198-excellence-signals-report.json`
> style_card_report: `archive/v10/artifacts/199-style-card-report.json`

## 边界

- report-only / observe-only
- voice anchors are observations, not DialogueStyleCard runtime data
- does not write back to characters or character_states
- does not modify Writer or CreativeDirector prompts
- does not enter accept/reject gates
- does not change CED, five-gate, segment audit, or T9

## 总览

| scope | anchors | unknown lines | weak explained |
|-------|--------:|--------------:|----------------|
| all | 17 | 1408 | 15/15 |
| genre:scifi | 10 | 752 | 8/8 |
| genre:xuanhuan | 7 | 656 | 7/7 |

## 声纹锚点

### all / 林渊

- character_id: `char-186d71f4`
- role_type: `protagonist`
- evidence_chapters: scifi Ch1, scifi Ch104, scifi Ch105, scifi Ch118, scifi Ch120, scifi Ch134, scifi Ch135, scifi Ch145, scifi Ch148, scifi Ch162, scifi Ch164, scifi Ch169, scifi Ch17, scifi Ch178, scifi Ch194, scifi Ch199, scifi Ch21, scifi Ch23, scifi Ch32, scifi Ch39, scifi Ch47, scifi Ch50, scifi Ch53, scifi Ch60, scifi Ch61, scifi Ch71, scifi Ch80, scifi Ch84, scifi Ch92, scifi Ch98
- distinctiveness_score: `0.439`
- interaction_pattern: `terse`
- lexical_markers: 方舟, 协议, 建造, 造者, 建造者, 所以, 一个, 神经
- emotional_register: 怒, 怕, 急, 疯
- drift_or_homogeneity_hits: -
- limitations: report-only observation, not DialogueStyleCard, speaker attribution is heuristic

sample_lines:
- Ch1 `说具体。` (pre_speech, 第7段第1句)
- Ch1 `调取它的初步扫描数据，` (post_speech, 第39段第1句)
- Ch1 `全波段扫描，能量场分析，表面结构成像。` (pre_speech, 第39段第1句)
- Ch1 `柯伊伯带深处有一个非自然结构，` (post_speech, 第53段第1句)
- Ch1 `我需要用考古权限进行详细扫描。` (pre_speech, 第53段第1句)

### all / 陆沉

- character_id: `char-9f6c78ce`
- role_type: `protagonist`
- evidence_chapters: xuanhuan Ch1, xuanhuan Ch104, xuanhuan Ch105, xuanhuan Ch118, xuanhuan Ch120, xuanhuan Ch134, xuanhuan Ch135, xuanhuan Ch145, xuanhuan Ch148, xuanhuan Ch162, xuanhuan Ch164, xuanhuan Ch169, xuanhuan Ch17, xuanhuan Ch178, xuanhuan Ch194, xuanhuan Ch199, xuanhuan Ch21, xuanhuan Ch23, xuanhuan Ch32, xuanhuan Ch39, xuanhuan Ch47, xuanhuan Ch50, xuanhuan Ch53, xuanhuan Ch60, xuanhuan Ch61, xuanhuan Ch80, xuanhuan Ch84, xuanhuan Ch92, xuanhuan Ch98
- distinctiveness_score: `0.439`
- interaction_pattern: `terse`
- lexical_markers: 封印, 知道, 父亲, 碎片, 这里, 灵渊, 令牌, 在这
- emotional_register: 冷, 疯, 杀
- drift_or_homogeneity_hits: -
- limitations: report-only observation, not DialogueStyleCard, speaker attribution is heuristic

sample_lines:
- Ch1 `又废了一块？你小子今天手抖得厉害，昨晚没睡好？` (post_speech, 第19段第2句)
- Ch1 `再来一锤。` (post_speech, 第25段第1句)
- Ch1 `下去看一眼。` (post_speech, 第41段第1句)
- Ch1 `你疯了？` (post_speech, 第42段第1句)
- Ch1 `这是……上古灵渊？这地方怎么会在我们铁匠铺下面？` (post_speech, 第48段第1句)

### all / 陈曦

- character_id: `char-835afdf11a294b5eac74a5d8998bd9a2-c504a760`
- role_type: `supporting`
- evidence_chapters: scifi Ch47, scifi Ch50, scifi Ch53, scifi Ch60, scifi Ch61, scifi Ch71, scifi Ch80, scifi Ch84, scifi Ch92
- distinctiveness_score: `0.47`
- interaction_pattern: `measured`
- lexical_markers: 方舟, 共鸣, 频率, 一个, 鸣频, 共鸣频, 鸣频率, 建造
- emotional_register: 急, 痛
- drift_or_homogeneity_hits: -
- limitations: report-only observation, not DialogueStyleCard, speaker attribution is heuristic

sample_lines:
- Ch47 `……我发现了。我知道他们在做什么。这不是监视，不是观察，是——他们在建造一个容器，一个能容纳意识的容器。但容器本身也在进化，它开始有自己的意志……` (voice_cue, 第31段第1句)
- Ch47 `别信她` (pre_speech, 第102段第1句)
- Ch50 `林渊。` (voice_cue, 第16段第1句)
- Ch50 `嗯，是这样……你刚刚激活了恒星净化协议。` (voice_cue, 第18段第1句)
- Ch50 `恒星净化协议的本质不是清除观察者，` (post_speech, 第34段第1句)

### all / 灵渊老人

- character_id: `char-d160a55a51de4a2bb82440ebc03ec23a-54c4b063`
- role_type: `supporting`
- evidence_chapters: xuanhuan Ch162, xuanhuan Ch199, xuanhuan Ch53, xuanhuan Ch60, xuanhuan Ch61
- distinctiveness_score: `0.508`
- interaction_pattern: `measured`
- lexical_markers: 封印, 令牌, 碎片, 血脉, 牌碎, 污染, 令牌碎, 牌碎片
- emotional_register: 杀
- drift_or_homogeneity_hits: -
- limitations: report-only observation, not DialogueStyleCard, speaker attribution is heuristic

sample_lines:
- Ch53 `天祈宗的人在底下凿了三十年。` (voice_cue, 第5段第1句)
- Ch53 `他们在封印根基上打洞，往里面灌蚀灵液。一滴能消耗一个凝气境修士十年的灵气积累。他们灌了整整三千斤。` (voice_cue, 第5段第2句)
- Ch53 `七年零三个月。` (voice_cue, 第12段第1句)
- Ch53 `他们没空说话。` (post_speech, 第14段第1句)
- Ch53 `最后那夜，封印崩了个口子。你爹用后背堵住裂纹，你娘十指的血全部滴进阵基。天亮后封印稳住了，但他们——` (pre_speech, 第14段第2句)

### all / 赵铭

- character_id: `char-835afdf11a294b5eac74a5d8998bd9a2-930b3f2e`
- role_type: `antagonist`
- evidence_chapters: scifi Ch105, scifi Ch135, scifi Ch145, scifi Ch162, scifi Ch169, scifi Ch178, scifi Ch71, scifi Ch84, scifi Ch92, scifi Ch98
- distinctiveness_score: `0.422`
- interaction_pattern: `terse`
- lexical_markers: 林渊, 共鸣, 方舟, 你在, 渊你, 信号, 容器, 突破
- emotional_register: 杀
- drift_or_homogeneity_hits: -
- limitations: report-only observation, not DialogueStyleCard, speaker attribution is heuristic

sample_lines:
- Ch71 `你在做什么？` (voice_cue, 第36段第1句)
- Ch71 `林渊，你的航向——` (voice_cue, 第39段第1句)
- Ch84 `你、在、做、什、么？` (voice_cue, 第3段第1句)
- Ch84 `共鸣耦合度——你让它继续上升？` (voice_cue, 第3段第2句)
- Ch84 `（停顿半秒）切断节点#19的连接。` (voice_cue, 第15段第1句)

### all / 老雷

- character_id: `char-835afdf11a294b5eac74a5d8998bd9a2-95f1d8ba`
- role_type: `supporting`
- evidence_chapters: scifi Ch17, scifi Ch194, scifi Ch199, scifi Ch21
- distinctiveness_score: `0.347`
- interaction_pattern: `terse`
- lexical_markers: 方舟, 钥匙, 林渊, 观察, 察者, 观察者, 听着, 共鸣
- emotional_register: -
- drift_or_homogeneity_hits: -
- limitations: report-only observation, not DialogueStyleCard, speaker attribution is heuristic

sample_lines:
- Ch17 `听着，小子，我没多少时间了。` (voice_cue, 第47段第1句)
- Ch17 `建造者的回收评估已经完成。观察者派出的回收舰队正在路上。方舟的共鸣信号像灯塔一样在宇宙中闪烁，他们不可能错过。你有两条路——找到木星轨道上的星门遗迹，激活第二把钥匙；或者看着方舟被摧毁，所有人在太阳…` (voice_cue, 第49段第1句)
- Ch17 `方舟爆炸后会释放出引力波信号。` (post_speech, 第53段第1句)
- Ch17 `听着，还有一件事。` (voice_cue, 第60段第1句)
- Ch17 `人类的存在不是偶然。建造者在销毁实验室前发现了某种规律——在宇宙的基本结构中，偶然性被刻意保留了。像是有人在规则中留下了一个后门。` (voice_cue, 第60段第3句)

### all / 指挥官

- character_id: `char-835afdf11a294b5eac74a5d8998bd9a2-0ca7a63a`
- role_type: `supporting`
- evidence_chapters: scifi Ch1, scifi Ch169, scifi Ch17
- distinctiveness_score: `0.368`
- interaction_pattern: `terse`
- lexical_markers: 时间, 一个, 信号, 到了, 明白, 林渊, 渊你, 你在
- emotional_register: -
- drift_or_homogeneity_hits: -
- limitations: report-only observation, not DialogueStyleCard, speaker attribution is heuristic

sample_lines:
- Ch1 `林渊，你在干什么？` (voice_cue, 第48段第2句)
- Ch1 `那你告诉我，为什么一个距离我们四十个天文单位、被柯伊伯带掩埋了可能几万年的东西，它的信号会和一个人类的前额叶皮层产生共振？` (post_speech, 第71段第1句)
- Ch1 `我什么都不知道，` (post_speech, 第76段第1句)
- Ch1 `但根据程序，在不明目标被确认安全之前，任何人都不能——` (pre_speech, 第76段第1句)
- Ch1 `然后他的飞船在返回途中失去了所有通讯信号。三小时后，我们在离观测站不到五百公里的地方找到了残骸。黑匣子里的数据全部被清除，只剩下一个时间戳。` (voice_cue, 第88段第1句)

### all / 张远

- character_id: `char-835afdf11a294b5eac74a5d8998bd9a2-b4126f0f`
- role_type: `supporting`
- evidence_chapters: scifi Ch118, scifi Ch120, scifi Ch134, scifi Ch135, scifi Ch92
- distinctiveness_score: `0.369`
- interaction_pattern: `terse`
- lexical_markers: 协议, 方舟, 议层, 协议层, 意志, 自己, 十七, 意识
- emotional_register: -
- drift_or_homogeneity_hits: -
- limitations: report-only observation, not DialogueStyleCard, speaker attribution is heuristic

sample_lines:
- Ch92 `根据协议，我是共鸣诱导协议的执行监督者。` (voice_cue, 第66段第3句)
- Ch92 `她知道我会变成这样吗？` (post_speech, 第89段第1句)
- Ch118 `你发出的摩尔斯电码。` (voice_cue, 第3段第1句)
- Ch118 `是我。` (voice_cue, 第7段第1句)
- Ch118 `那时候……我还以为自己能控制。` (voice_cue, 第7段第2句)

### all / 古老存在

- character_id: `char-d160a55a51de4a2bb82440ebc03ec23a-36f9a011`
- role_type: `supporting`
- evidence_chapters: xuanhuan Ch194
- distinctiveness_score: `0.384`
- interaction_pattern: `terse`
- lexical_markers: 封印, 她在, 在石, 石棺, 她在石, 在石棺, 传承, 印术
- emotional_register: -
- drift_or_homogeneity_hits: -
- limitations: report-only observation, not DialogueStyleCard, speaker attribution is heuristic

sample_lines:
- Ch194 `……你明白了？` (voice_cue, 第26段第1句)
- Ch194 `我是它的主人。` (post_speech, 第33段第1句)
- Ch194 `你父亲没告诉你，` (post_speech, 第37段第1句)
- Ch194 `这传承从来就不是给你的。` (pre_speech, 第37段第1句)
- Ch194 `他封印我的时候，用的不是你母亲的封印术，用的是你自己的血。` (voice_cue, 第39段第1句)

### all / 老周头

- character_id: `char-afa4025a`
- role_type: `supporting`
- evidence_chapters: xuanhuan Ch1, xuanhuan Ch145, xuanhuan Ch80
- distinctiveness_score: `0.471`
- interaction_pattern: `terse`
- lexical_markers: -
- emotional_register: 沉
- drift_or_homogeneity_hits: -
- limitations: report-only observation, not DialogueStyleCard, speaker attribution is heuristic

sample_lines:
- Ch1 `愣着干啥？` (voice_cue, 第18段第1句)
- Ch1 `别动。` (voice_cue, 第36段第1句)
- Ch1 `这地方不对劲。你先退出来，我去找——` (voice_cue, 第37段第1句)
- Ch1 `来不及了。` (voice_cue, 第38段第1句)
- Ch1 `三息？这他娘的是要命！你现在连练气都没有，灵气灌体跟直接灌岩浆有什么区别？不行，赶紧走，这玩意儿邪门。` (nearby_action, 第52段第1句)

### all / 考验之灵

- character_id: `char-d160a55a51de4a2bb82440ebc03ec23a-69f1c421`
- role_type: `supporting`
- evidence_chapters: xuanhuan Ch17
- distinctiveness_score: `0.435`
- interaction_pattern: `question-heavy`
- lexical_markers: 倒是, 之前, 几个
- emotional_register: -
- drift_or_homogeneity_hits: -
- limitations: report-only observation, not DialogueStyleCard, speaker attribution is heuristic

sample_lines:
- Ch17 `九煞炼心阵。` (voice_cue, 第21段第1句)
- Ch17 `有趣。` (post_speech, 第27段第1句)
- Ch17 `你倒是比之前那几个干脆得多。` (voice_cue, 第27段第2句)
- Ch17 `之前几个？` (post_speech, 第28段第1句)
- Ch17 `倒是有几分本事。` (voice_cue, 第64段第1句)

### all / 妹妹

- character_id: `char-835afdf11a294b5eac74a5d8998bd9a2-04f039f0`
- role_type: `supporting`
- evidence_chapters: scifi Ch145
- distinctiveness_score: `0.365`
- interaction_pattern: `terse`
- lexical_markers: 作为, 为通, 通道, 道锚, 锚点, 你会, 作为通, 为通道
- emotional_register: -
- drift_or_homogeneity_hits: -
- limitations: report-only observation, not DialogueStyleCard, speaker attribution is heuristic

sample_lines:
- Ch145 `我需要你的神经签名作为通道锚点。` (voice_cue, 第69段第2句)
- Ch145 `你会死的。` (voice_cue, 第70段第1句)
- Ch145 `你会消散。` (voice_cue, 第71段第1句)
- Ch145 `我知道。` (voice_cue, 第72段第1句)
- Ch145 `我用了十年。` (post_speech, 第76段第1句)

### all / 小周

- character_id: `char-835afdf11a294b5eac74a5d8998bd9a2-c2e5266c`
- role_type: `supporting`
- evidence_chapters: scifi Ch1
- distinctiveness_score: `0.359`
- interaction_pattern: `terse`
- lexical_markers: 林工, 东西
- emotional_register: -
- drift_or_homogeneity_hits: -
- limitations: report-only observation, not DialogueStyleCard, speaker attribution is heuristic

sample_lines:
- Ch1 `林工，B区深空探测阵列有点异常。` (voice_cue, 第5段第1句)
- Ch1 `老天……` (voice_cue, 第36段第1句)
- Ch1 `这是什么东西？` (voice_cue, 第36段第2句)
- Ch1 `那个……林工，这东西距离我们太远了，常规扫描分辨率不够。要精确成像需要动用——` (post_speech, 第40段第1句)
- Ch1 `用我的权限。` (post_speech, 第41段第1句)

### all / 陈薇

- character_id: `char-835afdf11a294b5eac74a5d8998bd9a2-b1625ec4`
- role_type: `supporting`
- evidence_chapters: scifi Ch104, scifi Ch178
- distinctiveness_score: `0.426`
- interaction_pattern: `question-heavy`
- lexical_markers: 陷阱, 是陷, 林渊, 是陷阱
- emotional_register: -
- drift_or_homogeneity_hits: -
- limitations: report-only observation, not DialogueStyleCard, speaker attribution is heuristic

sample_lines:
- Ch104 `所以反向锚点……从一开始就是陷阱？` (post_speech, 第60段第2句)
- Ch104 `陷阱？` (post_speech, 第61段第1句)
- Ch104 `谢谢。` (voice_cue, 第95段第1句)
- Ch104 `林渊，谢谢你。` (voice_cue, 第95段第2句)
- Ch178 `林渊——别进来——这是陷阱！` (voice_cue, 第87段第1句)

### all / 毒鳞

- character_id: `char-d160a55a51de4a2bb82440ebc03ec23a-c0619062`
- role_type: `antagonist`
- evidence_chapters: xuanhuan Ch104
- distinctiveness_score: `0.328`
- interaction_pattern: `terse`
- lexical_markers: -
- emotional_register: -
- drift_or_homogeneity_hits: -
- limitations: report-only observation, not DialogueStyleCard, speaker attribution is heuristic, small attributed sample

sample_lines:
- Ch104 `别浪费力气了。` (post_speech, 第61段第1句)
- Ch104 `这石室里布了七重锁灵阵，你连灵力都调动不起来。` (pre_speech, 第61段第2句)
- Ch104 `他娘的——` (voice_cue, 第76段第1句)

### all / 第七十六号

- character_id: `char-835afdf11a294b5eac74a5d8998bd9a2-16fa99ba`
- role_type: `supporting`
- evidence_chapters: scifi Ch47, scifi Ch50
- distinctiveness_score: `0.414`
- interaction_pattern: `question-heavy`
- lexical_markers: -
- emotional_register: -
- drift_or_homogeneity_hits: -
- limitations: report-only observation, not DialogueStyleCard, speaker attribution is heuristic, small attributed sample

sample_lines:
- Ch47 `你是什么？` (post_speech, 第17段第1句)
- Ch47 `你看到的编号矛盾是因为——` (voice_cue, 第18段第2句)
- Ch50 `然后呢？` (voice_cue, 第20段第1句)

### all / 高个修士

- character_id: `char-d160a55a51de4a2bb82440ebc03ec23a-3a431a6d`
- role_type: `antagonist`
- evidence_chapters: xuanhuan Ch178
- distinctiveness_score: `0.408`
- interaction_pattern: `urgent-imperative`
- lexical_markers: -
- emotional_register: -
- drift_or_homogeneity_hits: -
- limitations: report-only observation, not DialogueStyleCard, speaker attribution is heuristic, small attributed sample

sample_lines:
- Ch178 `跑啊。` (voice_cue, 第13段第1句)
- Ch178 `他用了灵渊传承的禁术——那种突破代价很大，撑不了多久——` (post_speech, 第63段第1句)
- Ch178 `他进暗河了！老四，追踪符！` (voice_cue, 第80段第1句)

### genre:scifi / 林渊

- character_id: `char-186d71f4`
- role_type: `protagonist`
- evidence_chapters: scifi Ch1, scifi Ch104, scifi Ch105, scifi Ch118, scifi Ch120, scifi Ch134, scifi Ch135, scifi Ch145, scifi Ch148, scifi Ch162, scifi Ch164, scifi Ch169, scifi Ch17, scifi Ch178, scifi Ch194, scifi Ch199, scifi Ch21, scifi Ch23, scifi Ch32, scifi Ch39, scifi Ch47, scifi Ch50, scifi Ch53, scifi Ch60, scifi Ch61, scifi Ch71, scifi Ch80, scifi Ch84, scifi Ch92, scifi Ch98
- distinctiveness_score: `0.417`
- interaction_pattern: `terse`
- lexical_markers: 方舟, 协议, 建造, 造者, 建造者, 所以, 一个, 神经
- emotional_register: 怒, 怕, 急, 疯
- drift_or_homogeneity_hits: -
- limitations: report-only observation, not DialogueStyleCard, speaker attribution is heuristic

sample_lines:
- Ch1 `说具体。` (pre_speech, 第7段第1句)
- Ch1 `调取它的初步扫描数据，` (post_speech, 第39段第1句)
- Ch1 `全波段扫描，能量场分析，表面结构成像。` (pre_speech, 第39段第1句)
- Ch1 `柯伊伯带深处有一个非自然结构，` (post_speech, 第53段第1句)
- Ch1 `我需要用考古权限进行详细扫描。` (pre_speech, 第53段第1句)

### genre:scifi / 陈曦

- character_id: `char-835afdf11a294b5eac74a5d8998bd9a2-c504a760`
- role_type: `supporting`
- evidence_chapters: scifi Ch47, scifi Ch50, scifi Ch53, scifi Ch60, scifi Ch61, scifi Ch71, scifi Ch80, scifi Ch84, scifi Ch92
- distinctiveness_score: `0.445`
- interaction_pattern: `measured`
- lexical_markers: 方舟, 共鸣, 频率, 一个, 鸣频, 共鸣频, 鸣频率, 建造
- emotional_register: 急, 痛
- drift_or_homogeneity_hits: -
- limitations: report-only observation, not DialogueStyleCard, speaker attribution is heuristic

sample_lines:
- Ch47 `……我发现了。我知道他们在做什么。这不是监视，不是观察，是——他们在建造一个容器，一个能容纳意识的容器。但容器本身也在进化，它开始有自己的意志……` (voice_cue, 第31段第1句)
- Ch47 `别信她` (pre_speech, 第102段第1句)
- Ch50 `林渊。` (voice_cue, 第16段第1句)
- Ch50 `嗯，是这样……你刚刚激活了恒星净化协议。` (voice_cue, 第18段第1句)
- Ch50 `恒星净化协议的本质不是清除观察者，` (post_speech, 第34段第1句)

### genre:scifi / 赵铭

- character_id: `char-835afdf11a294b5eac74a5d8998bd9a2-930b3f2e`
- role_type: `antagonist`
- evidence_chapters: scifi Ch105, scifi Ch135, scifi Ch145, scifi Ch162, scifi Ch169, scifi Ch178, scifi Ch71, scifi Ch84, scifi Ch92, scifi Ch98
- distinctiveness_score: `0.411`
- interaction_pattern: `terse`
- lexical_markers: 林渊, 共鸣, 方舟, 你在, 渊你, 信号, 容器, 突破
- emotional_register: 杀
- drift_or_homogeneity_hits: -
- limitations: report-only observation, not DialogueStyleCard, speaker attribution is heuristic

sample_lines:
- Ch71 `你在做什么？` (voice_cue, 第36段第1句)
- Ch71 `林渊，你的航向——` (voice_cue, 第39段第1句)
- Ch84 `你、在、做、什、么？` (voice_cue, 第3段第1句)
- Ch84 `共鸣耦合度——你让它继续上升？` (voice_cue, 第3段第2句)
- Ch84 `（停顿半秒）切断节点#19的连接。` (voice_cue, 第15段第1句)

### genre:scifi / 老雷

- character_id: `char-835afdf11a294b5eac74a5d8998bd9a2-95f1d8ba`
- role_type: `supporting`
- evidence_chapters: scifi Ch17, scifi Ch194, scifi Ch199, scifi Ch21
- distinctiveness_score: `0.321`
- interaction_pattern: `terse`
- lexical_markers: 方舟, 钥匙, 林渊, 观察, 察者, 观察者, 听着, 共鸣
- emotional_register: -
- drift_or_homogeneity_hits: -
- limitations: report-only observation, not DialogueStyleCard, speaker attribution is heuristic

sample_lines:
- Ch17 `听着，小子，我没多少时间了。` (voice_cue, 第47段第1句)
- Ch17 `建造者的回收评估已经完成。观察者派出的回收舰队正在路上。方舟的共鸣信号像灯塔一样在宇宙中闪烁，他们不可能错过。你有两条路——找到木星轨道上的星门遗迹，激活第二把钥匙；或者看着方舟被摧毁，所有人在太阳…` (voice_cue, 第49段第1句)
- Ch17 `方舟爆炸后会释放出引力波信号。` (post_speech, 第53段第1句)
- Ch17 `听着，还有一件事。` (voice_cue, 第60段第1句)
- Ch17 `人类的存在不是偶然。建造者在销毁实验室前发现了某种规律——在宇宙的基本结构中，偶然性被刻意保留了。像是有人在规则中留下了一个后门。` (voice_cue, 第60段第3句)

### genre:scifi / 指挥官

- character_id: `char-835afdf11a294b5eac74a5d8998bd9a2-0ca7a63a`
- role_type: `supporting`
- evidence_chapters: scifi Ch1, scifi Ch169, scifi Ch17
- distinctiveness_score: `0.336`
- interaction_pattern: `terse`
- lexical_markers: 时间, 一个, 信号, 到了, 明白, 林渊, 渊你, 你在
- emotional_register: -
- drift_or_homogeneity_hits: -
- limitations: report-only observation, not DialogueStyleCard, speaker attribution is heuristic

sample_lines:
- Ch1 `林渊，你在干什么？` (voice_cue, 第48段第2句)
- Ch1 `那你告诉我，为什么一个距离我们四十个天文单位、被柯伊伯带掩埋了可能几万年的东西，它的信号会和一个人类的前额叶皮层产生共振？` (post_speech, 第71段第1句)
- Ch1 `我什么都不知道，` (post_speech, 第76段第1句)
- Ch1 `但根据程序，在不明目标被确认安全之前，任何人都不能——` (pre_speech, 第76段第1句)
- Ch1 `然后他的飞船在返回途中失去了所有通讯信号。三小时后，我们在离观测站不到五百公里的地方找到了残骸。黑匣子里的数据全部被清除，只剩下一个时间戳。` (voice_cue, 第88段第1句)

### genre:scifi / 张远

- character_id: `char-835afdf11a294b5eac74a5d8998bd9a2-b4126f0f`
- role_type: `supporting`
- evidence_chapters: scifi Ch118, scifi Ch120, scifi Ch134, scifi Ch135, scifi Ch92
- distinctiveness_score: `0.343`
- interaction_pattern: `terse`
- lexical_markers: 协议, 方舟, 议层, 协议层, 意志, 自己, 十七, 意识
- emotional_register: -
- drift_or_homogeneity_hits: -
- limitations: report-only observation, not DialogueStyleCard, speaker attribution is heuristic

sample_lines:
- Ch92 `根据协议，我是共鸣诱导协议的执行监督者。` (voice_cue, 第66段第3句)
- Ch92 `她知道我会变成这样吗？` (post_speech, 第89段第1句)
- Ch118 `你发出的摩尔斯电码。` (voice_cue, 第3段第1句)
- Ch118 `是我。` (voice_cue, 第7段第1句)
- Ch118 `那时候……我还以为自己能控制。` (voice_cue, 第7段第2句)

### genre:scifi / 妹妹

- character_id: `char-835afdf11a294b5eac74a5d8998bd9a2-04f039f0`
- role_type: `supporting`
- evidence_chapters: scifi Ch145
- distinctiveness_score: `0.355`
- interaction_pattern: `terse`
- lexical_markers: 作为, 为通, 通道, 道锚, 锚点, 你会, 作为通, 为通道
- emotional_register: -
- drift_or_homogeneity_hits: -
- limitations: report-only observation, not DialogueStyleCard, speaker attribution is heuristic

sample_lines:
- Ch145 `我需要你的神经签名作为通道锚点。` (voice_cue, 第69段第2句)
- Ch145 `你会死的。` (voice_cue, 第70段第1句)
- Ch145 `你会消散。` (voice_cue, 第71段第1句)
- Ch145 `我知道。` (voice_cue, 第72段第1句)
- Ch145 `我用了十年。` (post_speech, 第76段第1句)

### genre:scifi / 小周

- character_id: `char-835afdf11a294b5eac74a5d8998bd9a2-c2e5266c`
- role_type: `supporting`
- evidence_chapters: scifi Ch1
- distinctiveness_score: `0.343`
- interaction_pattern: `terse`
- lexical_markers: 林工, 东西
- emotional_register: -
- drift_or_homogeneity_hits: -
- limitations: report-only observation, not DialogueStyleCard, speaker attribution is heuristic

sample_lines:
- Ch1 `林工，B区深空探测阵列有点异常。` (voice_cue, 第5段第1句)
- Ch1 `老天……` (voice_cue, 第36段第1句)
- Ch1 `这是什么东西？` (voice_cue, 第36段第2句)
- Ch1 `那个……林工，这东西距离我们太远了，常规扫描分辨率不够。要精确成像需要动用——` (post_speech, 第40段第1句)
- Ch1 `用我的权限。` (post_speech, 第41段第1句)

### genre:scifi / 陈薇

- character_id: `char-835afdf11a294b5eac74a5d8998bd9a2-b1625ec4`
- role_type: `supporting`
- evidence_chapters: scifi Ch104, scifi Ch178
- distinctiveness_score: `0.424`
- interaction_pattern: `question-heavy`
- lexical_markers: 陷阱, 是陷, 林渊, 是陷阱
- emotional_register: -
- drift_or_homogeneity_hits: -
- limitations: report-only observation, not DialogueStyleCard, speaker attribution is heuristic

sample_lines:
- Ch104 `所以反向锚点……从一开始就是陷阱？` (post_speech, 第60段第2句)
- Ch104 `陷阱？` (post_speech, 第61段第1句)
- Ch104 `谢谢。` (voice_cue, 第95段第1句)
- Ch104 `林渊，谢谢你。` (voice_cue, 第95段第2句)
- Ch178 `林渊——别进来——这是陷阱！` (voice_cue, 第87段第1句)

### genre:scifi / 第七十六号

- character_id: `char-835afdf11a294b5eac74a5d8998bd9a2-16fa99ba`
- role_type: `supporting`
- evidence_chapters: scifi Ch47, scifi Ch50
- distinctiveness_score: `0.453`
- interaction_pattern: `question-heavy`
- lexical_markers: -
- emotional_register: -
- drift_or_homogeneity_hits: -
- limitations: report-only observation, not DialogueStyleCard, speaker attribution is heuristic, small attributed sample

sample_lines:
- Ch47 `你是什么？` (post_speech, 第17段第1句)
- Ch47 `你看到的编号矛盾是因为——` (voice_cue, 第18段第2句)
- Ch50 `然后呢？` (voice_cue, 第20段第1句)

### genre:xuanhuan / 陆沉

- character_id: `char-9f6c78ce`
- role_type: `protagonist`
- evidence_chapters: xuanhuan Ch1, xuanhuan Ch104, xuanhuan Ch105, xuanhuan Ch118, xuanhuan Ch120, xuanhuan Ch134, xuanhuan Ch135, xuanhuan Ch145, xuanhuan Ch148, xuanhuan Ch162, xuanhuan Ch164, xuanhuan Ch169, xuanhuan Ch17, xuanhuan Ch178, xuanhuan Ch194, xuanhuan Ch199, xuanhuan Ch21, xuanhuan Ch23, xuanhuan Ch32, xuanhuan Ch39, xuanhuan Ch47, xuanhuan Ch50, xuanhuan Ch53, xuanhuan Ch60, xuanhuan Ch61, xuanhuan Ch80, xuanhuan Ch84, xuanhuan Ch92, xuanhuan Ch98
- distinctiveness_score: `0.465`
- interaction_pattern: `terse`
- lexical_markers: 封印, 知道, 父亲, 碎片, 这里, 灵渊, 令牌, 在这
- emotional_register: 冷, 疯, 杀
- drift_or_homogeneity_hits: -
- limitations: report-only observation, not DialogueStyleCard, speaker attribution is heuristic

sample_lines:
- Ch1 `又废了一块？你小子今天手抖得厉害，昨晚没睡好？` (post_speech, 第19段第2句)
- Ch1 `再来一锤。` (post_speech, 第25段第1句)
- Ch1 `下去看一眼。` (post_speech, 第41段第1句)
- Ch1 `你疯了？` (post_speech, 第42段第1句)
- Ch1 `这是……上古灵渊？这地方怎么会在我们铁匠铺下面？` (post_speech, 第48段第1句)

### genre:xuanhuan / 灵渊老人

- character_id: `char-d160a55a51de4a2bb82440ebc03ec23a-54c4b063`
- role_type: `supporting`
- evidence_chapters: xuanhuan Ch162, xuanhuan Ch199, xuanhuan Ch53, xuanhuan Ch60, xuanhuan Ch61
- distinctiveness_score: `0.536`
- interaction_pattern: `measured`
- lexical_markers: 封印, 令牌, 碎片, 血脉, 牌碎, 污染, 令牌碎, 牌碎片
- emotional_register: 杀
- drift_or_homogeneity_hits: -
- limitations: report-only observation, not DialogueStyleCard, speaker attribution is heuristic

sample_lines:
- Ch53 `天祈宗的人在底下凿了三十年。` (voice_cue, 第5段第1句)
- Ch53 `他们在封印根基上打洞，往里面灌蚀灵液。一滴能消耗一个凝气境修士十年的灵气积累。他们灌了整整三千斤。` (voice_cue, 第5段第2句)
- Ch53 `七年零三个月。` (voice_cue, 第12段第1句)
- Ch53 `他们没空说话。` (post_speech, 第14段第1句)
- Ch53 `最后那夜，封印崩了个口子。你爹用后背堵住裂纹，你娘十指的血全部滴进阵基。天亮后封印稳住了，但他们——` (pre_speech, 第14段第2句)

### genre:xuanhuan / 古老存在

- character_id: `char-d160a55a51de4a2bb82440ebc03ec23a-36f9a011`
- role_type: `supporting`
- evidence_chapters: xuanhuan Ch194
- distinctiveness_score: `0.41`
- interaction_pattern: `terse`
- lexical_markers: 封印, 她在, 在石, 石棺, 她在石, 在石棺, 传承, 印术
- emotional_register: -
- drift_or_homogeneity_hits: -
- limitations: report-only observation, not DialogueStyleCard, speaker attribution is heuristic

sample_lines:
- Ch194 `……你明白了？` (voice_cue, 第26段第1句)
- Ch194 `我是它的主人。` (post_speech, 第33段第1句)
- Ch194 `你父亲没告诉你，` (post_speech, 第37段第1句)
- Ch194 `这传承从来就不是给你的。` (pre_speech, 第37段第1句)
- Ch194 `他封印我的时候，用的不是你母亲的封印术，用的是你自己的血。` (voice_cue, 第39段第1句)

### genre:xuanhuan / 老周头

- character_id: `char-afa4025a`
- role_type: `supporting`
- evidence_chapters: xuanhuan Ch1, xuanhuan Ch145, xuanhuan Ch80
- distinctiveness_score: `0.455`
- interaction_pattern: `terse`
- lexical_markers: -
- emotional_register: 沉
- drift_or_homogeneity_hits: -
- limitations: report-only observation, not DialogueStyleCard, speaker attribution is heuristic

sample_lines:
- Ch1 `愣着干啥？` (voice_cue, 第18段第1句)
- Ch1 `别动。` (voice_cue, 第36段第1句)
- Ch1 `这地方不对劲。你先退出来，我去找——` (voice_cue, 第37段第1句)
- Ch1 `来不及了。` (voice_cue, 第38段第1句)
- Ch1 `三息？这他娘的是要命！你现在连练气都没有，灵气灌体跟直接灌岩浆有什么区别？不行，赶紧走，这玩意儿邪门。` (nearby_action, 第52段第1句)

### genre:xuanhuan / 考验之灵

- character_id: `char-d160a55a51de4a2bb82440ebc03ec23a-69f1c421`
- role_type: `supporting`
- evidence_chapters: xuanhuan Ch17
- distinctiveness_score: `0.463`
- interaction_pattern: `question-heavy`
- lexical_markers: 倒是, 之前, 几个
- emotional_register: -
- drift_or_homogeneity_hits: -
- limitations: report-only observation, not DialogueStyleCard, speaker attribution is heuristic

sample_lines:
- Ch17 `九煞炼心阵。` (voice_cue, 第21段第1句)
- Ch17 `有趣。` (post_speech, 第27段第1句)
- Ch17 `你倒是比之前那几个干脆得多。` (voice_cue, 第27段第2句)
- Ch17 `之前几个？` (post_speech, 第28段第1句)
- Ch17 `倒是有几分本事。` (voice_cue, 第64段第1句)

### genre:xuanhuan / 毒鳞

- character_id: `char-d160a55a51de4a2bb82440ebc03ec23a-c0619062`
- role_type: `antagonist`
- evidence_chapters: xuanhuan Ch104
- distinctiveness_score: `0.343`
- interaction_pattern: `terse`
- lexical_markers: -
- emotional_register: -
- drift_or_homogeneity_hits: -
- limitations: report-only observation, not DialogueStyleCard, speaker attribution is heuristic, small attributed sample

sample_lines:
- Ch104 `别浪费力气了。` (post_speech, 第61段第1句)
- Ch104 `这石室里布了七重锁灵阵，你连灵力都调动不起来。` (pre_speech, 第61段第2句)
- Ch104 `他娘的——` (voice_cue, 第76段第1句)

### genre:xuanhuan / 高个修士

- character_id: `char-d160a55a51de4a2bb82440ebc03ec23a-3a431a6d`
- role_type: `antagonist`
- evidence_chapters: xuanhuan Ch178
- distinctiveness_score: `0.418`
- interaction_pattern: `urgent-imperative`
- lexical_markers: -
- emotional_register: -
- drift_or_homogeneity_hits: -
- limitations: report-only observation, not DialogueStyleCard, speaker attribution is heuristic, small attributed sample

sample_lines:
- Ch178 `跑啊。` (voice_cue, 第13段第1句)
- Ch178 `他用了灵渊传承的禁术——那种突破代价很大，撑不了多久——` (post_speech, 第63段第1句)
- Ch178 `他进暗河了！老四，追踪符！` (voice_cue, 第80段第1句)

## Unknown Attribution

### all

- line_count: `1408`
- ratio: `0.599`
- limitations: unattributed dialogue preserved instead of fabricated, unknown attribution dominates this scope
- Ch1 `就是那个……呃，冥王星轨道外侧二十三号节点的数据流，零点三秒内出现了连续十七次相位抖动。` (第8段第1句)
- Ch1 `不可能。` (第9段第1句)
- Ch1 `我也觉得不可能，呃，但校准算法跑了三遍，结果一致。` (第11段第1句)
- Ch1 `把原始数据调给我，别经过降噪滤波。` (第12段第2句)
- Ch1 `那个……原始数据全是噪声，什么都看不见。` (第13段第1句)

### genre:scifi

- line_count: `752`
- ratio: `0.547`
- limitations: unattributed dialogue preserved instead of fabricated, unknown attribution dominates this scope
- Ch1 `就是那个……呃，冥王星轨道外侧二十三号节点的数据流，零点三秒内出现了连续十七次相位抖动。` (第8段第1句)
- Ch1 `不可能。` (第9段第1句)
- Ch1 `我也觉得不可能，呃，但校准算法跑了三遍，结果一致。` (第11段第1句)
- Ch1 `把原始数据调给我，别经过降噪滤波。` (第12段第2句)
- Ch1 `那个……原始数据全是噪声，什么都看不见。` (第13段第1句)

### genre:xuanhuan

- line_count: `656`
- ratio: `0.671`
- limitations: unattributed dialogue preserved instead of fabricated, unknown attribution dominates this scope
- Ch1 `喂，问你话呢。` (第21段第1句)
- Ch1 `嗯。` (第22段第1句)
- Ch1 `嗯个屁。` (第23段第1句)
- Ch1 `饿了就说饿了，累了就歇会儿，你小子别总是一副要死不活的样子。老子还指望你养老呢。` (第23段第2句)
- Ch1 `这他娘的是什么……` (第34段第1句)

## Sanity Check

| scope | weak samples | weak with voice evidence | weak unexplained |
|-------|-------------:|-------------------------:|------------------|
| all | 15 | 15 | - |
| genre:scifi | 8 | 8 | - |
| genre:xuanhuan | 7 | 7 | - |

## 局限

- 本报告只覆盖 Task 196 的 xuanhuan + sci-fi 60 章样本。
- 说话人归因为启发式，unknown 必须保留，不得强行分配。
- 本报告不是 DialogueStyleCard，不写回角色档案，不作为生成约束。
- 弱样本解释是方向性 sanity check，不支持 hard gate 阈值。
