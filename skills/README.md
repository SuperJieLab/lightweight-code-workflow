# AI 开发工作流 · skill 套件

一套以「提交承诺 → 落地方案 → 执行 → 复核 → 精简 → 交付」为主链的 AI 开发流程。设计依据见仓库根的 `WORKFLOW-DESIGN.md`，本文只讲怎么用、怎么读这套文件。

## 一、三层，但目录里看不出来

插件目录是平铺的，一层的 skill 和二层的长得一样。所以层级只在本文里声明，靠**名字的语义形态**区分：

| 层 | skill | 名字形态 | 共同点 |
|---|---|---|---|
| **工作区** | `workspace-init`、`workspace-status` | 管 `dev/` 这个载体 | 与具体需求无关，随时可跑 |
| **节点** | `spec-generation`、`plan-generation`、`tdd`、`code-review`、`code-slim-audit`、`spec-verify` | 指向一份产物 | 有独立产物、有退出判据、需要单独批准 |
| **通用能力** | `research`、`grill-me` | 指向做事的方式 | 落盘物不参与状态跃迁；`research` 固定产出一份报告，`grill-me` 的假设清单寄在当次产物里 |

判据：节点头的产物是状态跃迁的条件（缺了 `workspace-status` 会报），所以名字指向那份产物；通用能力的落盘物不影响任何 `status` 字段，所以名字指向那件事。

## 二、只有两个入口

1. **不知道下一步做什么** → `workspace-status`。它读状态、报矛盾、给下一步；进哪个 skill 由你决定。
2. **有新需求** → 直接说「我要做 X」。`spec-generation` 会先检查 `dev/` 是否已建，没建就转 `workspace-init`。

中间的流转不需要记：每个节点做完会推进状态，然后必须调一次 `workspace-status` 拿下一步——节点自己不知道后继是谁，这条纪律是整套流程能连起来的原因。

## 三、状态的唯一来源是产物文件头

`spec.md` 和每份 `plans/*.md` 的 front-matter 是唯一真实数据源。分期状态、Feature 状态、项目状态全部由它推导，任何索引表都不存状态。

```yaml
# spec.md
---
feature: F12
topic: 未读按会话维度
status: approved      # draft | approved | delivered（另有 superseded）
---

# plans/plan-1-xxx.md
---
feature: F12
phase: 1
status: executing     # draft | approved | executing | done | reviewed | closed（另有 abandoned）
---
```

完整格式、跃迁表、矛盾检查在 `workspace-status` 里，以那里为准。

## 四、每份 skill 的构成

一个 skill 就是一段针对 AI 的代码：有输入、有逻辑、有产出、有约束。按这个模型，每份必须有下面几块，缺一块就不合格。

| 元素 | 落在哪 | 说明 |
|---|---|---|
| **目的** | 开头一句 blockquote | 这个节点交付什么判断，不写为什么会有它 |
| **输入与依赖** | `## 输入与依赖`（有前置状态与开工先读）/ `## 什么时候用`（通用能力） | 前置状态、开工先读的文件清单、编号等外部输入的来源 |
| **本节点负责的状态** | `## 本节点负责的状态` | 从哪个状态到哪个状态、条件是什么；只有 spec / plan 单列一节，其余在退出判据末尾写明置什么状态 |
| **逻辑** | 正文各节 | 有迭代的（spec / plan）写成「规范 + 指导思路 + 参考样式」——规范列产出必须满足的性质，指导思路讲怎么想（不写步骤），节次只作样式；有真实先后的写成 `## 流程`，其下每步一个子节 |
| **产出** | 步骤内就地写明 | 落到哪个文件、什么节、什么格式；模板放 `assets/` |
| **约束** | `## 不做的事` | 越界动作与常见自我说服 |
| **退出判据** | `## 定稿`（一致性检查 + 门禁动作）或 `## 退出判据` | 怎么算做完，必须可判定；检查项要逐条可答 |
| **参考** | `references/`、`scripts/`、`assets/` | 见下 |

三处目录各装什么，按平台约定：

| 目录 | 装什么 | 本套件里 |
|---|---|---|
| `scripts/` | 可执行代码，跑起来比让模型照做可靠 | 状态推导、骨架初始化、引文定位 |
| `references/` | 读入上下文供判断的材料 | 语言检查清单、结构判据库 |
| `assets/` | 会被复制进产物的模板 | spec / plan / dev 四份文档模板 |

**结构纪律：有真实先后的用 `## 流程` 容器，没有的不用。**

判据：**这一步不做完，能不能做下一步？** 不能就按流程写，流程下每步一个子节，顺次做完即达目的。能就别套——spec 与 plan 是按缺口反复补，research 的两类材料谁先谁后都行，给它们编顺序等于造出并不存在的约束。容器只是归属，不要在流程下再写一遍步骤概略，那与子节标题逐条重复。

**内容纪律：只写执行时用得上的东西。**

设计理由、为什么会有这个节点、它与旧版的区别、它在整套体系里的位置——这些在执行时全部无用，属于 `WORKFLOW-DESIGN.md` 的内容，不写进 skill。判据：**删掉这句，执行行为会不会变？** 不会就删。

保留例外只有一种：理由会直接改变执行判断。比如「跑全套判据对找漏删无效」留着，因为它挡的是「干脆全跑一遍」这个错误动作；而「它相比旧设计更简洁」删掉，因为执行时没人需要知道。

**description 目的先行。** 首句说清这一步达成什么，不写体系内部的概念——「复核层一与层二」「需求层核验」这类说法只有读过 `WORKFLOW-DESIGN.md` 的人才懂，而 description 是给没读过的人看的，它决定这个 skill 会不会被选中。触发词保留用户原话，那部分是索引，不算文风问题。

**依赖纪律：节点可以依赖「通用能力」，不可以依赖「兄弟节点」。**

| 可以依赖 | 不可以依赖 |
|---|---|
| `research`、`grill-me`（能力，谁都能用） | 别的节点头（`plan-generation`、`code-review`……） |
| `workspace-status`（唯一的入口，用于取下一步与退回规则） | 兄弟节点的内部约定、它下一步会做什么 |

判据：**一个节点如果被删掉或改名，其他节点是否要跟着改？** 要改就说明依赖错了——编排关系只该存在于 `workspace-status` 里。节点之间靠「状态」通信，不靠调用。

## 五、脚本

能判定的步骤用脚本，不靠模型照做——判据见 `WORKFLOW-DESIGN.md` 第二节。脚本放在 `<skill>/scripts/`，`SKILL.md` 里写清怎么运行。

**脚本失败就报错，不预写备用路径。** 非零退出和异常栈本身就是可感知的信号，届时按 `SKILL.md` 正文判断即可。预写一套手工步骤等于维护第二份实现，而它会与脚本悄悄不一致，且没人检查这种不一致。

## 六、各 skill 的附带文件

| skill | 层 | 附带文件 |
|---|---|---|
| `workspace-init` | 工作区 | `scripts/init.py`、`assets/` 四份模板 |
| `workspace-status` | 工作区 | `scripts/status.py` |
| `spec-generation` | 节点 R1 | `assets/spec.md.template` |
| `plan-generation` | 节点 R2 | `assets/plan.md.template`、`references/structure-rules.md`、`scripts/structure-probe.py` |
| `tdd` | 节点 R3 | — |
| `code-review` | 节点 R4 | `references/lang-checklist.md`、`scripts/locate.py` |
| `code-slim-audit` | 节点 R5 | — |
| `spec-verify` | 节点 R6 | — |
| `research` | 通用能力 | — |
| `grill-me` | 通用能力 | — |
