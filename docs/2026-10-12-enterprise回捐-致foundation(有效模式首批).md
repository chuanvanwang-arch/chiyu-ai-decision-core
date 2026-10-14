# enterprise 复盘回捐（致 chiyu-foundation）

- 来文：chiyu-enterprise（消费方）
- 日期：2026-10-12
- 性质：R-E5 回捐 —— 四评分矩阵/E2E 复盘产生的**有效模式**首批回执，供贵方沉淀为通用判据
- 通道：按横性要求 3，本文落本仓 `docs/`，贵方只读快照收取；裁定回执按"来文 → 回执 → 修订"闭环

## 回捐模式（均经本仓源码实证，非声明）

| # | 模式 | 实证锚点 | 沉淀建议 |
|---|---|---|---|
| 1 | **新动作 = handler + catalog 双注册**：仅注册 handler 而漏登 PLATFORM_ACTIONS 目录 ⇒ 审批回派报「未注册 Action」，纯函数层判据全绿也无法发现，只有 E2E 闭环能抓到。同款坑已两次（iam-role-revoke、decision-element-matrix-apply） | `action/platform_catalog.py`；E2E `verify_element_matrix_e2e.py` 首跑实锤 | 通用判据候选：「动作注册面完整性」——凡新增 mutating 动作，静态扫描 handler 注册表与 catalog 目录差集 |
| 2 | **E2E 深于纯函数判据**：缺失⇒强制人工路径在纯函数层有判据仍漏注册面缺口；"生产接线同面"（真连配置存储+真审批闭环）才能闭环 R-E1 类验收 | 本轮 E2E 16/0 vs 主判据 34/0 并存 | 已按贵方 R-E4 思路把"直连实证与生产接线同面"扩为两份判据常态 |
| 3 | **fixture 有效性自证先行**：组合路径判据须先断言"sensitive_hits 非空"证明 fixture 真命中，再断言 verdict —— 否则敏感词未命中时 verdict 由他轨决定，断言假绿 | `verify_u2_spine_route.py` U16d 自证门 | 写入判据编写规范：涉及"命中类"fixture 一律先自证命中 |
| 4 | **变异断言两侧同源恒绿**：断言两侧引用同一常量时，篡改该常量的变异恒绿（R9 假绿变体）。修法＝断言锚用判据内字面量 | `verify_element_matrix.py` V2（m2 变异依赖此） | 变异自证设计时逐断言检查"锚来源" |

## 后续回捐节奏

矩阵复盘闭环上线后，按日复盘产生的行业级有效结论（如某矩阵方案在某行业胜出）按月汇总回捐；首批以上述工程模式为主（复盘数据尚需积累期，如实告知）。
