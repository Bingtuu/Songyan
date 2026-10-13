"""v4: mutable vs immutable numeric canon."""
import pytest

from songyan.canon import store, structured as S
from songyan.config import settings


@pytest.fixture(autouse=True)
def _db(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{tmp_path}/m.db")


def test_default_mutable_by_type():
    assert S.default_mutable("渗漏频率周期", "113号测点·章末")
    assert S.default_mutable("当铺账面余额", "")
    assert not S.default_mutable("案发日期", "", proposed=True)  # immutable keyword wins over LLM
    assert not S.default_mutable("死者年龄", "1931年")
    assert not S.default_mutable("门牌", "霞飞路")
    assert S.default_mutable("某量", "", proposed=True) and not S.default_mutable("某量", "")


def test_v3_fp_cycle_83_to_116_is_accepted():
    ms = [{"chapter": 2, "subject": "渗漏频率周期", "condition": "113号测点·章末", "value": "1.7", "mutable": True},
          {"chapter": 2, "subject": "渗漏频率强度", "condition": "章末", "value": "1.4", "mutable": True}]
    d = {"measures": [
        {"subject": "渗漏频率周期", "value": "11.6秒", "quote": "渗漏频率周期从8.3秒继续拉长至11.6秒", "canon_ref": "M1"},
        {"subject": "渗漏频率强度", "value": "0.08", "quote": "强度衰减至0.08", "canon_ref": "M2"}]}
    assert S.compare("p", ms, [], d, chapter=3) == []


def test_immutable_stays_hard_and_seam_without_narration_stays_hard():
    ms = [{"chapter": 1, "subject": "回声延迟偏移", "condition": "父亲笔记·历史", "value": "0.07", "mutable": False}]
    d = {"measures": [{"subject": "回声延迟偏移", "value": "0.7", "quote": "笔记写着0.7", "canon_ref": "M1"}]}
    assert [v["type"] for v in S.compare("p", ms, [], d, chapter=2)] == ["number"]
    import copy
    seam = [{"chapter": 2, "subject": "数据回传进度", "condition": "章末", "value": "100", "mutable": True}]
    d2 = {"measures": [{"subject": "数据回传进度", "value": "43%", "quote": "回传43%后中断", "canon_ref": ""}]}
    assert [v["type"] for v in S.compare("p", seam, [], copy.deepcopy(d2), chapter=3)] == ["number"]
    d3 = {"measures": [{"subject": "数据回传进度", "value": "43%", "quote": "进度降到43%", "canon_ref": ""}]}
    assert S.compare("p", seam, [], d3, chapter=3) == []


def test_store_mutable_updates_latest_no_conflict_immutable_conflicts():
    k = {"kind": "number", "key": "周期|测点", "subject": "周期", "condition": "测点"}
    store.add_facts("p", 1, [{**k, "value": "1.7", "mutable": True}])
    assert store.add_facts("p", 2, [{**k, "value": "8.3", "mutable": True}]) == []
    e = [x for x in store.get_entries("p", "number")][0]
    assert e["value"] == "8.3" and e["history"] == ["1.7"] and e["chapter"] == 2
    j = {"kind": "number", "key": "案发日期|", "subject": "案发日期", "condition": "", "mutable": False}
    store.add_facts("p", 1, [{**j, "value": "3"}])
    assert len(store.add_facts("p", 2, [{**j, "value": "5"}])) == 1
