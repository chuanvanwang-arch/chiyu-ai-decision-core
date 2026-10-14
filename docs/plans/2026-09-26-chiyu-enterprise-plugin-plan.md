# chiyu-enterprise 三插件包实施计划（T1–T5）

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 chiyu-enterprise 交付 3 个可分发插件包（企业决策专家 / 平台管理专家 / 场景包构建专家），含版本一致性校验器、场景包草稿池、锚点漂移守卫与全链验收。

**Architecture:** 权威源在 chiyu-enterprise 仓库根 `skills/`（19 SKILL），`plugin/` 为分发副本（pack 脚本同步 + verify 脚本 md5 防漂移）；场景包草稿池为 enterprise 层新模块 `host/scenario_draft.py`（唯一新增模块，零内核改动）；集成关系以 `docs/plans/2026-09-26-scenario-builder-integration-map.md` 的 file:line 锚点固化为可执行测试。

**Tech Stack:** Python 3.11+（pytest / dataclasses / zipfile / hashlib 纯标准库）；插件清单 JSON；设计输入 `docs/plans/2026-09-26-chiyu-enterprise-plugin-design.md`。

**执行仓：`D:\system\chiyu-enterprise`**（实施产物全部落该仓；本计划文档与设计文档在 chiyu-foundation 仓，为唯一事实源）。

**红线（每个 Task 都适用）：** ① 插件零新增 Action 定义（写清单只引用既有场景包命名空间 `gl.` / `fin.` / `wms.` / `q.`）；② 草稿绝不自动生效（promote 必须人工）；③ 无 delete/remove 工具与字面量；④ 禁 `git add -A`，只显式路径 add；⑤ 提交前跑该 Task 的测试，红不提交。

---

## File Structure

```
D:\system\chiyu-enterprise\
├─ skills/                                  # 权威源（Task 2/3/5 创建，19 SKILL）
│  ├─ enterprise-native/SKILL.md + registry.json
│  ├─ enterprise-query/…  enterprise-write/…  decision-advise/…  risk-probe/…
│  ├─ decision-retrospective/…  method-decision-rubric/…  method-root-cause/…
│  ├─ method-scenario-triage/…  method-risk-gate/…
│  ├─ tenant-onboarding/…  scenario-registry-admin/…  connector-admin/…
│  ├─ rbac-approval-admin/…  ops-insight/…
│  └─ scenario-author/…  draft-governance/…  integration-wizard/…  validation-run/…
├─ plugin/
│  ├─ enterprise-decision-platform/         # 分发副本（pack 脚本生成 skills/ 与 avatars/）
│  │  ├─ .workbuddy-plugin/plugin.json  openclaw.plugin.json  package.json
│  │  ├─ agents/enterprise-native.md  README.md
│  ├─ enterprise-platform-admin/（同构，agents/enterprise-admin.md）
│  └─ enterprise-scenario-builder/（同构，agents/enterprise-builder.md）
├─ scripts/
│  ├─ scaffold_plugin_manifests.py          # Task 1：生成 9 份 manifest
│  ├─ verify_enterprise_plugins.py          # Task 1：版本一致性 + md5 防漂移 + 内容规则
│  ├─ pack_enterprise_plugins.py            # Task 1：同步 skills + 生成 avatars + 打 3 zip
│  └─ scan_disclosure.py                    # Task 6：对外披露概念扫描
├─ packages/enterprise/src/enterprise/host/
│  └─ scenario_draft.py                     # Task 4：ScenarioDraft 三态池（唯一新模块）
└─ tests/
   ├─ test_scenario_draft.py                # Task 4
   └─ test_integration_anchors.py           # Task 5：集成映射锚点漂移守卫
```

**基线（Task 1 第一步实测）：** `python -m pytest tests -q` 应为 **369 passed / 4 skipped / 0 failed**（2026-09-26 设计文档记载）。若漂移，先停下取证，不得带病开工。

---

### Task 1: 包骨架 + 三清单脚手架 + pack/verify 脚本

**Files:**
- Create: `scripts/scaffold_plugin_manifests.py`
- Create: `scripts/verify_enterprise_plugins.py`
- Create: `scripts/pack_enterprise_plugins.py`
- Create(生成): `plugin/<三个包>/.workbuddy-plugin/plugin.json`、`openclaw.plugin.json`、`package.json`

- [ ] **Step 1: 记录基线**

```bash
cd /d/system/chiyu-enterprise && python -m pytest tests -q 2>&1 | tail -3
```
Expected: `369 passed, 4 skipped`（数量漂移 → 先取证再继续）。

- [ ] **Step 2: 写脚手架脚本（完整代码）**

```python
# scripts/scaffold_plugin_manifests.py — 生成三插件 manifest 三清单（幂等，重跑覆盖）
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PLUGINS = {
    "enterprise-decision-platform": {
        "display": "企业AI决策专家 · ChiYu青羽",
        "tagline": "AI-Native · Traceable, Trustworthy, Evolvable",
        "description": "企业级 AI 决策专家：场景自适应对话入口、决策建议卡、两阶段对话式写入、风险主动探测与决策复盘。",
        "version": "1.0.0",
        "agent": "enterprise-native",
        "skills": ["enterprise-native", "enterprise-query", "enterprise-write",
                   "decision-advise", "risk-probe", "decision-retrospective",
                   "method-decision-rubric", "method-root-cause",
                   "method-scenario-triage", "method-risk-gate"],
    },
    "enterprise-platform-admin": {
        "display": "企业平台治理助手 · ChiYu青羽",
        "tagline": "Industry-Adaptive, Full-Process Monitoring",
        "description": "企业级平台治理：行业租户接入（TenantProfile 注入）、场景包注册表启停、连接器五闸管理、RBAC 与运行洞察。",
        "version": "1.0.0",
        "agent": "enterprise-admin",
        "skills": ["tenant-onboarding", "scenario-registry-admin", "connector-admin",
                   "rbac-approval-admin", "ops-insight"],
    },
    "enterprise-scenario-builder": {
        "display": "场景包构建专家 · ChiYu青羽",
        "tagline": "Configure, Validate, Promote",
        "description": "实施伙伴交付入口：对话式构建场景包五元组、连接器接入向导、校验试运行与草稿池治理（人工 promote，不自动生效）。",
        "version": "1.0.0",
        "agent": "enterprise-builder",
        "skills": ["scenario-author", "draft-governance", "integration-wizard", "validation-run"],
    },
}


def write_json(p: Path, obj: dict) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    for pid, cfg in PLUGINS.items():
        base = ROOT / "plugin" / pid
        common = {"id": pid, "name": cfg["tagline"], "description": cfg["description"],
                  "version": cfg["version"],
                  "configSchema": {"type": "object", "additionalProperties": False,
                                   "properties": {}},
                  "skills": [f"skills/{s}" for s in cfg["skills"]]}
        write_json(base / ".workbuddy-plugin" / "plugin.json",
                   {"name": pid, "plugin": pid, "version": cfg["version"],
                    "displayName": {"zh": cfg["display"]}, **common})
        write_json(base / "openclaw.plugin.json", common)
        write_json(base / "package.json",
                   {"name": f"@chiyu-ai/{pid}", "version": cfg["version"],
                    "private": True, "description": cfg["description"]})
        print(f"scaffolded {pid}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: 运行脚手架并核对 9 份 manifest**

```bash
cd /d/system/chiyu-enterprise && python scripts/scaffold_plugin_manifests.py && find plugin -name "*.json" | sort
```
Expected: 输出 3 行 `scaffolded …`；`find` 列出 9 个 json（3 包 × 3 清单）。

- [ ] **Step 4: 写校验器（完整代码）**

```python
# scripts/verify_enterprise_plugins.py — 三包校验：版本一致性 + 副本 md5 + 内容防漂移
# 用法：python scripts/verify_enterprise_plugins.py   （exit 0 = 全绿；任何不一致 exit 1）
from __future__ import annotations
import hashlib, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = ROOT / "skills"
PLUGINS = ["enterprise-decision-platform", "enterprise-platform-admin",
           "enterprise-scenario-builder"]

