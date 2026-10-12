from songyan.canon import store, verify
from songyan.config import settings


def _db(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{tmp_path}/c.db")


def test_add_only_and_relation_conflict(tmp_path, monkeypatch):
    _db(tmp_path, monkeypatch)
    pid = "p"
    store.add_facts(pid, 1, [{"kind": "character", "key": "沈远", "relation": "父亲", "gender": "男"},
                             {"kind": "character", "key": "沈栖", "relation": "本人", "gender": "未知"}])
    c = store.add_facts(pid, 3, [{"kind": "character", "key": "沈拓", "relation": "父亲"},
                                 {"kind": "character", "key": "沈栖", "relation": "本人", "gender": "男"}])
    assert [x["new"] for x in c] == ["沈拓"]
    keys = {e["key"]: e for e in store.get_entries(pid, "character")}
    assert "沈拓" not in keys and keys["沈栖"]["gender"] == "男"  # gap filled, not overwritten
    c2 = store.add_facts(pid, 4, [{"kind": "character", "key": "沈栖", "gender": "女"}])
    assert c2 and store.get_entries(pid, "character")[1]["gender"] == "男"


def test_deterministic_name_and_gender(tmp_path, monkeypatch):
    _db(tmp_path, monkeypatch)
    pid = "p"
    store.add_facts(pid, 1, [{"kind": "character", "key": "沈远", "relation": "父亲", "gender": "男"},
                             {"kind": "character", "key": "沈栖", "relation": "本人", "gender": "男"}])
    vs = verify.deterministic_checks(pid, "沈栖翻开父亲沈拓的笔记。\n沈栖抬头，她看见她的手在抖，她没说话。")
    assert {v["type"] for v in vs} == {"name", "gender"}
