"""派发参数守卫 —— 三条硬化必须是可执行判据（照抄 `retro_cfg` 语义）。

⛔ 范围声明（诚实登记）：本文件测 `chiyu_kernel.orchestration.dispatch_cfg` 的
   **纯策略层**（只读白名单键 / 非法即回落出厂 + 留痕 / 永不抛）。派发器本体
   (`dispatcher.py`) 与任务持久化 (`store.py`) **未迁移进内核** ⇒ 不在此伪造绿。

三条硬化（`dispatch_cfg.py` docstring）：
    ① 只读白名单键：配置里多出来的键一律忽略（配置面 ≠ 隐式接口面）
    ② 逐个校验、非法即回落出厂兜底（不抛错、不就地裁剪），被拒项**留痕**
    ③ 脏配置不崩跑批，但**必须出声** —— `rejected` 非空即与"配置没问题"外观不同
"""
from __future__ import annotations

import pytest

from chiyu_kernel.orchestration import dispatch_cfg as dc


def test_defaults_are_conservative():
    """并发上限必须保守（SKILL #6 踩坑：一次性 13 并发触发限流误报）。"""
    assert dc.DISPATCH_CFG_DEFAULTS["max_inflight"] == 2
    assert dc.DISPATCH_CFG_DEFAULTS["max_inflight"] >= 1
    assert 0.0 <= dc.DISPATCH_CFG_DEFAULTS["jitter"] <= 1.0
    assert dc.DISPATCH_CFG_DEFAULTS["lock_ttl_seconds"] > 0
    assert dc.DISPATCH_CFG_DEFAULTS["lock_wait_seconds"] >= 0
    assert dc.DISPATCH_CFG_SECTION == "orchestration"


def test_missing_section_means_factory_defaults_not_an_error():
    val, rejected = dc.read_dispatch_cfg({})
    assert val == dc.DISPATCH_CFG_DEFAULTS
    assert rejected == []
    val2, rejected2 = dc.read_dispatch_cfg(None)
    assert val2 == dc.DISPATCH_CFG_DEFAULTS and rejected2 == []


def test_unknown_keys_are_ignored():
    """① 白名单键：配置段里多出来的键不得进入生效值（也不得报错）。"""
    val, rejected = dc.read_dispatch_cfg(
        {"orchestration": {"max_inflight": 4, "who_knows": "x"}}
    )
    assert val["max_inflight"] == 4
    assert "who_knows" not in val
    assert rejected == []


def test_non_dict_section_is_reported_visibly():
    val, rejected = dc.read_dispatch_cfg({"orchestration": ["not", "a", "dict"]})
    assert val == dc.DISPATCH_CFG_DEFAULTS
    assert len(rejected) == 1 and "必须是对象" in rejected[0]["why"]


@pytest.mark.parametrize("bad,why_key", [
    (0, "max_inflight"),
    (-1, "max_inflight"),
    (True, "max_inflight"),
    ("4", "max_inflight"),
    (2.5, "max_inflight"),
])
def test_illegal_int_is_rejected_and_falls_back(bad, why_key):
    """② 非法值 ⇒ 回落出厂 + 留痕；⛔ `int(True)==1`/`int("4")==4` 式的静默通过必须被拦。"""
    val, rejected = dc.read_dispatch_cfg({"orchestration": {why_key: bad}})
    assert val[why_key] == dc.DISPATCH_CFG_DEFAULTS[why_key]
    assert [r["key"] for r in rejected] == [why_key]


@pytest.mark.parametrize("key", ["backoff_base", "jitter"])
def test_illegal_float_is_rejected(key):
    for bad in (True, "0.5", float("nan"), float("inf")):
        val, rejected = dc.read_dispatch_cfg({"orchestration": {key: bad}})
        assert val[key] == dc.DISPATCH_CFG_DEFAULTS[key]
        assert [r["key"] for r in rejected] == [key]


def test_ratio_out_of_range_is_rejected_but_int_is_accepted():
    val, rejected = dc.read_dispatch_cfg({"orchestration": {"jitter": 1.5}})
    assert val["jitter"] == dc.DISPATCH_CFG_DEFAULTS["jitter"]
    assert rejected and "0,1" in rejected[0]["why"].replace(" ", "")
    ok, rej = dc.read_dispatch_cfg({"orchestration": {"jitter": 0}})
    assert ok["jitter"] == 0 and rej == []


def test_lock_wait_may_be_zero_but_positive_keys_may_not():
    """显式的"不等待"是合法配置；把"派发器停摆"误配出来则必须拒。"""
    ok, rej = dc.read_dispatch_cfg({"orchestration": {"lock_wait_seconds": 0}})
    assert ok["lock_wait_seconds"] == 0 and rej == []
    bad, rej2 = dc.read_dispatch_cfg({"orchestration": {"lock_ttl_seconds": 0}})
    assert bad["lock_ttl_seconds"] == dc.DISPATCH_CFG_DEFAULTS["lock_ttl_seconds"]
    assert rej2 and "≥ 1" in rej2[0]["why"]


def test_negative_value_is_rejected():
    val, rejected = dc.read_dispatch_cfg({"orchestration": {"backoff_base": -0.1}})
    assert val["backoff_base"] == dc.DISPATCH_CFG_DEFAULTS["backoff_base"]
    assert rejected and "不得为负" in rejected[0]["why"]


def test_read_never_raises_even_if_the_config_object_blows_up():
    """③ 顶层 catch 是最高层防线：读配置失败**不崩跑批**，但必须出声。"""
    class _Boom:
        def get(self, *_a, **_k):
            raise RuntimeError("cfg store down")

    val, rejected = dc.read_dispatch_cfg(_Boom())
    assert val == dc.DISPATCH_CFG_DEFAULTS
    assert rejected and "读配置段失败" in rejected[0]["why"]


def test_dispatch_cfg_report_shape_and_is_default_flag():
    rep = dc.dispatch_cfg_report({})
    assert set(rep) == {"section", "effective", "defaults", "rejected", "is_default"}
    assert rep["is_default"] is True and rep["rejected"] == []
    rep2 = dc.dispatch_cfg_report({"orchestration": {"max_inflight": 5}})
    assert rep2["is_default"] is False and rep2["effective"]["max_inflight"] == 5
    assert rep2["defaults"]["max_inflight"] == 2      # 出厂值不被污染
