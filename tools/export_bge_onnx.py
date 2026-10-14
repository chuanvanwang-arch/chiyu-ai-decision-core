#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""导出 bge-small-zh-v1.5 → ONNX（内核离线向量通道的**产物构建脚本**）。

上游依据：离线向量方案 B′ 的产物契约，与 `chiyu_kernel/vector/onnx_runner.py`
的 `EXPECTED_INPUTS / EXPECTED_OUTPUT / _warmup / config_dim` 一一对应。

产物契约（**不得放宽**）：
  · 输入 3 路：input_ids / attention_mask / token_type_ids
  · dynamic axes：batch(0) + seq(1) 双向动态（禁止烘死长度）
  · opset 17；单一输出 last_hidden_state（**不含** CLS 池化与 L2 归一化，
    二者留在 onnx_runner，与其 `OnnxRunner.encode()` 口径逐位对齐）
  · 对拍：ONNX 管线(tokenizers + CLS + L2) vs torch 参考(AutoTokenizer + AutoModel + CLS + L2)
    逐条 cos ≥ --min-cos（默认 0.9999）**且** max|Δ| ≤ --max-abs-diff（默认 1e-4）；
    **不达标 ⇒ 不落产物 + 退非零**（宁缺毋滥：宁可没有产物，不可有错产物）

依赖口径（正交，勿混）：
  · 导出期：torch + transformers + **onnx** —— **不入运行镜像**（内核运行期零 torch 是硬约束）
  · 运行期：onnxruntime + tokenizers

⛔ 本脚本**不下载权重**（离线环境禁出网）：要求 model_dir 下已有
   `model.safetensors` + `tokenizer.json`（HF 源权重的取得属外部通道职责）。
   本仓 `models/` 不入库（见 .gitignore），故克隆后需先补齐源权重再跑本脚本。

用法：
  python tools/export_bge_onnx.py                     # 导出 + 对拍 + 落产物
  python tools/export_bge_onnx.py --check-only        # 只对拍既有产物（不导出）
  python tools/export_bge_onnx.py --out /tmp/x.onnx   # 自定义产物路径
  python tools/export_bge_onnx.py --force             # 覆盖既有产物
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import sys
from datetime import datetime, timezone

try:  # Windows 控制台默认 cp936，中文输出会炸
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DEFAULT_MODEL_DIR = os.path.join(REPO, "models", "bge-small-zh-v1.5")
DEFAULT_OUT = os.path.join(DEFAULT_MODEL_DIR, "model.onnx")

MAX_CHARS = 480        # 与消费方入库口径的截断对齐（向量输入 ≤480 字符）
MAX_LEN = 512          # bge 系列位置编码上限
SEED = 20260921

# 边界样本：截断一致性、空输入、纯 ASCII、emoji、超长——词表/截断口径差异会在这里露头。
# ⛔ 语料保持**通用**（无领域字面量）：本脚本属底座，不得把某一项目的领域模型带进来。
EDGE_TEXTS = [
    "",
    "。",
    "a",
    "hello world 12345",
    "测试。",
    "😀😀 表情与符号 !@#$%^&*() 混排。",
    "。" * 600,                                    # 超长纯标点：考验截断
    ("这是一段用于触发位置编码上限的长文本，反复拼接以超过五百一十二个 token，"
     "用于验证导出图在超长输入下的截断行为与 torch 参考侧一致。") * 12,
]

# 通用对拍语料（无样本文件时的兜底；同义/无关对用于确认语义未被压平）
BUILTIN_TEXTS = [
    "今天天气很好，适合出门散步。",
    "天气不错，出去走走很舒服。",          # 上句的同义改写（语义能力探针）
    "数据库连接池耗尽导致服务不可用。",
    "订单在支付环节超时，需要人工介入核对。",
    "用户反馈页面加载缓慢，首屏超过五秒。",
]


