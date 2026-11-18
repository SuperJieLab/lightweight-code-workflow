#!/usr/bin/env python3
"""初始化 dev/ 工作区骨架。幂等：已存在的文件一律跳过，绝不覆盖。

用法：python3 init.py [仓库根目录]
输出：「新建 / 复用」清单；任何文件未被覆盖。
"""

import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATES = os.path.join(os.path.dirname(HERE), "assets")

DOCS = [
    ("README.md.template", "dev/README.md"),
    ("PROJECT.md.template", "dev/PROJECT.md"),
    ("RULES.md.template", "dev/RULES.md"),
    ("ISSUES.md.template", "dev/ISSUES.md"),
]

DIRS = ["dev/research", "dev/features"]

MEMORY_HEADER = "# 项目记忆\n\n"

BRIDGE_BEGIN = "<!-- workspace-init:begin -->"
BRIDGE_END = "<!-- workspace-init:end -->"

# 桥接块：让不认识这套工作流的 agent 一进项目就知道产物在哪、状态在哪、下一步问谁。
# 只增删块内内容，块外一个字不碰。
BRIDGE = BRIDGE_BEGIN + """
## 开发工作流（本工作区）

- 产物根目录 `dev/`，先读 `dev/README.md`。
- `dev/PROJECT.md` 项目是什么；`dev/RULES.md` 工程规则与目录承诺；`dev/ISSUES.md` 未结事项。
- 调研报告在 `dev/research/`，一个主题一份，别的目录没有。
- **状态只在文档头**：`dev/features/*/spec.md` 与 `plans/*.md` 的 front-matter `status` 字段，没有第二份状态表。
- 不知道下一步做什么 → 跑 `workspace-status`。
- 有新需求 → 直接说「我要做 X」。
- 两条通用能力：`research` 查外部事实与本仓库现状并出报告；`grill-me` 把没说出口的假设逼成决定。
""" + BRIDGE_END + "\n"


def main():
    repo = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    created, reused, warned = [], [], []

    for d in DIRS:
        path = os.path.join(repo, d)
        if os.path.isdir(path):
            reused.append(d + "/")
        else:
            os.makedirs(path, exist_ok=True)
            created.append(d + "/")

    docs_ok = True
    for tpl, dest in DOCS:
        src = os.path.join(TEMPLATES, tpl)
        dst = os.path.join(repo, dest)
        if os.path.exists(dst):
            reused.append(dest)
            continue
        if not os.path.exists(src):
            warned.append("模板缺失：%s" % src)
            docs_ok = False
            continue
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(src, dst)
        created.append(dest)

    mem = os.path.join(repo, ".workbuddy", "memory", "MEMORY.md")
    mem_rel = ".workbuddy/memory/MEMORY.md"

    if not docs_ok:
        warned.append("四份文档未齐，跳过工作流桥接块——索引不应指向不存在的文件")
    else:
        os.makedirs(os.path.dirname(mem), exist_ok=True)
        if not os.path.exists(mem):
            with open(mem, "w", encoding="utf-8") as f:
                f.write(MEMORY_HEADER + BRIDGE)
            created.append(mem_rel + "（新建，含工作流桥接块）")
        else:
            with open(mem, encoding="utf-8") as f:
                text = f.read()
            if not text.strip():
                with open(mem, "w", encoding="utf-8") as f:
                    f.write(MEMORY_HEADER + BRIDGE)
                created.append(mem_rel + "（空文件，补标题与工作流桥接块）")
            elif BRIDGE_BEGIN in text:
                if BRIDGE_END not in text:
                    warned.append("记忆层桥接块缺少结束标记 %s，请手工补齐：%s" % (BRIDGE_END, mem))
                else:
                    reused.append(mem_rel + "（桥接块已存在）")
            else:
                prefix = "" if not text else ("\n" if text.endswith("\n") else "\n\n")
                with open(mem, "a", encoding="utf-8") as f:
                    f.write(prefix + BRIDGE)
                created.append(mem_rel + "（追加工作流桥接块，块外未改动）")

    print("## 新建\n")
    print("\n".join("- " + c for c in created) if created else "无（全部复用）")
    print("\n## 复用\n")
    print("\n".join("- " + r for r in reused) if reused else "无")
    if warned:
        print("\n## 提示\n")
        print("\n".join("- " + w for w in warned))

    if warned and any("模板缺失" in w for w in warned):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
