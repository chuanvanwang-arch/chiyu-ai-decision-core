# F-A 需求输入：消费方侧 import 门禁（C1 实现）· CRM → foundation 交接

> 日期：2026-10-13
> 性质：**需求输入件**（非实现）——由 CRM 消费方提出契约要求，foundation 据此在 `tools/` 建正式件
> 关联：`docs/sanctioned-import-surface.md`（sanctioned 面唯一事实源）、`tools/check_import_surface.py`（贵仓既有同分发门禁，F-A 的派生起点）、`docs/2026-10-13-crm-response-foundation第四轮反馈.md`（C1 接受为 P1 候选）、`docs/2026-10-13-decision-facade-audit-c1-p2.md`（CRM 侧 F-A/F-B/F-C 整族决策）

---

## 0. 结论（先给结论）

- **F-A = C1 消费方侧 import 门禁的正式实现**：foundation 在 `tools/` 建 `facade_usage_audit.py`，从既有 `tools/check_import_surface.py` **派生**，**复用同一份 `SANCTIONED` / `CONFLICTING_NAMES` 单一事实源**，新增 `--consumer-root` 参数扫描消费方仓。
- **缺口事实**（trust-but-verify）：贵仓 `check_import_surface.py` 的 `SCAN_ROOTS` 仅覆盖 `packages/{chiyu-kernel,chiyu-decision,chiyu-portal}/src` + `examples/`（脚本行 40–45），**消费方仓（CRM/APS/enterprise）零覆盖**；而 CRM 侧已实测存在 off-facade 导入（F-C 修复 4 符号），证明消费方侧确有门禁需求。
- **本件是需求契约**：定义 F-A 的 CLI、判定口径、输出格式、与 C1 的关系；**不替贵仓写实现代码**，不替消费方改码。

---

## 1. 背景与触发

| 项 | 说明 |
|---|---|
| 现有贵仓门禁 | `tools/check_import_surface.py` 守"跨分发 import 必须落 sanctioned 面"，但 `SCAN_ROOTS` 不含任何消费方仓 ⇒ 消费方零覆盖（第四轮回执 §2.2 边界发现） |
| 消费方实证 | CRM `scripts/foundation_graph_write_stdio.py` 曾用 `chiyu_kernel.mcpserver` / `chiyu_kernel.graph.mcp` 两条 off-facade 导入（F-C 已于 2026-10-13 修复为单一 `chiyu_kernel.api`）；说明消费方侧确会发生 off-facade，需门禁防回归 |
| C1 候选状态 | foundation 第四轮回执已接受 C1 为 P1 候选；F-A 即 C1 的实现载体 |
| 选项②落点 | 用户拍板（`docs/2026-10-13-decision-facade-audit-c1-p2.md`）：落点 = 贵仓另起 `tools/` 正式件、兼作 C1 门禁，非移 enterprise 仓 |

---

## 2. 功能契约（CLI）

```
python tools/facade_usage_audit.py --consumer-root <path> [--baseline <json>] [--json] [--deep] [--verbose]
```

| 参数 | 必填 | 语义 |
|---|---|---|
| `--consumer-root` | 是 | 消费方仓根（如 `D:/system/CRM-ai-native`）；递归扫全部 `*.py` |
| `--baseline` | 否 | 过渡期豁免清单 JSON 路径（见 §3.3）；缺省 = 零豁免 |
| `--json` | 否 | 机器可读输出（供消费方 F-B 固化证据命令，见 §5） |
| `--deep` | 否 | 深度校验：对 sanctioned 路径但符号不在 `__all__` 的导入，连 venv 解析 `api.__all__` 复核（可选，默认关） |
| `--verbose` | 否 | 打印扫描统计与豁免项（⛔ 豁免必须可见，静默豁免 = 假绿） |
| 退出码 | — | `0` = 无违规；`1` = 存在 off-facade 违规 |

---

## 3. 扫描与判定口径（复用单一事实源，**不得另起一份允许清单**）

### 3.1 sanctioned 面（直接复用 `check_import_surface.py` 的 `SANCTIONED` 元组）
与 `docs/sanctioned-import-surface.md` §2 一致，唯一事实源：
`chiyu_kernel.api`、`chiyu_kernel.contract`（含子树）、`chiyu_kernel.approval`、`chiyu_decision.api`、`chiyu_portal.api`。

### 3.2 消费方判定规则
- 消费方仓**无自有 `chiyu_*` 分发包** ⇒ 其所有 `chiyu_kernel.*` / `chiyu_decision.*` / `chiyu_portal.*` 导入**全部视为跨分发消费导入**，必须命中 §3.1 中某个 sanctioned 前缀（相等或为其子树）。
- **违规** = `from chiyu_kernel.<X> import ...` 其中 `<X> != 'api'` 且 `<X>` 不是 `contract`/`approval` 子树，例如 `chiyu_kernel.mcpserver` / `chiyu_kernel.graph.mcp` / `chiyu_kernel.store.pg_store` 等。
- ⛔ `chiyu_kernel.api` 不得反含 `run_spine`（刻意设计，见 sanctioned 文档 §2 注）；决策脊柱请走 `chiyu_decision.api`。

