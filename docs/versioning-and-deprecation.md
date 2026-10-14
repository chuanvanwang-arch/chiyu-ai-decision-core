# 版本策略与 deprecation 政策

> 状态：**已生效**（2026-10-09，N1 落地）
> 配套：`CHANGELOG.md`（变更记录）· `chiyu_kernel.version`（机检出口）· `docs/sanctioned-import-surface.md`（导入面）

---

## 1. 三个版本号，各管一件事

| 版本 | 出口 | 何时升 | 消费方用法 |
|---|---|---|---|
| **分发包版本** | `from chiyu_kernel.api import __version__` | 每次发布（含新增能力） | 版本钉、构建期 `assert 版本 >= 基线` |
| **门面 API 版本** | `API_VERSION` / `api_version()` | 门面导出面发生**不兼容**变化时升主版本 | 判断"我的调用面是否被破坏" |
| **L0 契约版本** | `CONTRACT_VERSION` / `contract_version()` | 契约常量取值或形状变化时升级 | 判断"我的 TenantProfile / 谓词表是否要改" |

⛔ 三者**不可互相替代**：分发包版本会频繁变（新增能力也升），若用它判断兼容性会
误报"破坏性变更"；反之只用门面版本则无法做版本钉。

`__version__` **动态取已安装分发包的元数据**（未安装时回退 `PACKAGE_VERSION`）。
理由：写成常量会出现"包已升版、门面仍报旧版"的静默漂移 —— 而版本钉的意义正是**与分发物一致**。

---

## 2. SemVer 口径

- **MAJOR（主版本）**：导出面**移除**符号、改变函数签名语义、契约常量取值变化。
- **MINOR（次版本）**：新增能力 / 新增导出（严格加法）。
- **PATCH**：内部修复，不改变导出面与语义。

> ⚠️ `experimental` 能力不享受本承诺：其形态可能在 MINOR 内变化。
> 稳定子集与实验子集的划界见 `docs/capability-matrix.md`，机检入口 `capability_status(name)`。

---

## 3. Deprecation 政策（**先 warn 一版，再移除一版**）

1. **标记期**（≥1 个 MINOR 版本）：旧名保留可用，登记进 `DEPRECATIONS`（`旧名 -> 新名`，
   机检入口 `deprecations()`），`CHANGELOG` 标注 `[Deprecated]`。
2. **移除期**（下一个 MAJOR）：旧名移除，`CHANGELOG` 标注 `[BREAKING]`。
3. ⛔ **禁止**在同一版本内"标记即移除"。也**禁止**静默移除 —— 未登记进 `DEPRECATIONS`
   的移除视为缺陷。

**当前弃用清单**

| 旧名 | 建议新名 | 起始版本 | 移除版本 |
|---|---|---|---|
| `TIER_FTS_VECTOR` | `VTIER_FTS_VECTOR` | 0.1.0（2026-10-09） | 待定（≥ 下一 MAJOR） |
| `TIER_VECTOR` | `VTIER_VECTOR` | 0.1.0（2026-10-09） | 待定 |
| `TIER_FTS` | `VTIER_FTS` | 0.1.0（2026-10-09） | 待定 |
| `TIER_NONE` | `VTIER_NONE` | 0.1.0（2026-10-09） | 待定 |
| `TIER_ORDER` | `VTIER_ORDER` | 0.1.0（2026-10-09） | 待定 |

> 分族理由：向量降级族与自进化风险族（`TIER_AUTO/GUARDED/FORBIDDEN`）同处门面命名空间
> 却语义无关，共用 `TIER_` 前缀曾迫使消费方写长注释警告"不得简写"（消费方替基座打补丁）。

---

## 4. 消费方版本钉建议

```python
from chiyu_kernel.api import __version__, api_version, capability_status

assert tuple(int(x) for x in __version__.split(".")) >= (0, 1, 0), "底座版本过低"
assert api_version().split(".")[0] == "1", "门面主版本不兼容"
if capability_status("memory") == "experimental":
    ...  # ⛔ 不得把 memory 写进硬验收判据
```

---

## 5. 守卫

- `tests/test_version_and_capabilities.py`：能力清单与层枚举机械比对、状态值合法、门面导出齐备；
- `tests/test_facade_import_vs_all.py`：门面 import 了却没进 `__all__` 即红；
- `tests/test_version_consistency`（本节新增）：`__version__` 与 `pyproject.toml` 一致，
  且 `DEPRECATIONS` 的旧名**仍可导入**（未提前移除）。

---

## 6. 启动期能力自检（G5，2026-10-09 回应 enterprise 第二轮）

消费方在建链/启动期断言**能力存在且状态符合期望**（比版本钉更精确），
机检入口 = 门面 `require_capabilities(required: Mapping[str, str]) -> None`。

### 推荐断言语态

- **stable 必需**（缺失或非 stable ⇒ `RuntimeError`，启动失败）：生产路径依赖的能力；
- **experimental 显式豁免**：消费方明确接受实验态才检 `== "experimental"`（检到 stable 反而报错，作为"状态翻转哨兵"）；
- ⛔ 禁 `hasattr` 嗅探、禁"读注释推断状态"——只认 `capabilities()` / `require_capabilities()`。

### 推荐必检键清单（按消费形态）

| 消费形态 | 必检键（均 stable） |
|---|---|
| 接决策脊柱（enterprise T8 等） | `decision` / `persist` / `approval` / `store` / `contract` / `canary` |
| 走记忆网（实验态） | 上行 + `{"memory": "experimental"}`（哨兵式断言：翻转即启动红，强迫人工复核） |
| 仅内核 L0/L1 | `contract` / `vector` / `store` |

### 示例

```python
from chiyu_kernel.api import require_capabilities
require_capabilities({"decision": "stable", "persist": "stable",
                      "approval": "stable", "store": "stable"})
```

守卫：`tests/test_capability_gate.py`（6 项，含 memory 哨兵与 mismatch 聚合）。