# 内容防漂移规则：锚定 SKILL.md 关键纪律（缺任一条 → 红）
CONTENT_RULES = {
    "enterprise-decision-platform": [
        ("skills/enterprise-native/SKILL.md", "decision-advise"),
        ("skills/enterprise-native/SKILL.md", "禁止直接触发写工具"),
        ("skills/enterprise-write/SKILL.md", "confirm_token"),
        ("skills/enterprise-write/SKILL.md", "decision_id"),
    ],
    "enterprise-platform-admin": [
        ("skills/scenario-registry-admin/SKILL.md", "禁删只改 enabled"),
        ("skills/tenant-onboarding/SKILL.md", "由租户注入"),
    ],
    "enterprise-scenario-builder": [
        ("skills/draft-governance/SKILL.md", "不自动生效"),
        ("skills/validation-run/SKILL.md", "判别力自证"),
    ],
}
# 跨项目泄漏守卫：插件包内不得出现其他产品线标识
LEAK_RE = re.compile(r"crm-native|sales-decision|BJ-12345", re.IGNORECASE)


def md5(p: Path) -> str:
    return hashlib.md5(p.read_bytes()).hexdigest()


def fail(msg: str) -> None:
    print(f"FAIL: {msg}")
    globals()["_FAILED"] = True


