"""fix #3/#4: structured numeric/fact compare in code, aliases, setting interception, hard gates."""
import pytest

from songyan.canon import store, structured as S
from songyan.config import settings


@pytest.fixture(autouse=True)
def _db(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{tmp_path}/s.db")


def test_parse_numbers():
    assert S.parse_number("0.70秒") == 0.7 and S.parse_number("+0.07s") == 0.07
    assert S.parse_number("百分之四十三") == 43 and S.parse_number("100%") == 100
    assert S.numbers_differ("0.70", "+0.07") and not S.numbers_differ("12号", "十二号")


def test_within_draft_same_as_070_vs_007():
    draft = {"measures": [
        {"subject": "回声延迟", "condition": "第三坐标实测", "value": "0.70秒", "quote": "0.70秒", "same_as": 0},
        {"subject": "回声延迟修正量", "condition": "父亲笔记", "value": "+0.07s", "quote": "父亲五年前就记录过这个偏移量", "same_as": 1}]}
    v = S.compare("p", [], [], draft)
    assert len(v) == 1 and v[0]["type"] == "number"


def test_cross_chapter_43_vs_100_and_fact_carried_vs_walked():
    ms = [{"chapter": 2, "subject": "数据回传进度", "condition": "第二章锚钉回传·章末", "value": "100", "unit": "%"}]
    fs = [{"chapter": 2, "subject": "老周", "attribute": "进入接驳点的方式", "value": "自己走"}]
    draft = {"measures": [{"value": "43%", "quote": "回传43%后中断", "canon_ref": "M1"}],
             "facts": [{"ref": "F1", "value": "被背", "quote": "沈栖背着老周"}]}
    types = sorted(v["type"] for v in S.compare("p", ms, fs, draft))
    assert types == ["fact", "number"]
    ok = {"measures": [{"value": "百分之百", "canon_ref": "M1"}], "facts": [{"ref": "F1", "value": "自己走"}]}
    assert S.compare("p", ms, fs, ok) == []


def test_alias_lao_zhou_not_a_name_drift():
    store.add_facts("p", 0, [{"kind": "character", "key": "沈栖", "name": "沈栖", "relation": "本人", "gender": "男"},
                             {"kind": "character", "key": "周德望", "name": "周德望", "relation": "同事", "gender": "男"}])
    amap = S.alias_map("p")
    assert amap["老周"] == "周德望"
    from songyan.canon.verify import deterministic_checks
    assert deterministic_checks("p", "同事老周拍了拍他的肩。老周说他先走。") == []
    store.add_facts("p", 1, [{"kind": "character", "key": "周德望", "name": "周德望", "aliases": ["周工"]}])
    assert S.alias_map("p")["周工"] == "周德望"


def test_number_conflict_blocked_but_equal_value_ok():
    k = {"kind": "number", "key": "偏移|第三坐标", "subject": "偏移", "condition": "第三坐标"}
    store.add_facts("p", 1, [{**k, "value": "0.07"}])
    assert store.add_facts("p", 2, [{**k, "value": "0.070"}]) == []
    assert len(store.add_facts("p", 3, [{**k, "value": "0.70"}])) == 1


def test_setting_snapshot_screen():
    store.add_facts("p", 0, [{"kind": "character", "key": "沈远", "name": "沈远", "relation": "父亲"}])
    store.add_facts("p", 1, [{"kind": "number", "key": "回声延迟偏移|第三坐标", "subject": "回声延迟偏移",
                              "condition": "第三坐标", "value": "0.07"}])
    assert S.screen_setting("p", "父亲笔记", "父亲沈拓留下的笔记")
    assert S.screen_setting("p", "偏移", "第三坐标的回声延迟偏移为0.70秒")
    assert S.screen_setting("p", "偏移", "第三坐标的回声延迟偏移为0.07秒") == []


@pytest.mark.asyncio
async def test_hard_gate_rejects_after_retries_soft_passes(monkeypatch):
    from songyan.canon import nodes, verify
    import songyan.workflows._helpers as H

    class V:
        version_id, content = "v", "x"

    async def lv(_):
        return V()
    monkeypatch.setattr(H, "load_version", lv)
    viol = [{"type": "name", "severity": "error", "explanation": "父亲名字漂移"}]

    async def fake(*a):
        return viol
    monkeypatch.setattr(verify, "verify", fake)
    st = {"project_id": "p", "chapter_number": 3, "current_version_id": "v"}
    ds = [(await nodes.canon_verify_node(st))["_canon_decision"] for _ in range(nodes.MAX_RETRIES + 1)]
    assert ds[-1] == "reject" and ds[:-1] == ["retry"] * nodes.MAX_RETRIES
    viol[:] = [{"type": "fact", "severity": "error", "explanation": "soft"}]
    st["chapter_number"] = 4
    ds = [(await nodes.canon_verify_node(st))["_canon_decision"] for _ in range(nodes.MAX_RETRIES + 1)]
    assert ds[-1] == "pass"


def test_decimal_slip_detects_070_vs_007_only_at_anaphora():
    t = "两组数据并排。差值0.70秒。" + "填充。" * 400 + "铅笔字写着修正量+0.07s。0.07秒。父亲五年前就记录过这个偏移量。"
    v = S.decimal_slips(t)
    assert len(v) == 1 and "0.07" in v[0]["explanation"]
    assert S.decimal_slips("差值0.70秒。后来读数0.07秒，继续下降。") == []


def test_fact_families_no_paraphrase_fp():
    assert S.values_disagree("自己走", "被背出") and S.values_disagree("十二号通道", "七号通道")
    assert not S.values_disagree("已死亡", "已殉职") and not S.values_disagree("图纸", "手稿")
    assert not S.values_disagree("自己走", "未提及")


def test_compare_anaphora_code_decides():
    assert S.compare_anaphora([{"referent_value": "0.70秒", "asserted_value": "0.07s"}])
    assert not S.compare_anaphora([{"referent_value": "0.07秒", "asserted_value": "0.07s"}])


def test_opening_seam_fallback_link_43_vs_100():
    ms = [{"chapter": 2, "subject": "数据回传进度", "condition": "第二章锚钉回传·章末", "value": "100", "unit": "%"}]
    draft = {"measures": [{"subject": "数据回传进度", "value": "43%", "quote": "回传43%后中断", "canon_ref": ""}]}
    import copy
    assert [v["type"] for v in S.compare("p", ms, [], copy.deepcopy(draft), chapter=3)] == ["number"]
    assert S.compare("p", ms, [], copy.deepcopy(draft), chapter=5) == []  # only the immediate seam
