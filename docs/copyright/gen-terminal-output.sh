#!/usr/bin/env bash
# 真实执行软著材料所需的命令/演示，把标准输出落盘到 terminal-output/。
#
# ⛔ 本脚本只负责"跑真命令、存真输出"；渲染与截图由 capture-terminal.mjs 负责
#    （Node 在 Windows 下直接 spawn 该 venv 解释器会 EBUSY，故拆成两段）。
#
# 用法：bash docs/copyright/gen-terminal-output.sh
set -u

ROOT="D:/system/chiyu-foundation"
PY="C:/Users/wangchuan08/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe"
OUT="$ROOT/docs/copyright/terminal-output"

export PYTHONPATH="$ROOT/packages/chiyu-kernel/src;$ROOT/packages/chiyu-decision/src;$ROOT/packages/chiyu-portal/src;$ROOT/packages/chiyu-cli/src"
export PYTHONIOENCODING=utf-8
export PYTHONUTF8=1

mkdir -p "$OUT"
cd "$ROOT" || exit 1

run() {
  local id="$1"; shift
  local title="$1"; shift
  local budget="$1"; shift
  printf '  > %s %s\n' "$id" "$title"
  timeout "$budget" "$@" >"$OUT/$id-$title.txt" 2>&1
  local rc=$?
  if [ "$rc" -ne 0 ]; then
    printf '    !! 退出码 %s（%s）\n' "$rc" "$id"
  fi
  return 0
}

echo "== B 系列：命令行与运维工具 =="
run B01 命令行入口总览 120 "$PY" -m chiyu_cli --help
run B02 版本查询 120 "$PY" -m chiyu_cli --version
run B03 工作模式查询 120 "$PY" -m chiyu_cli modes
run B04 单模式详情 120 "$PY" -m chiyu_cli modes --mode ptc
run B05 决策脊柱执行 120 "$PY" -m chiyu_cli decide --topic "是否批准该客户的预算追加请求"
run B06 决策结果结构化输出 120 "$PY" -m chiyu_cli decide --topic "是否批准该客户的预算追加请求" --scores clarity=4,logic=4 --json
run B07 门户页面渲染 120 "$PY" -m chiyu_cli portal render --nl "显示本季度全部订单的列表，按金额排序" --title "季度订单" --particle-types order --entity-map "订单=order"
run B08 引导页生成 120 "$PY" -m chiyu_cli portal onboarding
run B09 自进化开闸认证 180 "$PY" -m chiyu_cli evolution readiness
run B10 包内自测 400 "$PY" -m chiyu_cli selftest

echo "== C 系列：门面能力演示 =="
for d in version:版本化与兼容承诺 contract:契约与配置载体 particle:粒子与本体管理 \
         vector:向量与语义检索 context:情境装配与降级召回 graph:图存储与关系视图 \
         spine:决策脊柱 approval:审批治理与续跑 events:事件与审计 canary:金丝雀探针 \
         plugins:插件与工作模式 mcp:模型接入与协议适配 portal:门户运行时; do
  key="${d%%:*}"; title="${d#*:}"
  case "$key" in
    version)  id=C01 ;; contract) id=C02 ;; particle) id=C03 ;; vector)   id=C04 ;;
    context)  id=C05 ;; graph)    id=C06 ;; spine)    id=C07 ;; approval) id=C08 ;;
    events)   id=C09 ;; canary)   id=C10 ;; plugins)  id=C11 ;; mcp)      id=C12 ;;
    portal)   id=C13 ;;
  esac
  run "$id" "$title" 180 "$PY" "$ROOT/docs/copyright/demo-runner.py" "$key"
done

echo "== D 系列：质量保证与守卫工具链 =="
run D01 导入方向守卫 180 "$PY" "$ROOT/tools/check_import_surface.py" --verbose
run D02 门面覆盖守卫 180 "$PY" "$ROOT/tools/check_facade_coverage.py" \
  --facade chiyu_kernel.api --package chiyu_kernel \
  --layers vector,ontology,context,actions,domain,persist,approval,graph,mcpserver,canary,orchestration,evolution,events,audit,llm,plugins,session,tools,skills,plan,mcp,hooks,interaction,workflow,scenario \
  --renames-file "$ROOT/tools/facade_renames.txt"
run D03 零残留守卫 180 "$PY" "$ROOT/tools/check_zero_residue.py"
run D04 分发物同步守卫 180 "$PY" "$ROOT/tools/check_dist_sync.py"
run D05 能力清单生成 180 "$PY" "$ROOT/tools/gen_capability_manifest.py"

echo
echo "完成。输出目录：$OUT"