def log(msg: str) -> None:
    print(f"[export_bge_onnx] {msg}", flush=True)


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build_corpus(n_real: int, corpus_file: str | None = None) -> tuple[list[str], str]:
    """对拍语料：可选外部文本文件（每行一条）+ 边界样本。返回 (texts, 来源说明)。"""
    texts: list[str] = []
    source = "builtin"
    if corpus_file and os.path.isfile(corpus_file):
        rows = [ln.strip()[:MAX_CHARS] for ln in
                open(corpus_file, encoding="utf-8-sig").read().splitlines()]
        rows = [r for r in rows if r]
        if rows:
            rnd = random.Random(SEED)
            texts = rnd.sample(rows, min(n_real, len(rows)))
            source = f"{os.path.relpath(corpus_file, REPO)}（{len(rows)} 行，seeded={SEED} 抽 {len(texts)}）"
    if not texts:
        texts = list(BUILTIN_TEXTS)
        source = "builtin（通用语料，无领域字面量）"
    return texts + EDGE_TEXTS, source


# ---------------------------------------------------------------- torch 参考侧

def torch_reference(model_dir: str, texts: list[str]):
    """与 `OnnxRunner.encode` 逐位同口径：CLS 池化 + L2 归一化。"""
    import numpy as np
    import torch
    from transformers import AutoModel, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(model_dir, local_files_only=True)
    model = AutoModel.from_pretrained(model_dir, local_files_only=True)
    model.eval()
    ids_log = []
    vecs = []
    with torch.no_grad():
        for t in texts:
            enc = tok(t, return_tensors="pt", truncation=True, max_length=MAX_LEN)
            ids_log.append([int(x) for x in enc["input_ids"][0].tolist()])
            out = model(**enc)
            v = out.last_hidden_state[:, 0, :]                       # [CLS]
            v = torch.nn.functional.normalize(v, p=2, dim=1)
            vecs.append(v.squeeze(0).numpy().astype(np.float32))
    return np.stack(vecs), ids_log


# ------------------------------------------------------------------ ONNX 侧

def onnx_encode(onnx_path: str, model_dir: str, texts: list[str]):
    """运行期口径的等价实现：tokenizers 直读 tokenizer.json（不依赖 transformers）。"""
    import numpy as np
    import onnxruntime as ort
    from tokenizers import Tokenizer

    tok = Tokenizer.from_file(os.path.join(model_dir, "tokenizer.json"))
    tok.enable_truncation(max_length=MAX_LEN)
    sess = ort.InferenceSession(onnx_path, providers=["CPUExecutionProvider"])
    in_names = [i.name for i in sess.get_inputs()]
    out_names = [o.name for o in sess.get_outputs()]
    ids_log, vecs, lens = [], [], []
    for t in texts:
        e = tok.encode(t)
        ids = np.asarray([e.ids], dtype=np.int64)
        mask = np.asarray([e.attention_mask], dtype=np.int64)
        types = np.asarray([e.type_ids], dtype=np.int64)
        feed = {}
        for nm in in_names:
            feed[nm] = {"input_ids": ids, "attention_mask": mask, "token_type_ids": types}[nm]
        hidden = sess.run(["last_hidden_state"] if "last_hidden_state" in out_names else None, feed)[0]
        v = hidden[:, 0, :].astype(np.float32)                       # [CLS]
        nrm = np.linalg.norm(v, axis=1, keepdims=True)
        v = v / np.where(nrm == 0, 1.0, nrm)                         # L2 归一化
        ids_log.append([int(x) for x in e.ids])
        lens.append(int(ids.shape[1]))
        vecs.append(v.squeeze(0))
    return np.stack(vecs), ids_log, lens, in_names, out_names


# --------------------------------------------------------------- 导出

def export_onnx(model_dir: str, tmp_out: str) -> None:
    import torch
    from transformers import AutoModel

    class _ExportWrapper(torch.nn.Module):
        """只暴露 last_hidden_state（单输出），避免 use_cache 带来 past_key_values 噪声。"""

        def __init__(self, m):
            super().__init__()
            self.m = m

        def forward(self, input_ids, attention_mask, token_type_ids):
            return self.m(input_ids=input_ids, attention_mask=attention_mask,
                          token_type_ids=token_type_ids).last_hidden_state

    model = AutoModel.from_pretrained(model_dir, local_files_only=True)
    model.eval()
    model.config.use_cache = False          # 否则输出含 past_key_values，图里多出无用分支
    model.config.return_dict = True
    wrap = _ExportWrapper(model).eval()

    dummy = torch.zeros((1, 8), dtype=torch.long)
    dyn = {n: {0: "batch", 1: "seq"} for n in
           ("input_ids", "attention_mask", "token_type_ids", "last_hidden_state")}
    torch.onnx.export(
        wrap,
        (dummy, dummy.clone(), dummy.clone()),
        tmp_out,
        input_names=["input_ids", "attention_mask", "token_type_ids"],
        output_names=["last_hidden_state"],
        dynamic_axes=dyn,
        opset_version=17,
        do_constant_folding=True,
        dynamo=False,        # torch>=2.9 默认走 dynamo 分支（需 onnxscript）；legacy 路径更稳
    )
    log(f"ONNX 已导出到临时文件：{os.path.relpath(tmp_out, REPO)}"
        f"（{os.path.getsize(tmp_out) / 1e6:.1f} MB）")


