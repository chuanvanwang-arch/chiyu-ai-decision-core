PY ?= C:/Users/wangchuan08/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe
PKG := packages/chiyu-kernel

.PHONY: test test-all check manifest dist lint


# ⛔ 不加 -o pythonpath：它相对 rootdir 解析，从仓库根传 "packages/chiyu-kernel/src"
#    会指到不存在的嵌套路径。路径装配职责：
#    · rootdir 归属 = 仓库根 pytest.ini
#    · 兄弟包 src 上路径 = 仓库根 conftest.py（各 tests/ conftest.py 仅在不冲突时补插）
TEST_PATHS := packages/chiyu-kernel/tests tools/tests
DECISION_TESTS := packages/chiyu-decision/src/chiyu_decision/tests
PORTAL_TESTS := packages/chiyu-portal/src/chiyu_portal/tests
EXAMPLES_TESTS := examples/reference_consumer/tests
CLI_TESTS := packages/chiyu-cli/tests

# ⛔ 兄弟包测试必须进回归闸门（2026-10-08/09 实测四处遗漏）：
#    ① chiyu_decision 的 24 个测试（含 WS3 approval_gate 接线测试）曾长期游离；
#    ② chiyu_portal 的 55 个测试（1311 行：nl_parser/schema/renderer/page_store/
#       guardrails/onboarding）曾长期游离——kernel 改动破坏 portal 时回归不红；
#    ③ WS9 参考消费层（examples/reference_consumer）的 15 个测试：样板一旦失效
#       （底座 API 漂移 / 探针失真）若不进闸门，就没人知道「样板其实跑不通」。
#    ④ chiyu_cli 的 13 个测试（commands/shell_lockdown 等）同样游离——cli 是
#       kernel 门面的直接消费方（如 _plugins.py 改走 api 门面时无回归保护）。
#    ⇒ `test` = 常驻包全量回归（kernel+tools+decision+portal+examples+cli），
#      `test-all` = `test` + 仓库根 tests/。判据存在但无人跑 = 不存在。
test:
	$(PY) -m pytest $(TEST_PATHS) $(DECISION_TESTS) $(PORTAL_TESTS) $(EXAMPLES_TESTS) $(CLI_TESTS) -q

test-all:
	$(PY) -m pytest $(TEST_PATHS) $(DECISION_TESTS) $(PORTAL_TESTS) $(EXAMPLES_TESTS) $(CLI_TESTS) tests -q

check:
	$(PY) tools/check_cython_friendly.py --root . $(PKG)/src

manifest:
	cd $(PKG)/src/chiyu_kernel/contract && $(PY) _gen_manifest.py

# B2 裁定（enterprise blocking-feedback）：chiyu-decision **属交付面**（授权分级、
#    可单独授权），分发方式 = 独立 wheel（版本钉 0.1.0），替代"拷 src 快照"现状。
#    kernel 与 decision 各自 wheel，消费方按授权择一/组合安装。
dist: check test
	cd $(PKG) && $(PY) -m build --wheel
	cd packages/chiyu-decision && $(PY) -m build --wheel
	# CRM 修复要求②：wheel↔源码 __all__ 一致性门禁（防中间态发版）
	$(PY) tools/check_dist_sync.py

lint:
	$(PY) tools/check_facade_coverage.py --facade chiyu_kernel.api --package chiyu_kernel --layers vector,ontology,context,actions,domain,persist,approval,gate,graph,mcpserver,canary,orchestration,evolution,events,audit,llm,plugins,session,tools,skills,plan,mcp,hooks,interaction,workflow,scenario,feedback,capability_audit,connectors,promotion,iam,conflict_resolver,attribution,audit_4q,ab_experiment,quota_gate,param_health_check,observability,agent_runtime,scheduler_core,nightly_report --renames-file tools/facade_renames.txt
	$(PY) tools/check_zero_residue.py
	# B1/N2：sanctioned import 面门禁（E1 双向：foundation 自身同样受约束）
	$(PY) tools/check_import_surface.py --verbose
	# T44：memory 单源裁定（graph_edge / particle_attribute 直写入口唯一，防双写回归）
	$(PY) tools/check_single_source_memory.py
