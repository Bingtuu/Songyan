"""V15 Task 235: 章节切分与人工确认（segment 阶段）.

只读源文件，产出可 diff 的章节边界清单；人工确认后才允许回放。
设计冻结见 docs/reports/234-v15-import-pipeline-audit.md。
"""

from __future__ import annotations

from songyan.exceptions import ImportSourceError

#: 解码尝试顺序：utf-8-sig 覆盖 BOM 与普通 utf-8；gb18030 是 GBK 超集（标准库自带）。
_DECODE_ORDER = ("utf-8-sig", "gb18030")


def decode_source(data: bytes) -> tuple[str, str]:
    """按固定顺序解码源文件字节；全部失败时显式报错，不猜测."""
    for encoding in _DECODE_ORDER:
        try:
            return data.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    msg = (
        "源文件编码无法识别（已尝试 utf-8-sig / gb18030）。"
        "请先用文本编辑器将源文件另存为 UTF-8 后重试。"
    )
    raise ImportSourceError(msg)