def assert_dynamic(onnx_path: str) -> dict:
    """反假绿：产物必须真动态。用两种序列长度回放，形状必须随输入变化。

    两种失败形态都要给可读诊断（均退非零，绝不静默）：
      ① 图里形状烘死 ⇒ ORT 直接抛 InvalidArgument（回放 seq 与导出时不一致）；
      ② 图声明动态但输出形状不随输入变 ⇒ 形状断言失败。
    只报 ① 的原始堆栈会让人误以为"ONNX 坏了"，实际是**导出时忘传 dynamic_axes**。
    """
    import numpy as np
    import onnxruntime as ort

    sess = ort.InferenceSession(onnx_path, providers=["CPUExecutionProvider"])
    names = [i.name for i in sess.get_inputs()]
    shapes = {}
    for L in (3, 11):
        feed = {nm: np.ones((1, L), dtype=np.int64) for nm in names}
        try:
            shapes[L] = list(sess.run(None, feed)[0].shape)
        except Exception as e:  # noqa: BLE001
            raise SystemExit(
                f"❌ 产物形状未动态：回放 seq={L} 被 ORT 拒绝"
                f"（{type(e).__name__}: {str(e).splitlines()[0]}）"
                f"\n   ⇒ batch/seq 在导出时被烘死（dynamic_axes 缺失）。"
                f"短工单与长工单共用同一张图会直接报错，且只跑单条样例的验收看不出来。") from e
    if not (shapes[3][0] == 1 and shapes[3][1] == 3 and shapes[11][1] == 11):
        raise SystemExit(f"❌ 产物非动态：seq=3 → {shapes[3]}，seq=11 → {shapes[11]}；"
                         f"禁止烘死 batch/seq")
    return shapes


# --------------------------------------------------------------- 对拍

