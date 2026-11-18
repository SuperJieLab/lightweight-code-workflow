#!/usr/bin/env python3
"""把「引用的原文片段」钉成行号。模型报原文，代码算行号——让模型算行号必错。

用法：
  python3 locate.py <目标文件> <片段文件>
  cat snippet.txt | python3 locate.py <目标文件> -

输出：匹配到的行区间，如 `42-45`；多处命中时逐行列出并标注「歧义」；未命中退出码 1。

归一化规则（与匹配口径一致）：去首尾空白、剥掉行首的 `+` / `-`、丢弃空行。
"""

import sys


def norm(line):
    s = line.strip()
    if s[:1] in ("+", "-"):
        s = s[1:]
    return s.strip()


def index_lines(lines):
    """返回 [(行号, 归一化内容)]，跳过空行。"""
    out = []
    for i, raw in enumerate(lines, start=1):
        n = norm(raw.rstrip("\r\n"))
        if n:
            out.append((i, n))
    return out


def find(index, target):
    if not target or len(index) < len(target):
        return []
    hits = []
    for i in range(len(index) - len(target) + 1):
        if all(index[i + j][1] == target[j] for j in range(len(target))):
            hits.append((index[i][0], index[i + len(target) - 1][0]))
    return hits


def main():
    if len(sys.argv) < 3:
        print(__doc__.strip())
        return 2
    path, snippet_arg = sys.argv[1], sys.argv[2]

    with open(path, encoding="utf-8", errors="replace") as f:
        index = index_lines(f)

    if snippet_arg == "-":
        snippet = sys.stdin.read()
    else:
        with open(snippet_arg, encoding="utf-8", errors="replace") as f:
            snippet = f.read()

    target = [norm(l) for l in snippet.splitlines()]
    target = [l for l in target if l]
    if not target:
        print("片段为空，无法定位")
        return 2

    hits = find(index, target)
    if not hits:
        print("未命中：片段与文件内容不一致。检查是否改写了原文（换行、缩进、注释），"
              "原文必须逐字引用。")
        return 1
    if len(hits) == 1:
        print("%d-%d" % hits[0])
        return 0

    print("歧义：命中 %d 处，需人工确认或加长片段" % len(hits))
    for start, end in hits:
        print("  %d-%d" % (start, end))
    return 1


if __name__ == "__main__":
    sys.exit(main())
