#!/usr/bin/env python3
"""初始化 dev/ 工作区骨架。幂等：已存在的文件一律跳过，绝不覆盖。

用法：python3 init.py [仓库根目录] [--refresh-bridge]
输出：「新建 / 复用 / 提示」清单；除 --refresh-bridge 外不改动任何既有内容。
--refresh-bridge：把记忆层里已存在的工作流桥接块重写成当前版本，只动块内，块外不碰。
"""

import os
import re
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

# 桥接块：让不认识这套工作流的 agent 一进项目就知道来源、文件地图、状态在哪、怎么进入。
# 四段顺序固定：来源与依赖 → 文档地图 → 状态唯一来源 → 进入方式。
# 只增删块内内容，块外一个字不碰。
BRIDGE = BRIDGE_BEGIN + """
## 开发工作流（本工作区）

本工作区按「轻量代码工作流」作业，共十个 skill：`workspace-init`、`workspace-status`、`spec-generation`、`plan-generation`、`tdd`、`code-review`、`code-slim-audit`、`spec-verify`、`research`、`grill-me`。它们由 `real-engineer-skills` 插件提供；**当前会话里看不到这些 skill 时先安装，不要凭印象自己编流程。**

### 先读哪份文档

| 路径 | 管什么 |
|---|---|
| `dev/README.md` | 工作区说明与格位表，从这份进 |
| `dev/PROJECT.md` | 项目现在什么样：整体目标、功能组织、怎么用 |
| `dev/RULES.md` | 工程规则、命名、目录承诺表；改代码前看这份 |
| `dev/ISSUES.md` | 不属于任何需求、但迟早要处理的事 |
| `dev/research/` | 调研报告，一个主题一份 |
| `dev/features/F<N>-<主题>/` | 一个需求一格：`spec.md` 是承诺、`plans/` 是方案、`checks/` 是复核快照 |

### 状态只有一个来源

`spec.md` 与 `plans/*.md` front-matter 里的 `status` 字段。不建索引表，不另记进度文件——两处状态迟早不一致，而不一致时没人知道该信哪份。

### 怎么进入流程

- **不知道下一步做什么**：跑 `workspace-status`，它读状态、报矛盾、给出下一步；进哪个 skill 由你定。
- **有新需求**：说「我要做 X」，从 `spec-generation` 起，先把承诺定成可判定的，再谈方案。
- **随时可用的两个能力**：`research` 查外部事实与本仓库现状并出一份报告；`grill-me` 把没说出口的假设逼成明确决定。
""" + BRIDGE_END + "\n"


def main():
    refresh = "--refresh-bridge" in sys.argv[1:]
    positional = [a for a in sys.argv[1:] if not a.startswith("--")]
    repo = positional[0] if positional else os.getcwd()
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
                elif refresh:
                    pattern = re.compile(
                        re.escape(BRIDGE_BEGIN) + r".*?" + re.escape(BRIDGE_END), re.S)
                    new_text, hits = pattern.subn(BRIDGE.rstrip("\n"), text)
                    if hits != 1:
                        warned.append("桥接块标记出现 %d 次，无法确定替换范围，未改动：%s" % (hits, mem))
                    else:
                        with open(mem, "w", encoding="utf-8") as f:
                            f.write(new_text)
                        created.append(mem_rel + "（桥接块刷新为当前版本，块外未改动）")
                else:
                    reused.append(mem_rel + "（桥接块已存在；要更新内容加 --refresh-bridge）")
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
