"""v3: bridge obligation + bridged-opening gate, tightened numeric checks, 8d06cf3 interrupt loop."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from songyan.canon import bridge, structured as S

ES = {"location": "测绘局走廊出口外", "situation": "陆秉安排明日复测",
      "pending": ["明日七点C-7分区复测", "备份文件夹“渗”已被删除"]}


def test_bridge_obligation_added_once():
    g = SimpleNamespace(obligations=["其他义务"])
    g = bridge.apply_to_goal(g, ES)
    g = bridge.apply_to_goal(g, ES)
    assert sum("开头衔接" in o for o in g.obligations) == 1 and "测绘局走廊出口外" in g.obligations[0]


def test_bridged_opening_accepts_time_jump_to_pending_scene():
    # v2 v-2-19 / v-2-15 style: explicit next-morning time + the agreed C-7 re-survey
    assert bridge.bridged_opening(ES, "沈栖把测绘仪从肩上卸下来的时候，腕表显示六点五十七分。C-7分区的入口闸门还未完全升起")
    assert bridge.bridged_opening(ES, "沈栖调整扫描频段。C-7分区的入口在七点十二分打开。")
    assert bridge.bridged_opening(ES, "走廊出口外的风裹着细砂，打在沈栖后颈上。")


def test_unbridged_opening_still_goes_to_judge():
    # v2 v-2-27: already inside C-7 with no time marker / transition
    assert not bridge.bridged_opening(ES, "测绘仪背带勒进肩胛骨时，沈栖正用牙咬住手套。他蹲在暗红色苔藓边缘")
    assert not bridge.bridged_opening(ES, "沈栖蹲在C-7分区界碑内侧，将探针从苔藓样本边缘撤回。")


def test_v2_anaphora_false_positives_gone():
    assert S.anaphora_sites("一百一十三这个数字不对。") == []
    assert S.anaphora_sites("他把这个数字记在记录板边缘的空白处。") == []
    assert S.anaphora_sites("读数跃至1.7Hz——和昨天老周消失前记录到的数字一模一样。") == []
    assert S.anaphora_sites("父亲五年前就记录过这个偏移量。")  # named quantity still counts


def test_v2_decimal_slip_false_positive_gone_true_positive_kept():
    fp = "规则检测仪读数0.3米处。" + "填充。" * 50 + "频率偏移+0.03单位，持续时间1.7秒。这个频率和昨天一样。"
    assert S.decimal_slips(fp) == []
    tp = "差值0.70秒。" + "填充。" * 300 + "修正量+0.07s。0.07秒。父亲五年前就记录过这个偏移量。"
    assert len(S.decimal_slips(tp)) == 1


def test_coordinates_not_paired_with_distance():
    d = {"measures": [
        {"subject": "位置", "value": "距离C-7分区边界正北方向七百三十米", "quote": "七百三十米"},
        {"subject": "坐标", "value": "北纬三十一度零七分", "quote": "北纬三十一度零七分", "same_as": 1}]}
    assert S.compare("p", [], [], d) == []