### 3.3 过渡期豁免（baseline）
- 迁移期消费方可能暂有已确权但未迁的路径；以 `--baseline <json>` 提供显式豁免清单，**每条须带理由**，脚本输出须打印命中数（与贵仓 `check_import_surface.py` 的 `EXEMPT_PATHS` 纪律同构）。
- **F-C 已修复后，CRM 预期零豁免**（4 符号均已改走 `chiyu_kernel.api`）；若 CRM F-B 初跑仍有违规，先修码而非加豁免。

### 3.4 易冲突名提示（复用 `CONFLICTING_NAMES`）
复用 `check_import_surface.py` 的 `CONFLICTING_NAMES` 清单，对消费方**扁平导入**易冲突名（如 `register_scenario`、`Particle`）给**警告级提示（不阻断）**，建议改命名空间引用（`import chiyu_kernel.api as api; api.<name>`）。⛔ 清单非空是判别力前提，不得清空。

---

## 4. 输出格式（JSON schema，供 CRM F-B 固化证据命令）

`--json` 输出结构（消费方 F-B 将断言 `violations == []`）：

```json
{
  "consumer_root": "/abs/path/to/CRM-ai-native",
  "scanned_files": 3,
  "imports_seen": 6,
  "violations": [
    {
      "file": "scripts/foundation_graph_write_stdio.py",
      "line": 51,
      "import": "from chiyu_kernel.mcpserver import StdioTransport, allow_principals",
      "symbols": ["StdioTransport", "allow_principals"],
      "suggested": "from chiyu_kernel.api import StdioTransport, allow_principals"
    }
  ],
  "conflict_warnings": [
    {"file": "...", "line": 0, "name": "register_scenario",
     "hint": "跨仓同名异义(H1)，建议 api.register_scenario 或全限定引用"}
  ],
  "ok": false
}
```

---

## 5. CRM 侧 F-B 证据命令（固化点）

F-B（CRM 接入门禁）将把以下命令固化为 CRM 侧守卫测试的输出来源（F-C 已先行，预期零违规）：

```bash
python tools/facade_usage_audit.py --consumer-root "$CRM_ROOT" --json > crm-facade-audit.json
# CRM 守卫断言 crm-facade-audit.json 的 violations == []
```

> 注：F-A 建件完成后，CRM 侧可新增 `test/scripts/facade-audit.test.js` 调用该命令并断言零违规；该测试是 F-B 的"门禁接入"载体。

---

## 6. 回归样例（4 个 off-facade 符号，F-C 已修复，作门禁判据验证素材）

以下符号**均在 `chiyu_kernel.api.__all__` 内再导出**（实取确认），故 off-facade 修复的"正确归处"是 `chiyu_kernel.api`：

| 符号 | 原 off-facade 路径（已修） | 正确路径 |
|---|---|---|
| `StdioTransport` | `chiyu_kernel.mcpserver` | `chiyu_kernel.api` |
| `allow_principals` | `chiyu_kernel.mcpserver` | `chiyu_kernel.api` |
| `build_graph_write_server` | `chiyu_kernel.graph.mcp` | `chiyu_kernel.api` |
| `open_graph_write_store` | `chiyu_kernel.graph.mcp` | `chiyu_kernel.api` |

F-A 门禁须能对上述 4 例判违规并给出 `suggested` 修正路径（即验证门禁判别力的素材）。

---

## 7. 与 C1 / `check_import_surface.py` 的关系（DRY，单一事实源）

- **C1 = F-A**：本件即 C1 的需求契约；F-A 建成即 C1 落地。
- **复用而非复制**：F-A 应 `import` 贵仓 `check_import_surface.py` 的 `SANCTIONED` 与 `CONFLICTING_NAMES`（或从中读取），**不得另起一份允许清单**——否则两门禁（贵仓侧 / 消费方侧）会对称漂移（判据 #14/#23）。
- **互补**：`check_facade_coverage.py` 守"能力是否漏出"；`check_import_surface.py` 守"贵仓内跨分发方向"；**F-A 守"消费方→贵仓的导入方向"**。三者互补，不可互相替代。

---

## 8. 不在本件范围内

- ❌ 不替贵仓写 `facade_usage_audit.py` 实现（本件为需求，实现由贵仓工程）。
- ❌ 不替消费方改码（F-C 已修 CRM 侧 off-facade；其余消费方由各自仓按 F-A 门禁自查）。
- ❌ 不定义"领域尺度/阈值/场景键入底座"（扩展建议 X-C3 已明确不建议，与 X3 对齐）。

---

## 9. 验收（贵仓建件后，CRM 侧可验）

1. 对 CRM 仓跑 `--consumer-root`：F-C 修复后须 `violations == []`、`ok == true`；
2. 对含 off-facade 的样例仓（或临时注入 4 符号旧路径）须判违规并给 `suggested`；
3. 门禁与 `check_import_surface.py` 复用同一 `SANCTIONED`（改 sanctioned 文档须两处同步生效）。

— CRM-ai-native 仓提出 · 落 foundation 仓 docs/（2026-10-13）