def parity(onnx_path: str, model_dir: str, texts: list[str], min_cos: float,
           max_abs_diff: float) -> dict:
    import numpy as np

    ref_vecs, ref_ids = torch_reference(model_dir, texts)
    onx_vecs, onx_ids, lens, in_names, out_names = onnx_encode(onnx_path, model_dir, texts)

    # 先隔离"分词不一致"与"模型不一致"：分词不一致时 cos 无意义
    tok_mismatch = [i for i, (a, b) in enumerate(zip(ref_ids, onx_ids)) if a != b]
    if tok_mismatch:
        raise SystemExit(
            f"❌ 分词口径不一致（{len(tok_mismatch)}/{len(texts)} 条），"
            f"index={tok_mismatch[:5]}：transformers.AutoTokenizer 与 tokenizers.Tokenizer "
            f"加载同一 tokenizer.json 必须逐 token 相同，否则对拍结论无效")

    cos = []
    mad = []
    for i in range(len(texts)):
        a, b = ref_vecs[i], onx_vecs[i]
        na, nb = float(np.linalg.norm(a)), float(np.linalg.norm(b))
        cos.append(float(np.dot(a, b) / (na * nb)) if na > 0 and nb > 0 else 0.0)
        mad.append(float(np.max(np.abs(a - b))))
    cos, mad = np.asarray(cos), np.asarray(mad)

    worst = int(np.argmin(cos))
    report = {
        "n_texts": len(texts),
        "min_cos": float(cos.min()),
        "mean_cos": float(cos.mean()),
        "max_abs_diff": float(mad.max()),
        "min_cos_index": worst,
        "min_cos_text_head": texts[worst][:60],
        "seq_lens": sorted(set(lens)),
        "onnx_inputs": in_names,
        "onnx_outputs": out_names,
        "dims": int(ref_vecs.shape[1]),
        "thresholds": {"min_cos": min_cos, "max_abs_diff": max_abs_diff},
    }
    ok = bool(cos.min() >= min_cos and mad.max() <= max_abs_diff)
    report["pass"] = ok
    return report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="bge-small-zh-v1.5 → ONNX 导出与对拍")
    ap.add_argument("--model-dir", default=os.environ.get("CHIYU_MODEL_DIR", DEFAULT_MODEL_DIR))
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--corpus-file", default=None, help="可选：每行一条文本的对拍语料")
    ap.add_argument("--real-texts", type=int, default=32, help="语料抽样条数（另加边界样本）")
    ap.add_argument("--min-cos", type=float, default=0.9999)
    ap.add_argument("--max-abs-diff", type=float, default=1e-4)
    ap.add_argument("--check-only", action="store_true", help="只对拍既有产物，不导出")
    ap.add_argument("--force", action="store_true", help="既有产物且未指定 --check-only 时覆盖")
    args = ap.parse_args(argv)

    model_dir = os.path.abspath(args.model_dir)
    out = os.path.abspath(args.out)
    if not os.path.isfile(os.path.join(model_dir, "model.safetensors")):
        raise SystemExit(f"❌ {model_dir} 下无 model.safetensors —— 本脚本只做 ONNX 转换，"
                         f"不负责下载权重（离线环境禁出网）")
    if not os.path.isfile(os.path.join(model_dir, "tokenizer.json")):
        raise SystemExit(f"❌ {model_dir} 下无 tokenizer.json —— tokenizers 直读所需")

    texts, source = build_corpus(args.real_texts, args.corpus_file)
    log(f"对拍语料 {len(texts)} 条，来源：{source}")

    tmp = out + ".tmp"
    exported = False
    if args.check_only:
        if not os.path.isfile(out):
            raise SystemExit(f"❌ --check-only 但产物不存在：{out}")
        target = out
    else:
        if os.path.isfile(out) and not args.force:
            log(f"产物已存在（{os.path.relpath(out, REPO)}），改判为 --check-only 模式；"
                f"要重导出请加 --force")
            target = out
        else:
            if os.path.exists(tmp):
                os.remove(tmp)
            export_onnx(model_dir, tmp)
            target = tmp
            exported = True

    shapes = assert_dynamic(target)
    log(f"动态性已核实：seq=3 → {shapes[3]}，seq=11 → {shapes[11]}")

    rep = parity(target, model_dir, texts, args.min_cos, args.max_abs_diff)
    rep.update({
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "artifact": os.path.relpath(out, REPO),
        "model_dir": os.path.relpath(model_dir, REPO),
        "corpus_source": source,
        "dynamic_shapes": {str(k): v for k, v in shapes.items()},
    })

    log(f"对拍结果：min_cos={rep['min_cos']:.8f} mean_cos={rep['mean_cos']:.8f} "
        f"max|Δ|={rep['max_abs_diff']:.3e}（阈值 cos≥{args.min_cos} 且 |Δ|≤{args.max_abs_diff}）")

    if not rep["pass"]:
        if exported and os.path.exists(tmp):
            os.remove(tmp)
            log("❌ 对拍不达标 ⇒ 已删除临时产物，**未落任何 ONNX**")
        log(f"最差样本 idx={rep['min_cos_index']} cos={rep['min_cos']:.8f} "
            f"text≈{rep['min_cos_text_head']!r}")
        print(json.dumps(rep, ensure_ascii=False, indent=2))
        return 1

    if exported:
        os.replace(tmp, out)                 # 先对拍后落盘：不达标绝不产生错产物
        rep["artifact_sha256"] = sha256_file(out)
        rep["artifact_bytes"] = os.path.getsize(out)
        log(f"✅ 对拍通过 ⇒ 产物已落盘：{os.path.relpath(out, REPO)} "
            f"({rep['artifact_bytes'] / 1e6:.1f} MB, sha256={rep['artifact_sha256'][:16]}…)")
    else:
        rep["artifact_sha256"] = sha256_file(out)

    rep_path = out + ".parity.json"
    with open(rep_path, "w", encoding="utf-8") as f:
        json.dump(rep, f, ensure_ascii=False, indent=2)
    log(f"对拍台账已写：{os.path.relpath(rep_path, REPO)}")
    print(json.dumps({k: rep[k] for k in
                      ("pass", "n_texts", "min_cos", "max_abs_diff", "dims")},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
