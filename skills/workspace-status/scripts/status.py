#!/usr/bin/env python3
"""读 dev/ 下所有 spec 与 plan 的文件头，推导阶段、检查矛盾、给出下一步。

用法：python3 status.py [仓库根目录]
输出：状态表 / 矛盾清单 / 下一步三段 markdown；有矛盾时退出码 1。
"""

import os
import re
import sys

SPEC_STATUS = {"draft", "approved", "delivered", "superseded"}
PLAN_STATUS = {"draft", "approved", "executing", "done", "reviewed", "closed", "abandoned"}

NEXT_BY_PLAN = {
    "draft": ("方案未定", "R2 plan-generation"),
    "approved": ("待执行", "R3 tdd"),
    "executing": ("执行中", "R3 tdd"),
    "done": ("待复核", "R4 code-review"),
    "reviewed": ("待精简", "R5 code-slim-audit"),
}


def read_head(path):
    """读 --- 包围的 front-matter，返回 dict。没有 front-matter 返回 None。"""
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return None, ""
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?", text, re.S)
    if not m:
        return None, text
    head = {}
    for line in m.group(1).splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        k, v = line.split(":", 1)
        head[k.strip()] = v.split("#")[0].strip()
    return head, text[m.end():]


def load_plans(fdir):
    plans = []
    pdir = os.path.join(fdir, "plans")
    if not os.path.isdir(pdir):
        return plans
    for name in sorted(os.listdir(pdir)):
        if not name.endswith(".md"):
            continue
        path = os.path.join(pdir, name)
        head, body = read_head(path)
        head = head or {}
        try:
            phase = int(head.get("phase", "0"))
        except ValueError:
            phase = 0
        checked = len(re.findall(r"^\s*-\s*\[x\]", body, re.M))
        results = len(re.findall(r"^\s*结果[：:]", body, re.M))
        plans.append({
            "file": name,
            "path": path,
            "head": head,
            "phase": phase,
            "status": head.get("status", ""),
            "checked": checked,
            "results": results,
        })
    plans.sort(key=lambda p: (p["phase"], p["file"]))
    return plans


def derive(spec, plans, fid):
    """返回 (阶段, 下一步, 阻塞说明)。"""
    status = spec.get("status", "")
    if not status:
        return "状态缺失", "修 spec 文件头", "spec 缺 status 字段"
    if status not in SPEC_STATUS:
        return "状态非法", "修 spec 文件头", "spec 的 status 不在枚举内：%s" % status
    if status == "superseded":
        return "已废弃", "—", "该 Feature 被替代"
    if status == "delivered":
        return "已完成", "—", ""
    if status == "draft":
        return "承诺未定", "R1 spec-generation", ""

    active = [p for p in plans if p["status"] != "abandoned"]
    if not active:
        return "待写方案", "R2 plan-generation", ""

    pending = [p for p in active if p["status"] != "closed"]
    if not pending:
        return "待交付", "R6 spec-verify", ""

    first = pending[0]
    stage, nxt = NEXT_BY_PLAN.get(first["status"], ("状态未知", "修 plan 文件头"))
    block = ""
    if first["status"] != "draft" and first["phase"] > 1:
        prev = [p for p in active if p["phase"] == first["phase"] - 1]
        if prev and prev[0]["status"] != "closed":
            block = "第 %d 分期未 closed" % (first["phase"] - 1)
    return stage, nxt, block


