# 决策读回契约（N4）—— 消费方读决策事实的**权威读面与统一判定式**

> 状态：**已生效**（2026-10-09，N4 落地）
> 来源：enterprise 反馈 #4（决策读回契约）；配套 `docs/sanctioned-import-surface.md`（导入面）、
> `chiyu_kernel.canary`（三判据统一判定式，N7）

---

## 1. 为什么需要

各消费方此前自造读面（自写 SQL / 自建 timeline），导致：

1. **判定口径漂移**：什么算"真落库"、什么算"链自洽"，各有一套；
2. **读面绑死实现**：表结构变化时 N 个消费方同时碎；
3. **无证伪方法**：出了争议（"到底落没落库"）没有权威判定式可对。

⇒ 本文把"读什么表、走什么 API、用什么判定式"收归基座单一事实源。

---

## 2. 存储三表（写侧唯一事实源 = `PgVectorStorePersister`）

| 表 | 关键列 | 语义 |
|---|---|---|
| `event` | `id`(=decision_id) · `ts` · `domain` · `event_type='decision'` · `stage='S5_persist'` · `subject_id` · `decision_id` · `dims` · `payload jsonb`（含 `confidence` / `redline_hit` / `content_hash` / `vector_provider` / `vector_degraded` 等） | 决策事件（写时含 G 幂等 `content_hash`） |
| `particle` | `particle_id`(=decision_id) · `type='decision'` · `layer='L1'` · `label` · `status='persisted'` · `vec` · `provider` · `ai_generated` | 决策主体锚点（向量 + provider 降级留痕） |
| `graph_edge` | `from_id` · `to_id` · `predicate` · `layer` · `serves_dims` · `edge_source`（引擎写恒 `'engine'`）· `evidence_ref` · `valid_from/until` · `weight` · `relation_confidence` | 受控边（含 7 条记忆谓词边） |

⛔ 三表**同 store 同事务边界**（N 四轨同库）：读回时若只有 event 无 particle，即为"半写"缺陷，不是落库成功。

---

## 3. 权威读面 API（全部**只读**，经 sanctioned 面可达）

| API | 出处 | 用途 |
|---|---|---|
| `decision_backlinks(...)` | `chiyu_kernel.api` | 决策回链四问：被谁引用 / 覆盖谁 / 谁覆盖我 / 源自哪条例外 |
| `timeline_view(...)` | `chiyu_kernel.api` | 时间线叙事（四源只读聚合；时间基准 `COALESCE(decided_at, created_at)`） |
| `relation_view(...)` | `chiyu_kernel.api` | 关系图谱（受控边多跳遍历，深度上限 `MAX_TRAVERSAL_HOPS`） |
| `verify_chain(...)` / `chain_hash(...)` | `chiyu_kernel.api` | 审计链复核（哈希链自洽） |
| `execute_fetch(sql, params, fetch_all=)` | `PgVectorStore` 实例方法 | 白名单化只读 SQL（禁 DROP/硬删除） |

⛔ `GraphStore` 协议**无写方法**（设计即只读派生面）；写只经 persister。

---

## 4. 统一判定式（证伪"到底落没落库"的唯一口径）

**基座统一实现**：`chiyu_kernel.canary.canary_probe(...)`（N7）。三判据：

1. **决策真落库** = `event` 行存在 **且** `particle` 行存在（成对，缺一即"半写"）；
2. **记忆网真物化** = 该决策 `edge_source='engine'` 边数 **恰好等于** 注入 references 的非空谓词数
   （多写 = 幻影边，少写 = 漏物化，`==` 是承重判据，**不许**放宽为 `>=`）；
3. **红线挡落库** = 红线决策 `persisted=False` 且被审批闸拦下（REJECTED 或 PENDING）。

消费方自造探针的判据若与本式冲突，**以本式为准**；发现本式有缺陷请提 issue 改基座，
不要在消费方侧私自放宽（判据漂移 = 探针失效的开始）。

---

## 5. 消费方接入最小范式

```python
from chiyu_kernel.api import canary_probe
from chiyu_decision.api import run_spine

report = canary_probe(
    store=my_store,                                   # PgVectorStore 或同鸭子类型
    run_decision=lambda: run_spine(..., persister=...),   # 正常决策（已接同一 store）
    decision_id="dec-1",
    references={"subject": ["doc-1"], ...},           # 记忆网供给
    run_redline_decision=lambda: run_spine(..., redline_items=("...",)),
)
assert report.ok, report.details
```
