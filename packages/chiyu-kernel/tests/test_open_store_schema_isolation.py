"""open_store schema 感知守卫（Batch-2a：enterprise 自建双键注册表的根因修复）。

根因（2026-10-14 源码实测，api.py 原 `open_store`）：
    单例条件只比对 profile 身份（`_store is None or _store.profile is not profile`），
    同一 profile 第二次传不同 schema 时 **schema 参数被静默忽略**，返回第一个
    store ⇒ 进程内多租户共用一个 store 实例指向同一 schema（串库）。
    enterprise `tenant/store.py` 自建 `(profile, schema)` 双键隔离注册表的
    根因即此（见其盘点 §七.3）——修 foundation，而非保留企业副本。

判据（三条，缺一即红）：
  ① 同 profile 不同 schema ⇒ 不同 store 实例（且各带自己的 schema）；
  ② 同 (profile, schema) ⇒ 同一实例（保留"单实例"纪律，不开重复门面）；
  ③ 不同 profile 同 schema ⇒ 相互隔离（profile 不串）。
"""
from __future__ import annotations

from chiyu_kernel.api import open_store
from chiyu_kernel.contract import CORE_ROLES
from chiyu_kernel.contract.particle import ParticleTypeSet
from chiyu_kernel.contract.profile import TenantProfile


def _profile() -> TenantProfile:
    return TenantProfile(domain="demo", particle_types=ParticleTypeSet(set(CORE_ROLES)))


def test_open_store_distinguishes_schema():
    """① 同 profile 不同 schema 必须得到不同 store（否则进程内串库）。"""
    p = _profile()
    a = open_store(p, "tenant_a")
    b = open_store(p, "tenant_b")
    assert a is not b, (
        "open_store 同 profile 不同 schema 返回了同一实例 ⇒ schema 参数被静默"
        "忽略（enterprise 双键注册表所绕开的根因 bug）")
    assert a.schema == "tenant_a"
    assert b.schema == "tenant_b"


def test_open_store_singleton_per_profile_schema():
    """② 同 (profile, schema) 保留单实例语义（不开重复门面）。"""
    p = _profile()
    a = open_store(p, "tenant_a")
    assert open_store(p, "tenant_a") is a


def test_open_store_different_profiles_isolated():
    """③ 不同 profile 同 schema 相互隔离（profile 不串）。"""
    p1, p2 = _profile(), _profile()
    s1 = open_store(p1, "tenant_a")
    s2 = open_store(p2, "tenant_a")
    assert s1 is not s2
    assert s1.profile is p1
    assert s2.profile is p2