def check(spec, plans, fid, dirname):
    issues = []
    s = spec.get("status", "")
    if s and s not in SPEC_STATUS:
        issues.append("%s：spec 的 status 非法（%s）" % (fid, s))
    if not s:
        issues.append("%s：spec 缺 status 字段" % fid)

    if spec.get("feature") and spec["feature"] != fid:
        issues.append("%s：spec 的 feature 字段写成 %s" % (fid, spec["feature"]))

    for p in plans:
        st = p["status"]
        if st and st not in PLAN_STATUS:
            issues.append("%s/%s：plan 的 status 非法（%s）" % (fid, p["file"], st))
        if not st:
            issues.append("%s/%s：plan 缺 status 字段" % (fid, p["file"]))
        if p["head"].get("feature") and p["head"]["feature"] != fid:
            issues.append("%s/%s：plan 的 feature 字段写成 %s" % (fid, p["file"], p["head"]["feature"]))

    # 1. spec 仍 draft 但有非 draft 的 plan
    if s == "draft":
        bad = [p["file"] for p in plans if p["status"] not in ("draft", "")]
        if bad:
            issues.append("%s：spec 仍是 draft，但 %s 已推进（跳过批准或忘了重开）" % (fid, "、".join(bad)))

    # 2. spec 已 delivered 但有非 closed 的 plan
    if s == "delivered":
        bad = [p["file"] for p in plans if p["status"] not in ("closed", "abandoned")]
        if bad:
            issues.append("%s：spec 已 delivered，但 %s 未 closed" % (fid, "、".join(bad)))

    # 3. 分期号断号或重号
    phases = [p["phase"] for p in plans if p["status"] != "abandoned"]
    if phases:
        if len(set(phases)) != len(phases):
            issues.append("%s：分期号重号（%s）" % (fid, phases))
        if sorted(phases) != list(range(1, len(phases) + 1)):
            issues.append("%s：分期号不连续（%s）" % (fid, sorted(phases)))

    # 4. 某分期 approved 但前一个分期未 closed
    active = [p for p in plans if p["status"] != "abandoned"]
    for p in active:
        if p["status"] == "draft" or p["phase"] <= 1:
            continue
        prev = [q for q in active if q["phase"] == p["phase"] - 1]
        if prev and prev[0]["status"] != "closed":
            issues.append("%s：第 %d 分期已 %s，但第 %d 分期仍是 %s"
                          % (fid, p["phase"], p["status"], p["phase"] - 1, prev[0]["status"]))

    # 6. 勾选数与结果行数不等
    for p in plans:
        if p["checked"] != p["results"]:
            issues.append("%s/%s：勾选 %d 项，结果行 %d 条，不等（勾了没写结果，或反之）"
                          % (fid, p["file"], p["checked"], p["results"]))

    return issues


def main():
    repo = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    froot = os.path.join(repo, "dev", "features")

    if not os.path.isdir(froot):
        print("## 状态\n\n工作区未初始化：`dev/features/` 不存在。请先跑 `workspace-init`。")
        return 0

    rows, issues = [], []
    max_id = 0
    for dirname in sorted(os.listdir(froot)):
        fdir = os.path.join(froot, dirname)
        if not os.path.isdir(fdir):
            continue
        m = re.match(r"^F(\d+)", dirname)
        fid = "F" + m.group(1) if m else dirname
        if m:
            max_id = max(max_id, int(m.group(1)))
        spec_path = os.path.join(fdir, "spec.md")
        spec, _ = read_head(spec_path)
        if spec is None:
            issues.append("%s：缺 spec.md 或其 front-matter" % fid)
            continue
        plans = load_plans(fdir)
        stage, nxt, block = derive(spec, plans, fid)
        issues.extend(check(spec, plans, fid, dirname))
        rows.append((fid, spec.get("topic", "—"), stage, nxt, block or "—"))

    print("## 状态\n")
    if not rows:
        print("`dev/features/` 下还没有任何 Feature。可以开始第一个需求。")
    else:
        print("| Feature | 主题 | 阶段 | 下一步 | 阻塞 |")
        print("|---|---|---|---|---|")
        for r in rows:
            print("| %s | %s | %s | %s | %s |" % r)

    done = [r for r in rows if r[2] == "已完成"]
    if not issues and rows and len(done) == len(rows):
        print("\n当前无需动作。全部 Feature 已交付。")

    print("\n## 矛盾\n")
    if issues:
        for i in issues:
            print("- " + i)
    else:
        print("无。")

    print("\n## 下一步\n")
    if issues:
        print("先处理上面的矛盾，再按下面的建议推进——矛盾意味着有人手工改了文件头，此时的状态不可信。\n")
    cand = [r for r in rows if r[3] not in ("—",) and r[2] not in ("已完成", "已废弃")]
    if not cand:
        print("没有需要推进的 Feature。")
    else:
        f, topic, stage, nxt, block = cand[0]
        print("建议 %s。%s · %s · %s。理由：编号最小的未完成 Feature%s。"
              % (nxt, f, topic, stage, "，依赖已满足" if block == "—" else "，但" + block))

    print("\n下一个可用编号：F%d" % (max_id + 1))

    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
