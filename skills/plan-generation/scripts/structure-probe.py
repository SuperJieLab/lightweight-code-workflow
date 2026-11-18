#!/usr/bin/env python3
"""结构探针：数一个功能散在几个目录、跨目录引用几条。

用法：
    python3 structure-probe.py <仓库根> --feature order
    python3 structure-probe.py <仓库根> --feature order --feature user --json

只输出数字与明细，不给建议。判「应搬 / 合理」由人做，判据见 references/structure-rules.md。
"""
import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict

SOURCE_EXT = {".py", ".js", ".jsx", ".ts", ".tsx", ".dart", ".swift", ".m", ".mm", ".h"}
PARSE_EXT = {".py", ".js", ".jsx", ".ts", ".tsx", ".dart"}
SKIP_DIRS = {".git", "node_modules", "dist", "build", "__pycache__", ".venv", "venv",
             "Pods", ".build", "DerivedData", ".next", "coverage"}
TOKEN_SPLIT = re.compile(r"[/_.\-\s]+")
# 驼峰切分：Swift / ObjC / Kotlin 的主流命名靠大小写分界，不做这一步 OrderViewController 永远命中不了 order
CAMEL = re.compile(r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+|\d+")

PY_FROM = re.compile(r"^\s*from\s+(\.*[\w\.]*)\s+import\b")
PY_IMPORT = re.compile(r"^\s*import\s+([\w\.]+)")
JS_FROM = re.compile(r"""\bfrom\s+['"]([^'"]+)['"]""")
JS_REQUIRE = re.compile(r"""\brequire\(\s*['"]([^'"]+)['"]""")
DART_IMPORT = re.compile(r"""^\s*import\s+['"]([^'"]+)['"]""")


def collect(root):
    """遍历源码文件，返回 [(相对路径, 所在目录)]，跳过依赖与构建目录。"""
    out = []
    for cur, dirs, names in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for n in sorted(names):
            if os.path.splitext(n)[1] in SOURCE_EXT:
                rel = os.path.relpath(os.path.join(cur, n), root).replace(os.sep, "/")
                out.append((rel, os.path.dirname(rel)))
    return out


def hit_feature(rel, keyword):
    """按路径段的词元匹配功能关键词：先按分隔符切，再按驼峰切。

    两步都做是因为 snake_case 与 PascalCase 各占一半语言，只做一步会整类漏掉。
    """
    for seg in rel.split("/"):                 # 保留大小写，驼峰切分要用
        for token in TOKEN_SPLIT.split(seg):
            if token.lower() == keyword:
                return True
            if keyword in (t.lower() for t in CAMEL.findall(token)):
                return True
    return False


def build_index(files):
    """模块键（无扩展名的路径形态）→ 文件列表。"""
    index = defaultdict(list)
    for rel, _ in files:
        ext = os.path.splitext(rel)[1]
        base = rel[: -len(ext)]
        if ext == ".py" and base.endswith("/__init__"):
            base = base[: -len("/__init__")]
        elif ext == ".py" and base == "__init__":
            base = ""
        if base:
            index[base].append(rel)
        index[rel].append(rel)
    return index


def resolve_relative(spec, src_rel):
    """把 ./ ../ 开头的相对说明符解析成仓库内相对路径候选。"""
    base = os.path.dirname(src_rel)
    cand = os.path.normpath(os.path.join(base, spec)).replace(os.sep, "/")
    if cand.startswith("../") or cand == "..":
        return []
    return [cand]


def resolve_py(mod, src_rel, index):
    if mod.startswith("."):
        dots = len(mod) - len(mod.lstrip("."))
        rest = mod[dots:]
        base = os.path.dirname(src_rel)
        for _ in range(dots - 1):
            base = os.path.dirname(base)
        path = rest.replace(".", "/")
        cand = os.path.normpath(os.path.join(base, path)).replace(os.sep, "/") if path else base
        cands = [cand]
    else:
        cands = [mod.replace(".", "/")]
        # 也尝试去掉顶层包名后从仓库根找
        parts = cands[0].split("/")
        if len(parts) > 1:
            cands.append("/".join(parts[1:]))
    return cands


def imports_of(rel, text, index):
    """返回该文件引用的项目内目标文件列表。"""
    ext = os.path.splitext(rel)[1]
    found = []
    if ext == ".py":
        for line in text.splitlines():
            m = PY_FROM.match(line) or PY_IMPORT.match(line)
            if not m:
                continue
            # 命中第一个候选即停，不做多候选叠加：多算会让「应搬」误触发
            for cand in resolve_py(m.group(1), rel, index):
                hit = index.get(cand) or index.get(cand + ".py")
                if hit:
                    found.extend(hit)
                    break
    elif ext in {".js", ".jsx", ".ts", ".tsx"}:
        for spec in JS_FROM.findall(text) + JS_REQUIRE.findall(text):
            if not spec.startswith("."):
                continue
            for cand in resolve_relative(spec, rel):
                for key in (cand, cand + ".ts", cand + ".tsx", cand + ".js",
                            cand + ".jsx", cand + "/index.ts", cand + "/index.js"):
                    if key in index:
                        found.extend(index[key])
    elif ext == ".dart":
        for spec in DART_IMPORT.findall(text):
            if spec.startswith("package:") or spec.startswith("dart:"):
                continue
            if not spec.startswith("."):
                continue
            for cand in resolve_relative(spec, rel):
                if cand in index:
                    found.extend(index[cand])
    return sorted(set(found))


def main():
    ap = argparse.ArgumentParser(description="结构探针：功能分布目录数与跨目录引用条数")
    ap.add_argument("root", nargs="?", default=".")
    ap.add_argument("--feature", action="append", required=True,
                    help="功能关键词，可重复；按路径词元精确匹配")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    root = os.path.abspath(args.root)
    if not os.path.isdir(root):
        sys.exit(f"不是目录：{root}")

    files = collect(root)
    index = build_index(files)
    dir_of = dict(files)

    # 引用表：源文件 → 目标文件
    edges = {}
    parsed = unparsed = 0
    for rel, _ in files:
        if os.path.splitext(rel)[1] not in PARSE_EXT:
            unparsed += 1
            continue
        parsed += 1
        try:
            with open(os.path.join(root, rel), encoding="utf-8", errors="ignore") as f:
                edges[rel] = imports_of(rel, f.read(), index)
        except OSError:
            edges[rel] = []

    report = {"root": root, "features": [], "parsed_files": parsed,
              "unparsed_files": unparsed,
              "ref_metric_applicable": parsed > 0}

    # 全库口径：一个文件指向几个别的目录，就计几条；搬迁前后用同一口径对照
    global_cross = 0
    for rel, targets in edges.items():
        src_dir = dir_of[rel]
        global_cross += len({dir_of.get(t, "") for t in targets} - {src_dir})
    report["global_cross_refs"] = global_cross

    for kw in map(str.lower, args.feature):
        hits = [(rel, d) for rel, d in files if hit_feature(rel, kw)]
        spread = sorted({d for _, d in hits})
        cross = Counter()
        for rel in (r for r, _ in hits if r in edges):
            src_dir = dir_of[rel]
            for target in edges[rel]:
                tgt_dir = dir_of.get(target, "")
                if tgt_dir != src_dir:
                    cross[f"{src_dir or '.'} -> {tgt_dir or '.'}"] += 1
        report["features"].append({
            "feature": kw,
            "files": len(hits),
            "dir_count": len(spread),
            "dirs": spread,
            "cross_refs": sum(cross.values()),
            "cross_ref_pairs": dict(cross.most_common()),
            "paths": [r for r, _ in hits],
        })

    crowded = Counter(d for _, d in files).most_common(3)
    depth = max((d.count("/") + (1 if d else 0) for _, d in files), default=0)
    report["max_depth"] = depth
    report["source_files"] = len(files)
    report["crowded_dirs"] = [{"dir": d or ".", "files": n} for d, n in crowded]

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return

    for f in report["features"]:
        print(f"功能 {f['feature']}: {f['files']} 个文件，散在 {f['dir_count']} 个目录")
        if f["dirs"]:
            print(f"  目录: {', '.join(d or '.' for d in f['dirs'])}")
        if report["ref_metric_applicable"]:
            print(f"  跨目录引用: {f['cross_refs']} 条")
            for pair, n in f["cross_ref_pairs"].items():
                print(f"    {pair}: {n}")
        else:
            print("  跨目录引用: 不适用（无可解析引用的语言）")
    if report["ref_metric_applicable"]:
        print(f"全库跨目录引用: {global_cross} 条（搬迁前后用同一口径对照）")
    print(f"最大深度: {depth} 层 / 源码文件 {len(files)} 个")
    if unparsed:
        print(f"  引用指标未覆盖 {unparsed} 个文件（Swift / ObjC），只参与路径指标")
    for c in report["crowded_dirs"]:
        print(f"  {c['dir']}: {c['files']} 个文件")


if __name__ == "__main__":
    main()