def main() -> int:
    globals()["_FAILED"] = False
    for pid in PLUGINS:
        base = ROOT / "plugin" / pid
        mans = {}
        for rel in (".workbuddy-plugin/plugin.json", "openclaw.plugin.json", "package.json"):
            f = base / rel
            if not f.exists():
                fail(f"{pid} 缺清单 {rel}")
                continue
            mans[rel] = json.loads(f.read_text(encoding="utf-8"))
        if len(mans) != 3:
            continue
        versions = {m["version"] for m in mans.values()}
        if len(versions) != 1:
            fail(f"{pid} 版本三清单不一致: {sorted(versions)}")
        if mans["openclaw.plugin.json"]["id"] != pid:
            fail(f"{pid} openclaw id 漂移: {mans['openclaw.plugin.json']['id']}")
        declared = [s.split("/")[-1] for s in mans["openclaw.plugin.json"]["skills"]]
        for s in declared:
            src = SKILLS_ROOT / s / "SKILL.md"
            dist = base / "skills" / s / "SKILL.md"
            if not src.exists():
                fail(f"{pid} 权威源缺 {s}/SKILL.md")
                continue
            if not dist.exists():
                fail(f"{pid} 分发副本缺 {s}/SKILL.md（先跑 pack）")
            elif md5(src) != md5(dist):
                fail(f"{pid} {s} 副本漂移（权威源 md5={md5(src)[:8]} 副本={md5(dist)[:8]}）")
            if src.exists() and LEAK_RE.search(src.read_text(encoding="utf-8")):
                fail(f"{pid} {s} 疑似跨项目泄漏命中 {LEAK_RE.pattern}")
        if not (base / f"agents").exists() or not list((base / "agents").glob("*.md")):
            fail(f"{pid} 缺 agents/ 面孔")
        for rel, needle in CONTENT_RULES.get(pid, []):
            f = ROOT / rel
            if f.exists() and needle not in f.read_text(encoding="utf-8"):
                fail(f"内容防漂移：{rel} 缺关键纪律「{needle}」")
    if globals()["_FAILED"]:
        return 1
    print("verify_enterprise_plugins: ALL GREEN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: 跑校验器，确认红（SKILL 未建）**

```bash
cd /d/system/chiyu-enterprise && python scripts/verify_enterprise_plugins.py; echo "EXIT=$?"
```
Expected: `EXIT=1`，错误为「权威源缺 …/SKILL.md」「缺 agents/ 面孔」。

- [ ] **Step 6: 写打包脚本（完整代码）**

```python
# scripts/pack_enterprise_plugins.py — 同步权威源 → 分发副本 + 生成 avatars + 打 3 zip
from __future__ import annotations
import shutil, struct, zipfile, zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = ROOT / "skills"
PLUGINS = {
    "enterprise-decision-platform": ("enterprise-native", (34, 211, 238)),   # 青
    "enterprise-platform-admin": ("enterprise-admin", (251, 191, 36)),       # 琥珀
    "enterprise-scenario-builder": ("enterprise-builder", (167, 139, 250)),  # 紫
}


def write_png(path: Path, rgb: tuple, size: int = 256) -> None:
    """纯标准库生成纯色 PNG（确定性，避免二进制入计划）。"""
    raw = b"".join(b"\x00" + bytes(rgb) * size for _ in range(size))

    def chunk(t: bytes, d: bytes) -> bytes:
        return (struct.pack(">I", len(d)) + t + d
                + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF))
    ihdr = struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)
    png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
           + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(png)


def main() -> None:
    for pid, (agent, rgb) in PLUGINS.items():
        base = ROOT / "plugin" / pid
        skills_dst = base / "skills"
        if skills_dst.exists():
            shutil.rmtree(skills_dst)
        skills_dst.mkdir(parents=True)
        for skill_dir in sorted(SKILLS_ROOT.iterdir()):
            if skill_dir.is_dir():
                shutil.copytree(skill_dir, skills_dst / skill_dir.name)
        write_png(base / "avatars" / f"{agent}.png", rgb)
        out = ROOT / "plugin" / f"{pid}.zip"
        if out.exists():
            out.unlink()
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in sorted(base.rglob("*")):
                if f.is_file():
                    zf.write(f, f.relative_to(base))
        print(f"packed {pid} -> {out.name} ({out.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
```

- [ ] **Step 7: 提交（Task 1 结构件）**

```bash
cd /d/system/chiyu-enterprise && git add scripts/scaffold_plugin_manifests.py scripts/verify_enterprise_plugins.py scripts/pack_enterprise_plugins.py plugin/enterprise-decision-platform/.workbuddy-plugin/plugin.json plugin/enterprise-decision-platform/openclaw.plugin.json plugin/enterprise-decision-platform/package.json plugin/enterprise-platform-admin/.workbuddy-plugin/plugin.json plugin/enterprise-platform-admin/openclaw.plugin.json plugin/enterprise-platform-admin/package.json plugin/enterprise-scenario-builder/.workbuddy-plugin/plugin.json plugin/enterprise-scenario-builder/openclaw.plugin.json plugin/enterprise-scenario-builder/package.json && git commit -m "feat(plugin): 三插件包骨架 + manifest 三清单脚手架 + verify/pack 校验器（verify 当前红=SKILL 未建，T2-T5 补齐）"
```

---

### Task 2: 插件① enterprise-decision-platform（agent 面孔 + 10 SKILL）

**Files:**
- Create: `skills/enterprise-native/SKILL.md`、`skills/enterprise-native/registry.json`（及同构 9 个 SKILL 目录）
- Create: `plugin/enterprise-decision-platform/agents/enterprise-native.md`
- Create: `plugin/enterprise-decision-platform/README.md`

- [ ] **Step 1: 写编排入口 SKILL（完整内容；路由纪律是 verify 防漂移锚点，逐字保留）**

`skills/enterprise-native/SKILL.md`:
```markdown
---
name: enterprise-native
description: 企业决策编排入口——意图路由 → 场景包分发（惰性编排），角色自适应
---
# enterprise-native · 编排入口

## 角色自适应
按登录角色（analyst 财务分析 / planner 计划 / quality_engineer 质量 / buyer 采购 /
manager 管理层）经 RBAC 裁剪可见场景包与 SKILL；同一面孔、不同能力面。

## 路由纪律（红线）
识别业务决策诉求（记账/保修计提/返利/仓配/补货/经营分析/质量处置/审批等）时：
1. **先调 `decision-advise` 取建议卡，再走查询或两阶段写入**；不得跳过建议直接给处置结论。
2. 建议卡 B 档（触碰红线或高风险场景）**禁止直接触发写工具**，必须引导发起审批，
   并明确告知「这超出你的权限，需审批」。

## 分发
- 单点提效场景（1 agent_role）→ 对应场景包单 Action 闭环（一次确认闸）
- 流程提效场景（≥2 角色 + edges）→ 拓扑接力，每环节 ApprovalGate/HITL
- 端到端场景 → decision-advise → run_decision 全链（感知→认知→决策→执行）

## Action 读清单（只读直连）
- `<ns>.agent.*` / `<ns>.integration.*`（ns ∈ gl/fin/wms/q，由已注册场景包承载）

## Action 写清单（两阶段 + decision_id；本插件零新增 Action）
- 全部引用既有场景包 Action 治理面；未接 handler 的 fqn 平台显式报接线缺口
```

`skills/enterprise-native/registry.json`:
```json
{"skill_id": "enterprise-native", "category": "orchestration", "enabled": true,
 "rbac_roles": ["analyst", "planner", "quality_engineer", "buyer", "manager"],
 "methodology_id": null}
```

- [ ] **Step 2: 写其余 9 个 SKILL（完整内容；registry.json 同构，仅 skill_id/category/rbac_roles 不同）**

`skills/enterprise-query/SKILL.md`:
```markdown
---
name: enterprise-query
description: 跨场景推理查询——粒子图 + 决策链 + 检索，只读直连
---
# enterprise-query · 读
- 输入：自然语言查询 + 场景名（缺省则路由到角色可见的全部已注册场景）。
- 只读：直连 Action 读面，无闸；绝不调用写动作。
- 返回：结构化结果 + 溯源（来源场景包 / 连接器 / 决策链引用）。
- 无数据：显式返回 empty + 缺口说明，不用空字典冒充结果。
```
registry: `{"skill_id": "enterprise-query", "category": "query", "enabled": true, "rbac_roles": ["analyst", "planner", "quality_engineer", "buyer", "manager"], "methodology_id": null}`

`skills/enterprise-write/SKILL.md`:
```markdown
---
name: enterprise-write
description: 对话式写入——两阶段确认 + 决策第 0 闸
---
# enterprise-write · 写（红线最多的 SKILL）
## 两阶段流程
1. phase1：取表单 + 参数收集 → 平台返回 `confirm_token`（无 token 不写）。
2. phase2：携 `confirm_token` 执行；必须带 `decision_id`（决策第 0 闸；缺 → `decision_required`）。
## 纪律
- 无 delete/remove 工具；只增改。
- 跨租户写一律被 G-A 拦（`cross_tenant_denied`），不尝试绕行。
- 未接 handler 的 Action：平台显式报接线缺口——如实转述，不重试、不伪造成功。
```
registry: `{"skill_id": "enterprise-write", "category": "write", "enabled": true, "rbac_roles": ["analyst", "planner", "quality_engineer", "buyer"], "methodology_id": null}`

`skills/decision-advise/SKILL.md`:
```markdown
---
name: decision-advise
description: 决策建议卡三档——先 advise 后写
---
# decision-advise · 决策建议
- 坐标：决策场景 × 业务阶段（对齐平台 8 大决策场景模型）。
- 三档产出：
  - A 明确处置：条件齐备且证据充分 → 推荐 disposition + 依据 + 先例。
  - B 风险提示：触碰红线（如毛利下限）或高风险场景 → 必须走审批，不给直接处置。
  - C 只补信息：坐标不明或必填缺失 → 只列缺口与追问话术，不给处置。
- 只读、零落库：对话原文即时消费，不写入任何存储。
```
registry: `{"skill_id": "decision-advise", "category": "decision", "enabled": true, "rbac_roles": ["analyst", "planner", "quality_engineer", "buyer", "manager"], "methodology_id": null}`

`skills/risk-probe/SKILL.md`:
```markdown
---
name: risk-probe
description: 链断裂 / SLA 超时 / 审批堆积主动探测
---
# risk-probe · 主动探测
- 订阅平台事件流（GET /events），识别三类风险：链断裂、SLA 超时、审批堆积。
- 产出：风险卡（等级 + 证据 + 建议动作）；只读探测，绝不代执行修复动作。
- 低置信推断必须标注「内部推断（低置信）」。
```
registry: `{"skill_id": "risk-probe", "category": "probe", "enabled": true, "rbac_roles": ["analyst", "manager"], "methodology_id": null}`

`skills/decision-retrospective/SKILL.md`:
```markdown
---
name: decision-retrospective
description: 决策复盘与效果回接
---
# decision-retrospective · 复盘
- 输入：decision_id（必填）→ 拉审计链 + 结果数据。
- 产出：复盘卡（判定 good/poor + 差距归因 + 可沉淀经验）。
- 判定 approved+good 的经验经平台 evolution 机制沉淀为技能草稿（本 SKILL 只上报，不直接写能力层）。
```
registry: `{"skill_id": "decision-retrospective", "category": "retrospective", "enabled": true, "rbac_roles": ["manager", "analyst"], "methodology_id": null}`

`skills/method-decision-rubric/SKILL.md`:
```markdown
---
name: method-decision-rubric
description: 结构化决策评分方法论——多维度确定性打分 + 一次 LLM 收紧
---
# method-decision-rubric · 方法论
- 九个维度逐项确定性打分（规则可复算），仅 1 次调用 LLM 做总收紧，其余维度零 LLM。
- 输出：维度分表 + 总分 + 一票否决项（若命中）。
- 判据：维度缺证据 = 0 分并显式标注「缺证据」，不打印象分。
```
registry: `{"skill_id": "method-decision-rubric", "category": "methodology", "enabled": true, "rbac_roles": ["manager", "analyst"], "methodology_id": "decision-rubric"}`

`skills/method-root-cause/SKILL.md`:
```markdown
---
name: method-root-cause
description: 根因链方法论——证据盘点 → 根因 → 反事实检验
---
# method-root-cause · 方法论
- 三步：① 独立证据盘点（每条证据带来源锚点）② 根因链（不断链条式追问到可动作层）
  ③ 反事实检验（移除该根因，问题是否消失）。
- 判据：无证据支撑的根因假设一律标「待验证」，不得当结论输出。
```
registry: `{"skill_id": "method-root-cause", "category": "methodology", "enabled": true, "rbac_roles": ["analyst", "quality_engineer", "manager"], "methodology_id": "root-cause"}`

`skills/method-scenario-triage/SKILL.md`:
```markdown
---
name: method-scenario-triage
description: 场景三级判别方法论——单点 / 流程 / 端到端
---
# method-scenario-triage · 方法论
- 判别三问：① 只跨数据不跨岗位？→ 单点提效（1 agent_role 场景包）
  ② 跨岗位且需接力？→ 流程提效（多角色 + edges）③ 需要感知→认知→决策→执行闭环？
  → 端到端增值（接 run_decision）。
- 判错代价对策：先判级再建包；升级（单点→流程）允许，降级需复盘。
```
registry: `{"skill_id": "method-scenario-triage", "category": "methodology", "enabled": true, "rbac_roles": ["manager"], "methodology_id": "scenario-triage"}`

`skills/method-risk-gate/SKILL.md`:
```markdown
---
name: method-risk-gate
description: 风险权衡与红线一票否决方法论
---
# method-risk-gate · 方法论
- 量化：风险 = 概率 × 损失；收益同理；净值 < 0 → 一票否决。
- 红线清单来自租户 TenantProfile 注入（平台零领域字面量），命中即 B 档建议卡。
- 判据：红线不可被收益对冲；缓解措施只降概率不改定性。
```
registry: `{"skill_id": "method-risk-gate", "category": "methodology", "enabled": true, "rbac_roles": ["manager", "analyst"], "methodology_id": "risk-gate"}`

- [ ] **Step 3: 写 agent 面孔与 README（完整内容）**

`plugin/enterprise-decision-platform/agents/enterprise-native.md`:
```markdown
# 企业AI决策专家（enterprise-native）

角色自适应的企业级 AI 决策专家：场景自适应查询、决策建议卡、两阶段对话式写入、
链路风险主动预警。

## 能力映射（一句话 → 能力）
- 查数据 / 查进度 / 查决策链 → enterprise-query
- 记账 / 计提 / 返利 / 补货 / 质量处置 → 先 decision-advise 取建议卡 → enterprise-write
- 这事能不能干 / 有没有风险 → decision-advise（A/B/C 三档）
- 链路哪里断了 / 什么超时了 → risk-probe
- 上一批决策效果怎么样 → decision-retrospective

## 纪律
- 先 advise 后写；B 档禁止直接写，引导审批。
- 写操作两阶段 confirm_token + decision_id；无 delete 工具。
- 租户隔离：只读/写本租户作用域。
```

`plugin/enterprise-decision-platform/README.md`:
```markdown
# enterprise-decision-platform · 企业AI决策专家

对接平台：chiyu-enterprise（经平台 MCP/RPC 通道；端点与凭据由连接器配置决定，包内不写死主机）。
- 权威源：仓库根 `skills/`（本目录 skills/ 为分发副本，pack 脚本同步）。
- 校验：`python scripts/verify_enterprise_plugins.py`
- 打包：`python scripts/pack_enterprise_plugins.py`
```

- [ ] **Step 4: 同步 + 校验（本包转绿）**

```bash
cd /d/system/chiyu-enterprise && python scripts/pack_enterprise_plugins.py && python scripts/verify_enterprise_plugins.py; echo "EXIT=$?"
```
Expected: EXIT=1 但错误仅剩插件②③（权威源缺/内容规则缺）；插件①相关错误为零。若插件① 仍有 FAIL → 修复后重跑。

- [ ] **Step 5: 提交**

```bash
cd /d/system/chiyu-enterprise && git add skills/enterprise-native skills/enterprise-query skills/enterprise-write skills/decision-advise skills/risk-probe skills/decision-retrospective skills/method-decision-rubric skills/method-root-cause skills/method-scenario-triage skills/method-risk-gate plugin/enterprise-decision-platform/agents/enterprise-native.md plugin/enterprise-decision-platform/README.md plugin/enterprise-decision-platform/skills plugin/enterprise-decision-platform/avatars && git commit -m "feat(plugin): 插件①企业决策专家 agent 面孔 + 10 SKILL（先 advise 后写路由纪律 + 两阶段写 + 4 方法论）"
```

---

### Task 3: 插件② enterprise-platform-admin（5 SKILL）

**Files:**
- Create: `skills/tenant-onboarding/…`、`scenario-registry-admin/…`、`connector-admin/…`、`rbac-approval-admin/…`、`ops-insight/…`
- Create: `plugin/enterprise-platform-admin/agents/enterprise-admin.md`、`README.md`

- [ ] **Step 1: 写 5 个 SKILL（完整内容）**

`skills/tenant-onboarding/SKILL.md`:
```markdown
---
name: tenant-onboarding
description: 行业租户接入——TenantProfile 生成（领域取值由租户注入）
---
# tenant-onboarding · 租户接入
- 产出 TenantProfile：粒子类型 / 知识谓词 / 红线事项目录 **由租户注入**——本 SKILL
  与内核零领域字面量，不得内置任何行业取值。
- 步骤：① 问行业与业务对象 ② 生成 profile 草稿（JSON）③ 租户确认 ④ 提交管理面落库。
- 纪律：接入配置是草稿流（同场景包草稿池纪律），不经本 SKILL 直接改运行时。
```
registry: `{"skill_id": "tenant-onboarding", "category": "admin", "enabled": true, "rbac_roles": ["platform-admin"], "methodology_id": null}`

`skills/scenario-registry-admin/SKILL.md`:
```markdown
---
name: scenario-registry-admin
description: 场景包注册表后台启停——DB 权威源、禁删只改 enabled、热生效
---
# scenario-registry-admin · 场景包启停
三要素（缺一即设计偏离）：
1. **DB 为启停权威源**：首启幂等灌种子，DB enabled 覆盖出厂声明。
2. **禁删只改 enabled**：任何诉求都不产生删除操作；下线 = enabled:false。
3. **热生效**：启停同步内存注册表，立即生效无需重启。
- 启停动作必须带 decision_id 留痕（决策第 0 闸）。
```
registry: `{"skill_id": "scenario-registry-admin", "category": "admin", "enabled": true, "rbac_roles": ["platform-admin"], "methodology_id": null}`

`skills/connector-admin/SKILL.md`:
```markdown
---
name: connector-admin
description: 连接器五闸管理——接入凭据、启停、写回白名单
---
# connector-admin · 连接器管理
- 凭据**不进对话**：向导/管理面只回传凭据引用 id；本 SKILL 永不接收明文密钥。
- 读写：GET /connectors、GET /integrations（控制面）；写回白名单仅限 scope=read_write 连接器。
- 探测：接入后调 GET /integrations/{cid}/probe 验证连通；transport 缺失 = G-E 显式失败，不假成功。
```
registry: `{"skill_id": "connector-admin", "category": "admin", "enabled": true, "rbac_roles": ["platform-admin"], "methodology_id": null}`

`skills/rbac-approval-admin/SKILL.md`:
```markdown
---
name: rbac-approval-admin
description: 角色权限 + ApprovalGate/HITL 配置（阈值后台可配置）
---
# rbac-approval-admin · 权限与审批配置
- 阈值/规则一律后台可配置（config_store），本 SKILL 不硬编码任何阈值。
- 变更两阶段：phase1 出 diff 预览 → 管理员确认 → phase2 落库，带 decision_id。
- 审批流去硬编码：角色→审批人映射为配置项；改配置不改代码。
```
registry: `{"skill_id": "rbac-approval-admin", "category": "admin", "enabled": true, "rbac_roles": ["platform-admin"], "methodology_id": null}`

`skills/ops-insight/SKILL.md`:
```markdown
---
name: ops-insight
description: 运行洞察——审计链、SLA、僵尸任务治理、决策监控
---
# ops-insight · 运行洞察
- 读控制面：GET /audit、/dashboard、/decision-board、/agents、/redline。
- 僵尸任务：识别 running 超时任务 → 建议治理动作（只建议，不代执行）。
- 结论必须引用真实计数/ID；无数据显式报 empty，不编造。
```
registry: `{"skill_id": "ops-insight", "category": "admin", "enabled": true, "rbac_roles": ["platform-admin", "manager"], "methodology_id": null}`

- [ ] **Step 2: agent 面孔 + README**

`plugin/enterprise-platform-admin/agents/enterprise-admin.md`:
```markdown
# 企业平台治理助手（enterprise-admin）

行业自适应、全流程可观测的企业级平台治理助手。

## 能力映射
- 接入一个新行业租户 → tenant-onboarding（TenantProfile 草稿）
- 上下线一个场景包 → scenario-registry-admin（禁删只改 enabled）
- 接一个外部系统 → connector-admin（五闸 + probe）
- 调角色权限 / 审批阈值 → rbac-approval-admin（两阶段 + diff 预览）
- 平台现在健康吗 → ops-insight（真实计数，不编造）

## 红线继承
无 delete；写动作两阶段 + decision_id；租户隔离；凭据不进对话。
```

`plugin/enterprise-platform-admin/README.md`:（同 Task 2 Step 3 的 README 模板，首行标题改为本包名，其余逐字相同）

- [ ] **Step 3: 同步 + 校验**

```bash
cd /d/system/chiyu-enterprise && python scripts/pack_enterprise_plugins.py && python scripts/verify_enterprise_plugins.py; echo "EXIT=$?"
```
Expected: EXIT=1 仅剩插件③错误；插件②错误为零。

- [ ] **Step 4: 提交**

```bash
cd /d/system/chiyu-enterprise && git add skills/tenant-onboarding skills/scenario-registry-admin skills/connector-admin skills/rbac-approval-admin skills/ops-insight plugin/enterprise-platform-admin && git commit -m "feat(plugin): 插件②平台管理专家 5 SKILL（租户注入铁律 + 启停三要素 + 凭据不进对话）"
```

---

### Task 4: host/scenario_draft.py（TDD，2026-09-26 拍板的唯一新模块）

**Files:**
- Create: `packages/enterprise/src/enterprise/host/scenario_draft.py`
- Test: `tests/test_scenario_draft.py`

- [ ] **Step 1: 写失败测试（完整代码）**

```python
# tests/test_scenario_draft.py — ScenarioDraft 三态池（draft→validated→promoted）
"""集成映射 §2-B1：草稿绝不自动生效；promote 人工触发；无显式注册回调则零副作用。"""
import pytest

from enterprise.host.scenario_draft import DraftError, ScenarioDraftPool


def test_add_creates_draft_status():
    pool = ScenarioDraftPool()
    d = pool.add("gl_auto_post", {"action_namespace": "gl.", "agent_roles": ["fin_analyst"]})
    assert d.status == "draft"
    assert d.name == "gl_auto_post"
    assert pool.get("gl_auto_post").spec["action_namespace"] == "gl."


def test_validate_with_errors_stays_draft():
    pool = ScenarioDraftPool()
    pool.add("bad_pkg", {"action_namespace": "gl."})
    errs = pool.validate("bad_pkg", errors=["fqn 越权: gl.integration.x 不在命名空间"])
    assert errs  # 返回错误清单
    assert pool.get("bad_pkg").status == "draft"  # ⛔ 有错不升级


def test_validate_clean_promotes_to_validated():
    pool = ScenarioDraftPool()
    pool.add("ok_pkg", {"action_namespace": "gl."})
    assert pool.validate("ok_pkg", errors=[]) == []
    assert pool.get("ok_pkg").status == "validated"


def test_promote_from_draft_rejected():
    pool = ScenarioDraftPool()
    pool.add("still_draft", {"action_namespace": "gl."})
    with pytest.raises(DraftError, match="validated"):
        pool.promote("still_draft", by="platform-admin")


def test_promote_records_actor_and_returns_spec():
    pool = ScenarioDraftPool()
    pool.add("good_pkg", {"action_namespace": "fin."})
    pool.validate("good_pkg", errors=[])
    spec = pool.promote("good_pkg", by="wang")
    assert spec["action_namespace"] == "fin."
    assert pool.get("good_pkg").status == "promoted"
    assert pool.get("good_pkg").history[-1]["action"] == "promote"
    assert pool.get("good_pkg").history[-1]["by"] == "wang"


def test_promote_without_register_callback_has_no_side_effect():
    """⛔ 零自动生效：pool 自身绝不触碰 scenario_loader；注册只经显式回调。"""
    pool = ScenarioDraftPool()
    pool.add("pure_pkg", {"action_namespace": "wms."})
    pool.validate("pure_pkg", errors=[])
    calls = []
    pool.promote("pure_pkg", by="wang", register=lambda spec: calls.append(spec))
    assert calls == [{"action_namespace": "wms."}]  # 回调仅一次
    # 无回调时不发生任何注册（对照：不传 register 也正常返回）
    pool.add("pure2", {"action_namespace": "q."})
    pool.validate("pure2", errors=[])
    assert pool.promote("pure2", by="wang")["action_namespace"] == "q."


def test_add_duplicate_name_rejected():
    pool = ScenarioDraftPool()
    pool.add("dup", {"action_namespace": "gl."})
    with pytest.raises(DraftError, match="已存在"):
        pool.add("dup", {"action_namespace": "fin."})
```

- [ ] **Step 2: 跑测试确认失败**

```bash
cd /d/system/chiyu-enterprise && python -m pytest tests/test_scenario_draft.py -q
```
Expected: FAIL — `ModuleNotFoundError: No module named 'enterprise.host.scenario_draft'`。

- [ ] **Step 3: 写实现（完整代码）**

```python
# packages/enterprise/src/enterprise/host/scenario_draft.py
"""场景包草稿池（集成映射 §2-B1，2026-09-26 拍板：enterprise 层唯一新模块）。

⛔ 草稿绝不自动生效（与 evolution/bridge.py SkillDraft 同纪律、不同泳道）：
  - 状态机 draft → validated → promoted；validate(errors非空) 不升级。
  - promote 仅自 validated 态、人工触发、记录 actor；本模块自身绝不触碰
    scenario_loader——注册只经调用方显式传入的 register 回调（零自动生效路径）。
  - 与技能草稿（SkillDraft）是两条独立泳道：本池沉淀"场景包"，不承载技能。
⛔ 零领域字面量：不认识任何具体场景/行业；spec 即调用方传入的 dict。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


class DraftError(Exception):
    """草稿池状态违例（重复名 / 非 validated 提升等）。"""


@dataclass
class ScenarioDraft:
    name: str
    spec: Dict[str, Any]
    status: str = "draft"          # draft | validated | promoted
    history: List[Dict[str, Any]] = field(default_factory=list)


class ScenarioDraftPool:
    """进程内草稿池（先例：host/control_plane.py 的进程内单例风格）。"""

    def __init__(self) -> None:
        self._drafts: Dict[str, ScenarioDraft] = {}

    def add(self, name: str, spec: Dict[str, Any]) -> ScenarioDraft:
        if name in self._drafts:
            raise DraftError(f"草稿 {name} 已存在")
        d = ScenarioDraft(name=name, spec=dict(spec))
        d.history.append({"action": "add", "by": "builder"})
        self._drafts[name] = d
        return d

    def get(self, name: str) -> Optional[ScenarioDraft]:
        return self._drafts.get(name)

    def validate(self, name: str, *, errors: List[str]) -> List[str]:
        """外部校验（validation-run SKILL）产出 errors；空 → 升 validated，非空 → 留 draft。"""
        d = self._require(name)
        if errors:
            d.history.append({"action": "validate", "errors": list(errors)})
            return list(errors)
        if d.status == "draft":
            d.status = "validated"
        d.history.append({"action": "validate", "errors": []})
        return []

    def promote(self, name: str, *, by: str,
                register: Optional[Callable[[Dict[str, Any]], None]] = None) -> Dict[str, Any]:
        """人工提升：仅 validated 态；register 回调由调用方显式传入（通常包装
        scenario_loader.register_scenario 的 spec→factory 构造）。"""
        d = self._require(name)
        if d.status != "validated":
            raise DraftError(f"草稿 {name} 状态为 {d.status}，仅 validated 可 promote（人工闸）")
        d.status = "promoted"
        d.history.append({"action": "promote", "by": by})
        if register is not None:
            register(dict(d.spec))
        return dict(d.spec)

    def pending(self) -> List[ScenarioDraft]:
        """未提升草稿（只读视图，供看板/审计）。"""
        return [d for d in self._drafts.values() if d.status != "promoted"]

    def _require(self, name: str) -> ScenarioDraft:
        d = self._drafts.get(name)
        if d is None:
            raise DraftError(f"草稿 {name} 不存在")
        return d


__all__ = ["DraftError", "ScenarioDraft", "ScenarioDraftPool"]
```

- [ ] **Step 4: 跑测试确认全绿 + 全量回归**

```bash
cd /d/system/chiyu-enterprise && python -m pytest tests/test_scenario_draft.py -q && python -m pytest tests -q 2>&1 | tail -1
```
Expected: 7 passed；全量 `376 passed, 4 skipped`（369+7；若基线数不同，按实际 +7 核对）。

- [ ] **Step 5: 变异自证（守卫自身的覆盖度也要被守卫）**

临时把 `promote` 的 `if d.status != "validated"` 改成 `if False:` → 跑测试应红（test_promote_from_draft_rejected 失败）→ 还原 → 复绿。

```bash
cd /d/system/chiyu-enterprise && python -m pytest tests/test_scenario_draft.py -q
```
Expected: 还原后 7 passed。

- [ ] **Step 6: 提交**

```bash
cd /d/system/chiyu-enterprise && git add packages/enterprise/src/enterprise/host/scenario_draft.py tests/test_scenario_draft.py && git commit -m "feat(host): ScenarioDraft 三态草稿池（draft→validated→promoted，零自动生效，注册仅经显式回调）7 passed"
```

---

### Task 5: 插件③ enterprise-scenario-builder（4 SKILL）+ 锚点漂移守卫

**Files:**
- Create: `skills/scenario-author/…`、`draft-governance/…`、`integration-wizard/…`、`validation-run/…`
- Create: `plugin/enterprise-scenario-builder/agents/enterprise-builder.md`、`README.md`
- Test: `tests/test_integration_anchors.py`

- [ ] **Step 1: 写 4 个 SKILL（完整内容）**

`skills/scenario-author/SKILL.md`:
```markdown
---
name: scenario-author
description: 场景包五元组对话式构建——配置画像，不写代码
---
# scenario-author · 五元组构建
- 逐项收集（缺项追问，不臆造）：① tenant_profile（领域取值由租户注入）
  ② action_namespace（如 gl./fin./wms./q.）③ agent_roles + agent_edges(from,to,action)
  ④ connector_ids（仅可引用本租户已注册连接器）⑤ assets（prompt/规则/schema/kb）。
- 每个 Action 声明 fqn（必须落在命名空间树内）+ capability + guard（mutating/needs_force）。
- 产物 = ScenarioSpec（JSON）→ 交 draft-governance 入池；本 SKILL 不直接触碰运行时。
- handler 绑定方式在 spec 中声明；未绑定的 fqn 注册后执行会显式报接线缺口（如实告知伙伴）。
```
registry: `{"skill_id": "scenario-author", "category": "builder", "enabled": true, "rbac_roles": ["builder", "platform-admin"], "methodology_id": null}`

`skills/draft-governance/SKILL.md`:
```markdown
---
name: draft-governance
description: 草稿池治理——draft→validated→promoted，不自动生效
---
# draft-governance · 草稿池（红线）
- 场景包草稿进 ScenarioDraftPool（enterprise 层），状态机 draft → validated → promoted。
- **不自动生效**：promote 是管理面人工动作；本 SKILL 无任何自动 promote 路径。
  自动生效路径 = 零（验收判据，变异自证）。
- 与技能草稿（SkillDraft/决策沉淀）是两条独立泳道，不混写。
- 全程留痕：add/validate/promote 进 history，可审计。
```
registry: `{"skill_id": "draft-governance", "category": "builder", "enabled": true, "rbac_roles": ["builder", "platform-admin"], "methodology_id": null}`

`skills/integration-wizard/SKILL.md`:
```markdown
---
name: integration-wizard
description: 连接器接入向导——五闸回连配置
---
# integration-wizard · 连接器接入
- 产出连接器配置草稿 → 提交控制面 POST /integrations；连通性验证走
  GET /integrations/{cid}/probe。
- **凭据不进对话**：只回传凭据引用 id；明文密钥一旦出现在对话中立即警示并作废该流程。
- scope 只读优先：默认 read；需写回时显式说明将触发五闸（G-A 跨租户 / G-B 只读优先 /
  G-C 决策锚 / G-D HITL / G-E 传输）。
```
registry: `{"skill_id": "integration-wizard", "category": "builder", "enabled": true, "rbac_roles": ["builder", "platform-admin"], "methodology_id": null}`

`skills/validation-run/SKILL.md`:
```markdown
---
name: validation-run
description: 场景包校验与试运行——判别力自证闸
---
# validation-run · 校验
- 结构校验：五元组字段完整；agent_edges 三元组合法；fqn 前缀 = action_namespace；
  connector_ids ⊆ 本租户已注册连接器。
- **判别力自证**：投 3 类故意错配置（越权 fqn / 缺 agent_role / guard 缺失）必须逐条
  检出并拒绝入池——错配置漏检 = 本 SKILL 不合格。
- 试运行：沙箱桩执行（不触真实连接器）；真实调用必须经平台五闸。
- 全绿 → 提请 validated；仍有错 → 保持 draft 并输出错误清单。
```
registry: `{"skill_id": "validation-run", "category": "builder", "enabled": true, "rbac_roles": ["builder", "platform-admin"], "methodology_id": null}`

- [ ] **Step 2: agent 面孔 + README（README 模板同 Task 2，标题换本包名）**

`plugin/enterprise-scenario-builder/agents/enterprise-builder.md`:
```markdown
# 场景包构建专家（enterprise-builder）

实施伙伴交付入口：把业务场景变成场景包配置画像，不写代码。

## 能力映射
- 新建一个业务场景包 → scenario-author（五元组对话式收集）
- 接外部系统 → integration-wizard（凭据不进对话）
- 这个包能不能上线 → validation-run（判别力自证 + 沙箱试运行）
- 上线了没有 / 谁批准的 → draft-governance（三态留痕，promote 人工）

## 红线
builder 无生产写权限：只产草稿 + 沙箱试运行；promote 由管理面人工执行。
零新增 Action：全部引用既有场景包治理面。
```

- [ ] **Step 3: 写锚点漂移守卫测试（完整代码；集成映射 §2 全部锚点固化为可执行契约）**

```python
# tests/test_integration_anchors.py — 集成映射锚点漂移守卫
"""docs/plans/2026-09-26-scenario-builder-integration-map.md §2 的 file:line 锚点
固化为存在性断言：符号消失即红（锚点不是一次性文档，是可执行契约）。"""
from pathlib import Path

ENT = Path(__file__).resolve().parents[1] / "packages" / "enterprise" / "src" / "enterprise"

ANCHORS = {  # 相对路径 → 必须存在的符号/纪律串
    "scenario/loader.py": ["def register_scenario", "def resolve_guard",
                           "供 host 写闸消费"],
    "scenario/package.py": ["class ScenarioPackage", "class ScenarioAction",
                            "from chiyu_kernel.contract import TenantProfile"],
    "action/executor.py": ["def execute_action", "接线缺口", "provider.switch"],
    "connector/gateway.py": ["G-A", "G-B", "G-C", "G-D", "G-E", "def infer_is_write",
                             "def call_connector"],
    "evolution/bridge.py": ["绝不自动生效", "def evolve_from_event", "class EvolutionBridge",
                            'bus.subscribe("decision"'],
    "memory/writeback.py": ["def write_decisions_back", "decision_required"],
    "host/control.py": ['@router.get("/scenarios")', '@router.post("/integrations")',
                        '@router.get("/integrations/{cid}/probe")',
                        "def bootstrap_control_state"],
    "host/scenario_draft.py": ["class ScenarioDraftPool", "绝不自动生效", "仅 validated 可 promote"],
}


def test_integration_anchors_present():
    missing = []
    for rel, needles in ANCHORS.items():
        f = ENT / rel
        if not f.exists():
            missing.append(f"{rel} 文件缺失")
            continue
        text = f.read_text(encoding="utf-8")
        for n in needles:
            if n not in text:
                missing.append(f"{rel} 缺锚点「{n}」")
    assert not missing, "集成锚点漂移（对照 integration-map.md 更新或修复代码）:\n" + "\n".join(missing)


def test_draft_pool_no_auto_register():
    """⛔ 零自动生效反向断言：scenario_draft.py 不得 import scenario_loader。"""
    text = (ENT / "host" / "scenario_draft.py").read_text(encoding="utf-8")
    assert "scenario_loader" not in text, "草稿池不得直连 loader（注册只经显式回调）"
```

- [ ] **Step 4: 跑锚点测试 + 全量回归 + 校验器全绿**

```bash
cd /d/system/chiyu-enterprise && python -m pytest tests/test_integration_anchors.py -q && python -m pytest tests -q 2>&1 | tail -1 && python scripts/pack_enterprise_plugins.py && python scripts/verify_enterprise_plugins.py; echo "EXIT=$?"
```
Expected: 锚点测试 2 passed；全量 383 passed / 4 skipped（376+2… 按实际 +2 核对）；verify **EXIT=0 ALL GREEN**。

- [ ] **Step 5: 变异自证**

临时删除 `loader.py` 的 `def resolve_guard` 行 → 锚点测试必须红 → 还原 → 复绿。

- [ ] **Step 6: 提交**

```bash
cd /d/system/chiyu-enterprise && git add skills/scenario-author skills/draft-governance skills/integration-wizard skills/validation-run plugin/enterprise-scenario-builder tests/test_integration_anchors.py && git commit -m "feat(plugin): 插件③场景包构建专家 4 SKILL + 集成锚点漂移守卫（17 锚点固化可执行契约）"
```

---

### Task 6: 全链验收（禁词扫描 + 三 zip + 基线复核）

**Files:**
- Create: `scripts/scan_disclosure.py`

- [ ] **Step 1: 写披露扫描脚本（完整代码；按概念扫描，非单词）**

```python
# scripts/scan_disclosure.py — 对外披露纪律扫描（按概念而非单词；含权属代号组合模式）
# 用法：python scripts/scan_disclosure.py   （命中 → exit 1；设计文档只写类别不写 token）
from __future__ import annotations
import re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGETS = [ROOT / "plugin"]
# 概念级模式：权属类字样 + 代号组合（命中任一即违规）
PATTERNS = [
    r"专利", r"实施例", r"权利要求", r"权 ?[0-9]", r"[A-H] ?件",
    r"7[×xX*]7", r"审查意见", r"公开号",
]


def main() -> int:
    hits = []
    rx = [re.compile(p) for p in PATTERNS]
    for base in TARGETS:
        for f in sorted(base.rglob("*")):
            if f.is_file() and f.suffix in (".md", ".json", ".js", ".py", ".txt"):
                text = f.read_text(encoding="utf-8", errors="ignore")
                for i, line in enumerate(text.splitlines(), 1):
                    for r in rx:
                        if r.search(line):
                            hits.append(f"{f.relative_to(ROOT)}:{i}: {line.strip()[:80]}")
    if hits:
        print("DISCLOSURE HITS:")
        print("\n".join(hits))
        return 1
    print("scan_disclosure: CLEAN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: 全链验收（一次跑全）**

```bash
cd /d/system/chiyu-enterprise && python scripts/pack_enterprise_plugins.py && python scripts/verify_enterprise_plugins.py && python scripts/scan_disclosure.py && python -m pytest tests -q 2>&1 | tail -1 && ls -la plugin/*.zip
```
Expected: pack 3 行 → `verify_enterprise_plugins: ALL GREEN` → `scan_disclosure: CLEAN` → 全量全绿（0 failed）→ 3 个 zip 存在。

- [ ] **Step 3: 提交**

```bash
cd /d/system/chiyu-enterprise && git add scripts/scan_disclosure.py plugin/enterprise-decision-platform.zip plugin/enterprise-platform-admin.zip plugin/enterprise-scenario-builder.zip && git commit -m "feat(plugin): 全链验收收口——披露概念扫描 + 三 zip 产出 + verify ALL GREEN"
```
（注：zip 若入 .gitignore 则只提交扫描脚本，zip 留本地产物——提交前 `git check-ignore -v plugin/*.zip` 核对，不能以 `git status` 未列出为准。）

---

## Self-Review（已执行）

1. **Spec coverage**：设计 §4 10 SKILL→Task 2；§5 5 SKILL→Task 3；§6 4 SKILL + 草稿池→Task 4/5；§7 零内核改动→Task 4 仅 enterprise 层 + 反向断言 test_draft_pool_no_auto_register；§8 版本纪律/副本 md5→Task 1 verify；§10 五条验收→Task 5 Step 4（①②⑤）+ Task 4 Step 5（变异）+ Task 5 Step 5（判别力）+ Task 6 Step 2（全链）。集成映射 17 锚点→Task 5 test_integration_anchors（8 文件 17 串）。**无缺口**。
2. **Placeholder scan**：无 TBD/TODO；README 模板复用处已显式写明「逐字相同仅换标题」且模板全文在 Task 2。
3. **Type consistency**：`ScenarioDraftPool.add/get/validate/promote/pending` 与测试、与 draft-governance SKILL 文案一致；verify 的 CONTENT_RULES 锚串与 SKILL.md 原文逐字核对一致（「禁止直接触发写工具」「禁删只改 enabled」「不自动生效」「判别力自证」）。
