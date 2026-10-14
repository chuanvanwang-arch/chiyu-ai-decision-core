# N3 E2E 独立复验留痕（verify_element_matrix_e2e.py 原始输出）

- 性质：foundation 增补改善要求 **N3（P1）**留痕补证 —— "生产接线同面"证据的原始输出存档
- 复验时间：2026-10-12 16:28（GMT+8）
- 环境：本仓 `scripts/verify_element_matrix_e2e.py`；`CHIYU_DB_DSN=postgresql://chiyu@127.0.0.1:5432/chiyu_test`（本地便携 PG，⛔ 非生产）；`CHIYU_DB_SCHEMA=public`；`CHIYU_TOKEN_SIGNING_KEY=ops-local-key`；解释器 = `.workbuddy/binaries/python/envs/default`（含 psycopg2）
- 结果：**16 PASS / 0 FAIL**（RC=0），夹具自清复原（CLEAN）

## 原始输出（逐行原样，未剪辑）

```text
PASS | 真库 config_store 可达 | prior={'value': {'value': {'value': 'M1', 'decision_id': None}, 'decision_id': None}, 'decision_id': None}
PASS | ① dict 形态（config.html 表单）⇒ M3 生效 | v=M3 src=config
PASS | ② 裸串形态（apply 通道）⇒ M4 生效 | v=M4 src=config
PASS | ③ 非法 dict ⇒ M1 + invalid_shape 原因 | v=M1 src=config:invalid_shape:矩阵配置形态非法（dict keys=['oops']）⇒ 须 matrix/value 键或裸字符串
PASS | ④ 非法裸串 M9 ⇒ M1 + default 原因 | v=M1 src=default:矩阵值非法（'M9'）⇒ 使用 M1
PASS | ⑤-0 闭环基线 M1（真实配置读回） | src=config
PASS | ⑤-1 复盘产建议（当前矩阵=真实配置 M1） | status=ok p0={'kind': 'element_matrix', 'tenant_id': 't_matrix_e2e', 'current': 'M1', 'target': 'M2', 'delta': 1, 'reason': '转人工占比 57% ≥ 50% 且人工全数批准 ⇒ 闸在制造无谓摩擦 ⇒ 倾向更重自动化矩阵', 'evidence': {'total': 35, 'pending': 20, 'pending_decided': 20, 'pending_approved': 20, 'pending_rejected': 0, 'pending_open': 0, 'pending_rate': 0.5714, 'reject_rate': 0.0, 'approve_rate': 1.0}, 'source': 'retro:evidence_signals'}
PASS | ⑤-2 建议⛔ 未改配置（只读）
PASS | ⑤-3 建议生成审批单（action=decision-element-matrix-apply） | created=[('ap-0001', 'decision-element-matrix-apply')]
PASS | ⑤-4 建单后⛔ 仍未生效（须审批）
PASS | ⑤-5 审批状态=APPROVED | APPROVED
PASS | ⑤-6 回派动作=decision-element-matrix-apply | decision-element-matrix-apply
PASS | ⑤-7 回派执行成功
PASS | ⑤-8 消费点**读回新矩阵 M2**（闭环终点=生效，非仅落库） | v=M2 src=config
PASS | ⑥ G3 直调拒绝（缺 _approval_passed ⇒ ValueError） | G3: 矩阵落盘必须经审批回派（缺 _approval_passed ⇒ 拒绝直调）
PASS | ⑥ 直调后配置未被改动（仍 M2） | v=M2
CLEAN | 已复原 t_matrix_e2e/decision_element_matrix 为进入前原值 {...}

==== 16 PASS / 0 FAIL ====
```

## 复验顺带修复（R-E3 实跑纪律自查产出）

④ 原输出曾为 `v=M1 ... ⇒ 使用 M9`（值正确、文案错位——control_plane 非法租户值分支传 `default=tenant_default` 拼文案后又被改值 M1）。已订正 `control_plane.py::_element_matrix_of`（不传自定义 default，文案如实"使用 M1"）。上方输出为**订正后**复跑结果。主判据同步复验 PASS=39/FAIL=0。
