"""Style Mimicry Engine — 从参考作品提取风格样本并注入上下文."""

from __future__ import annotations

from songyan.models.context import ContextPackage, SoftReference
from songyan.models.style_mimicry import StyleSample

# ---------------------------------------------------------------------------
# 内置风格样本库
# ---------------------------------------------------------------------------

_BUILTIN_SAMPLES: dict[str, StyleSample] = {
    "三体": StyleSample(
        work_name="三体",
        author="刘慈欣",
        excerpt=(
            "汪淼觉得这根本不是人能做出来的事，但眼前的数字确实在倒计时。"
            "他试图用理智去解释，可越解释越觉得荒谬。"
            "宇宙的背景辐射中竟然出现了规律的闪烁，"
            "那不是自然现象，那是某种存在留下的信息。"
            "他想起叶文洁说过的话：不要回答。"
            "但现在，人类已经回答了，而且回答得太彻底。"
        ),
        analysis=(
            "句式节奏：简洁短句为主，概念密集，每句承载一个科学或哲学命题；"
            "描写密度：低，重概念轻环境；"
            "对话风格：克制、信息量大，常带有预言性质；"
            "词汇偏好：科学术语、宇宙尺度词汇、冷峻的动词。"
        ),
        genre_tags=["硬科幻", "宏观叙事", "冷峻"],
        confidence=0.95,
    ),
    "射雕英雄传": StyleSample(
        work_name="射雕英雄传",
        author="金庸",
        excerpt=(
            "郭靖见那道士身法飘逸，掌势如行云流水，竟全然瞧不出破绽。"
            "他心中暗惊，手上却不敢怠慢，一招『亢龙有悔』蓄势待发。"
            "那道士笑道：'小伙子，内力倒是浑厚，可惜招式太死板。'"
            "说着身形一转，已绕至郭靖身后。"
            "郭靖急退三步，背脊已抵上石壁，心中反倒静下来。"
        ),
        analysis=(
            "句式节奏：长短交错，动作描写用短句，心理活动用长句；"
            "描写密度：中等，武打动作细腻，环境点到为止；"
            "对话风格：机智、带有江湖气息，常有双关和机锋；"
            "词汇偏好：古典词汇、武学招式名、江湖称谓。"
        ),
        genre_tags=["武侠", "古韵", "动作描写"],
        confidence=0.95,
    ),
    "长安十二时辰": StyleSample(
        work_name="长安十二时辰",
        author="马伯庸",
        excerpt=(
            "张小敬站在望楼上，俯瞰着灯火通明的长安城。"
            "每一盏灯笼下都可能藏着刺客，每一条巷弄里都可能是陷阱。"
            "他只有十二个时辰。"
            "从西市到东市，从平康坊到兴庆宫，"
            "他必须在这座城市的血管里奔跑，"
            "在阴谋发酵之前找到那根引线。"
            "而在他看不见的地方，有人正微笑着转动一枚玉佩。"
        ),
        analysis=(
            "句式节奏：紧凑，时间压力感强，频繁使用短句制造紧迫感；"
            "描写密度：高，历史细节密集，器物、服饰、建筑均有考据；"
            "对话风格：干练，信息量大，常伴随动作进行；"
            "词汇偏好：唐代官制、坊市名称、器物专有名词。"
        ),
        genre_tags=["历史悬疑", "紧凑", "多线叙事"],
        confidence=0.90,
    ),
    "流浪地球": StyleSample(
        work_name="流浪地球",
        author="刘慈欣",
        excerpt=(
            "发动机的光芒照亮了半个夜空，像一把巨大的光剑刺向宇宙。"
            "地下城的生活是规律的，也是压抑的。"
            "人们习惯了永昼与永夜的交替，习惯了地震和岩浆的威胁。"
            "但没有人抱怨，因为所有人都知道，地球正在离开太阳系。"
            "这不是一个人的选择，这是全人类的选择。"
            "而选择的代价，就是放弃天空。"
        ),
        analysis=(
            "句式节奏：冷峻、平稳，大段落叙述中偶尔插入短句制造停顿；"
            "描写密度：中等偏下，重技术细节和集体感受，轻个人情感；"
            "对话风格：极少，以叙述者独白为主；"
            "词汇偏好：工程术语、集体主义词汇、天文和物理概念。"
        ),
        genre_tags=["末日科幻", "冷峻", "集体主义"],
        confidence=0.92,
    ),
    "雪中悍刀行": StyleSample(
        work_name="雪中悍刀行",
        author="烽火戏诸侯",
        excerpt=(
            "徐凤年提起那壶温好的黄酒，仰头灌了一口。"
            "酒液入喉，火烧似的辣。"
            "他望着窗外的那株老梅，忽然想起很多年前，"
            "那个在风雪中为他撑伞的老黄。"
            "人走了，剑还在。"
            "剑在，江湖就还在。"
            "他把酒壶往桌上一顿，笑道：'走，去会会那位天下第一。'"
        ),
        analysis=(
            "句式节奏：诗化短句与长叙述交替，富有韵律感；"
            "描写密度：中等，重意境轻细节，常用留白；"
            "对话风格：洒脱、江湖气，常有豪情与反讽并存；"
            "词汇偏好：古典意象（酒、剑、风雪）、江湖称谓、诗意化动词。"
        ),
        genre_tags=["玄幻", "诗意", "江湖气", "人物群像"],
        confidence=0.88,
    ),
}


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------
class StyleMimicryEngine:
    """风格模仿引擎 — 提取参考作品风格并注入上下文."""

    def __init__(self) -> None:
        self._builtin_samples: dict[str, StyleSample] = dict(_BUILTIN_SAMPLES)

    def extract_style_sample(self, reference_work: str) -> StyleSample | None:
        """从参考作品提取风格样本.

        Args:
            reference_work: 作品名（如"三体"）或文本片段。
                - 如果是已知作品名，返回内置预置样本。
                - 如果是文本片段（长度 > 50 字），用启发式规则生成样本。
                - 否则返回 None。

        Returns:
            StyleSample 或 None。
        """
        # 1. 直接匹配内置库
        if reference_work in self._builtin_samples:
            return self._builtin_samples[reference_work]

        # 2. 尝试模糊匹配（去掉书名号等）
        cleaned = reference_work.strip("《》").strip()
        if cleaned in self._builtin_samples:
            return self._builtin_samples[cleaned]

        # 3. 如果是文本片段（长度 > 50），用启发式规则
        if len(reference_work) > 50:
            return self._heuristic_extract(reference_work)

        return None

    def _heuristic_extract(self, text: str) -> StyleSample:
        """启发式提取风格特征.

        基于文本的统计特征生成简单的风格分析。
        """
        # 简单启发式：计算平均句长、对话比例等
        sentences = [s.strip() for s in text.split("。") if s.strip()]
        avg_len = sum(len(s) for s in sentences) / max(len(sentences), 1)

        dialogue_count = text.count("'") + text.count("'") + text.count("「") + text.count("「")
        dialogue_ratio = dialogue_count / max(len(text), 1)

        # 生成分析描述
        rhythm = "短促有力" if avg_len < 20 else "绵长舒缓" if avg_len > 50 else "错落有致"
        desc_density = "高" if avg_len > 40 else "中" if avg_len > 25 else "低"
        dialogue_style = "丰富" if dialogue_ratio > 0.1 else "克制"

        analysis = (
            f"句式节奏：{rhythm}，平均句长 {avg_len:.0f} 字；"
            f"描写密度：{desc_density}；"
            f"对话风格：{dialogue_style}；"
            f"词汇偏好：基于输入文本的统计推断。"
        )

        return StyleSample(
            work_name="自定义文本",
            excerpt=text[:500],
            analysis=analysis,
            genre_tags=["自定义"],
            confidence=0.5,
        )

    def inject_into_context(
        self,
        style_sample: StyleSample,
        ctx: ContextPackage,
    ) -> ContextPackage:
        """将风格样本注入 ContextPackage.soft_references.

        Args:
            style_sample: 要注入的风格样本。
            ctx: 当前上下文包。

        Returns:
            注入后的上下文包（原地修改）。
        """
        import json as _json

        content = _json.dumps(
            {
                "work_name": style_sample.work_name,
                "author": style_sample.author or "未知作者",
                "excerpt": style_sample.excerpt,
                "analysis": style_sample.analysis,
            },
            ensure_ascii=False,
        )
        ref = SoftReference(
            type="style_sample",
            content=content,
            relevance_score=0.9,
            is_critical=False,
        )
        ctx.soft_references.append(ref)
        return ctx

    def inject_multiple(
        self,
        style_samples: list[StyleSample],
        ctx: ContextPackage,
    ) -> ContextPackage:
        """批量注入多个风格样本.

        Args:
            style_samples: 风格样本列表。
            ctx: 当前上下文包。

        Returns:
            注入后的上下文包。
        """
        for sample in style_samples:
            ctx = self.inject_into_context(sample, ctx)
        return ctx
