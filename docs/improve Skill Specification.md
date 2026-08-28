# `/improve` Skill Specification

## 1. Purpose

`/improve` 用于在 `/design` 已经完成以后，对已经确认的 implementation design 进行一次独立、对抗性的再次检查，并将有价值的改进直接整合回原 design。

它的核心目标是：

> 在正式进入 `/implement` 之前，通过独立重新审查设计、必要的项目调查和验证，发现 `/design` 阶段遗漏或可以进一步优化的问题，并把最终 design 提升到更可靠、更简单、更完整、更适合实现的状态。

`/improve` 主要回答：

```text
当前 design 是否真的已经足够好？
有没有遗漏的重要问题？
有没有不必要的复杂度？
有没有更简单或更可靠的实现方式？
有没有与真实项目不一致的假设？
有没有遗漏的模块、数据流或边界情况？
有没有潜在的兼容性、错误处理或维护风险？
Testing 是否覆盖了真正重要的行为？
是否存在实现时很可能导致返工的问题？
是否存在多个 Agent 独立发现的风险？
```

`/improve` 不只是：

```text
review the document
```

而是：

```text
review
↓
investigate
↓
validate
↓
decide
↓
improve the design
```

---

## 2. Position in the Workflow

完整工作流为：

```text
/discuss
↓
/design
↓
/improve
↓
/implement
↓
/review
```

每个 Skill 独立执行。

`/improve` 完成后不得自动进入 `/implement`。

用户需要手动调用：

```text
/implement
```

才能继续下一阶段。

---

## 3. Boundary with `/design`

`/design` 的职责是：

```text
形成 Agent 当前认为：
合理
完整
真实
可执行
可以指导 implementation

的 implementation design。
```

因此 `/design` 不得：

```text
故意留下问题等待 /improve
降低 design 的质量要求
把自己不确定的部分直接丢给 /improve
```

`/improve` 的职责是：

```text
在一个已经完整的 design 基础上
重新独立寻找进一步改进的空间
```

因此：

```text
/design
=
produce a strong design

/improve
=
challenge and improve that strong design
```

`/improve` 不是 `/design` 的收尾阶段。

---

## 4. Boundary with `/discuss`

`/improve` 不负责重新决定：

```text
Goal
Scope
Expected behavior
User-visible behavior
Requirement
Important constraint
Compatibility requirement
High-level product direction
```

这些属于 `/discuss`。

如果 `/improve` 发现新的项目事实，导致已经确认的需求或高层方向可能不再成立：

```text
发现新事实
↓
确认它确实影响 Requirement 或高层方向
↓
说明发现
↓
说明为什么原 Decision 可能有问题
↓
停止 /improve
↓
要求重新运行 /discuss
```

不得在 `/improve` 中直接重新决定这些内容。

---

## 5. Boundary with `/implement`

`/improve` 可以：

```text
调查代码
调查配置
调查测试
调查 Git history
分析实现方式
验证关键技术假设
通过隔离 prototype 验证 design
修改 design 文档
```

但不得：

```text
正式实现功能
修改正式业务代码
完成 production implementation
把 prototype 留作正式实现
commit implementation
push implementation
创建 implementation PR
```

`/improve` 的正式产物仍然是：

```text
improved design
```

不是：

```text
implementation
```

---

## 6. Boundary with `/review`

`/improve` 审查的是：

```text
implementation design
```

`/review` 审查的是：

```text
actual implementation
```

因此：

```text
/improve
→ implementation 之前

/review
→ implementation 之后
```

即使 `/improve` 进行了 prototype 验证，也不能认为：

```text
design validated
=
implementation correct
```

最终代码的：

```text
correctness
regression
code quality
design compliance
security problems
performance problems
implementation mistakes
```

仍然属于 `/review`。

---

## 7. Start Condition

`/improve` 的正式输入必须是一份：

```yaml
status: confirmed
```

的 design。

启动 `/improve` 后，Agent 必须首先找到当前任务对应的 design，并检查其状态。

允许：

```text
status: confirmed
→ 进入 /improve
```

不允许：

```text
status: draft
→ 继续 /improve
```

如果 design 仍然是 `draft`：

```text
停止
↓
指出 design 尚未完成确认
↓
要求先完成 /design
```

---

## 8. Why Confirmed Design Is Required

`/improve` 必须建立在一个稳定设计基线上。

如果允许直接处理尚未确认的 draft：

```text
/design
和
/improve
```

的职责会混合。

正确关系是：

```text
/design
↓
完成当前 Agent 认为最合理的设计
↓
用户确认
↓
status: confirmed
↓
/improve
↓
重新独立挑战该设计
```

因此：

> `/improve` 不负责帮助 `/design` 完成一个还没有完成的 design。

---

## 9. Design Discovery

如果用户没有明确提供 design 文件路径，Agent 应根据：

```text
当前任务
当前对话
当前工作区
design 目录
最近相关 design
```

寻找对应的 confirmed design。

不得仅根据：

```text
文件时间最近
文件名看起来相似
```

就静默选择。

如果存在多个可能对应当前任务的 confirmed design，并且无法可靠确定目标：

```text
指出候选 design
↓
让用户确认目标
```

不得改错文件。

---

## 10. Improve the Existing Design

`/improve` 必须直接修改原 design 文件。

例如：

```text
docs/designs/2026-08-28-user-search.md
```

运行 `/improve` 后仍然修改：

```text
docs/designs/2026-08-28-user-search.md
```

不得创建：

```text
2026-08-28-user-search-improved.md
2026-08-28-user-search-v2.md
2026-08-28-user-search-final.md
2026-08-28-user-search-final-final.md
```

同一个 design 生命周期只有一个当前权威文件。

---

## 11. Status Transition

`/improve` 的输入为：

```yaml
status: confirmed
```

在 Agent **实际开始修改 design 文件之前**，必须把状态改为：

```yaml
status: draft
```

之后：

```text
improve design
↓
完成验证
↓
请求用户重新确认
↓
用户确认
↓
status: confirmed
```

原因是：

> 用户之前确认的是修改前的 design，不是 `/improve` 修改后的内容。

因此 design 内容变化以后，不得继续保留：

```yaml
status: confirmed
```

---

## 12. Read Before Improve

`/improve` 不得看到 design 后立即开始重写。

必须先理解：

```text
Goal
Requirements
Implementation Approach
File Changes
Testing
所有适用的可选章节
已经确认的重要 Technical Decision
已经确认的 trade-off
已有兼容性要求
已有验证结果
```

并理解 design 中不同内容的来源：

```text
Requirement
Project Fact
Prototype-validated Fact
Technical Decision
Assumption
```

---

## 13. Investigate the Real Project

`/improve` 不只审查 Markdown 文本。

Agent 可以并且应该在有需要时调查真实项目。

可以调查：

```text
项目结构
相关模块
相关页面
相关组件
相关 service
API
database schema
类型
配置
测试
package metadata
项目文档
Git history
类似功能
已有 abstraction
已有 design pattern
当前分支
当前工作区修改
```

目标是验证：

```text
design 描述的系统是否真实存在
design 是否遗漏相关实现
design 的假设是否成立
建议是否与项目架构兼容
```

---

## 14. Do Not Reinvestigate Everything

允许调查真实项目，不代表每次 `/improve` 都需要重新研究整个仓库。

调查应围绕：

```text
当前 design
+
潜在改进点
+
会影响判断的重要事实
```

例如：

```text
某个建议依赖权限系统现状
→ 调查权限系统

某个建议依赖缓存行为
→ 调查缓存实现

某个建议与数据库无关
→ 不需要完整研究 database schema
```

原则：

> Investigate enough to make the improvement reliable, but do not restart `/design` from zero.

---

## 15. Working Tree Awareness

`/improve` 调查项目时必须考虑：

```text
当前 branch HEAD
+
当前工作区中的未提交修改
```

当前未提交修改可能已经改变：

```text
相关模块
接口
类型
测试
数据流
配置
```

因此不能因为未 commit 就忽略。

---

## 16. Protect User Work

`/improve` 不得为了调查或验证：

```text
stash 用户修改
reset 用户修改
clean 用户文件
覆盖用户修改
强制 checkout
切换用户当前 worktree 的 branch
删除未跟踪文件
恢复用户没有要求恢复的文件
```

用户当前工作状态必须保持安全。

---

## 17. Multi-Agent First

如果当前环境支持 subagent，`/improve` 默认优先使用多个 Agent 并行审查。

默认：

```text
3 个 Agent
```

最大：

```text
5 个 Agent
```

规则：

```text
用户没有指定
→ 默认 3 个

用户指定 1 到 5
→ 使用用户指定数量

用户指定超过 5
→ 最多使用 5 个

环境可用 Agent 少于目标数量
→ 使用实际可用数量

环境完全不支持 subagent
→ 主 Agent 单独完成完整 /improve
```

不得因为没有 subagent 就拒绝执行整个 `/improve`。

---

## 18. Independent Agents

所有并行 Agent 必须独立工作。

结构：

```text
confirmed design
        ↓
 ┌──────┼──────┐
 ↓      ↓      ↓
Agent 1 Agent 2 Agent 3
 ↓      ↓      ↓
独立调查
独立分析
独立判断
独立提出建议
 └──────┼──────┘
        ↓
     Main Agent
```

subagent 之间不得：

```text
读取彼此输出
互相讨论
在另一个 Agent 的建议上继续改写
提前形成共识
```

主 Agent 是第一个统一读取所有审查结果的 Agent。

---

## 19. Same Review Problem

多个 Agent 不采用固定角色分工。

不得预先固定：

```text
Agent 1 = correctness
Agent 2 = architecture
Agent 3 = edge cases
Agent 4 = performance
Agent 5 = maintainability
```

每个 Agent 都应该独立审查完整 design。

它们都应尝试发现：

```text
correctness problems
missing requirements
architecture problems
unnecessary complexity
simpler alternatives
incorrect project assumptions
missing affected modules
bad abstractions
edge cases
compatibility problems
error-handling gaps
data-flow problems
control-flow problems
migration risks
security concerns
performance concerns
maintainability problems
testing gaps
implementation risks
likely rework
```

具体关注点根据当前 design 自然变化。

---

## 20. Do Not Force Categories

上面的检查方向不是固定 checklist。

Agent 不得为了完整而机械输出：

```text
Correctness: no issue
Security: no issue
Performance: no issue
Migration: N/A
Caching: N/A
Concurrency: N/A
```

如果某个方向与当前 design 无关：

```text
忽略
```

不是：

```text
强行检查并输出空结论
```

---

## 21. Agent Prompt Principle

subagent 的任务本质上应接近：

```text
Independently review this confirmed implementation design.

Investigate the real project where useful.

Find meaningful ways to improve the design before implementation.

Do not assume the design is correct.
Do not change confirmed product requirements.
Do not implement the feature.
Return only improvements that could materially improve the design.
```

不同平台可以根据能力调整具体 prompt。

Skill 不应依赖某一段完全固定的 prompt 文本。

核心要求是：

```text
同一个完整问题
+
独立判断
+
允许调查项目
+
寻找实质性改进
```

---

## 22. Adversarial Review Mindset

subagent 不应默认：

```text
/design 已确认
=
design 一定正确
```

它们应该尝试挑战 design。

例如：

```text
这个 abstraction 真有必要吗？
是否遗漏已有机制？
是否在重复项目已经存在的能力？
是否引入了不必要的新 subsystem？
文件范围是否遗漏？
数据流是否真实？
是否存在更简单的实现？
是否存在隐含兼容性问题？
Testing 是否验证了真正关键行为？
```

但“对抗性”不代表：

```text
为了找问题而找问题
为了不同而提出替代方案
必须推翻 design
必须增加复杂度
```

如果 design 已经合理，可以明确：

```text
没有发现值得修改的实质问题
```

---

## 23. Meaningful Improvement Only

只有会实际改善以下至少一项的建议才值得进入主 Agent 的候选集合：

```text
Correctness
Completeness
Simplicity
Consistency
Maintainability
Implementation feasibility
Compatibility
Reliability
Security
Performance
Testability
Risk reduction
Implementation clarity
```

不应采纳纯风格型建议，例如：

```text
换一个标题名字
重新排列没有实际影响的段落
增加更多解释但不提升 implementation readiness
使用 Agent 更个人偏好的 abstraction
把简单设计改得更“高级”
```

---

## 24. Simplicity Is an Improvement

`/improve` 不只是寻找：

```text
还缺什么？
```

也必须寻找：

```text
什么可以删除？
什么可以简化？
什么 abstraction 没有必要？
什么未来扩展是过度设计？
什么内容实际上可以复用现有系统？
```

因此改进可能是：

```text
增加内容
修改内容
删除内容
简化方案
减少文件
减少 abstraction
减少依赖
减少状态
减少特殊情况
```

---

## 25. Main Agent Aggregation

所有 subagent 完成后，主 Agent 负责：

```text
读取全部结果
↓
识别重复建议
↓
合并相同问题
↓
区分事实与判断
↓
检查建议是否违反 Requirement
↓
检查建议是否改变高层方向
↓
识别建议之间的冲突
↓
识别普通 Technical Decision
↓
识别重大 Technical Decision
↓
确定哪些建议值得进入 design
```

不得把多个 subagent 的输出简单拼接后直接写入 design。

---

## 26. Repeated Findings

如果多个 Agent 独立发现同一个问题：

```text
这是提高该问题优先级的信号
```

但：

```text
出现次数
≠
自动正确
```

主 Agent 仍应判断：

```text
问题是否真实
是否适用于当前项目
是否会实质改善 design
```

不得使用纯多数投票替代技术判断。

---

## 27. Substantive Conflicts

如果多个 Agent 对同一个**重要改进点**存在实质性冲突，主 Agent不得自行选择一个方向。

例如：

```text
Agent 1:
应该拆出新的 subsystem

Agent 2:
应该继续复用现有 subsystem
```

并且两者会造成明显不同的：

```text
架构
复杂度
长期维护方式
实现范围
接口
数据模型
兼容性
```

则：

```text
整理冲突
↓
确认双方依据
↓
说明关键 trade-off
↓
给出主 Agent 推荐
↓
请求用户决定
↓
等待确认
```

不得：

```text
按 Agent 数量投票
随机选择
静默采用主 Agent 偏好的方案
```

---

## 28. Non-Substantive Differences

如果多个 Agent 只是：

```text
措辞不同
实现细节表达不同
强调重点不同
```

但最终技术方向相同，则不属于实质冲突。

主 Agent 可以自行合并。

例如：

```text
Agent 1:
validation 应放在现有 service 层

Agent 2:
复用当前 service validation

```

如果两者实际上表达同一方案，则可以合并成一个改进点。

---

## 29. Requirement Changes Are Not Improvements

如果某个建议实际上要求改变：

```text
功能目标
用户行为
scope
兼容要求
权限要求
产品方向
用户可见结果
```

它不属于普通 `/improve` 建议。

流程：

```text
识别 Requirement-level change
↓
不要写入 design
↓
说明为什么它改变了已确认需求
↓
停止 /improve
↓
要求重新运行 /discuss
```

不得因为多个 Agent 都推荐，就绕过 `/discuss`。

---

## 30. High-Level Direction Changes

如果改进建议需要改变已经在 `/discuss` 确认的高层方向，例如：

```text
原方向：
扩展现有权限体系

新建议：
建立新的权限 subsystem
```

应先判断这究竟属于：

```text
implementation-level architecture
```

还是：

```text
high-level product / system direction
```

如果属于后者：

```text
返回 /discuss
```

不得由 `/improve` 自行决定。

---

## 31. Ordinary Technical Decisions

普通、低风险、可逆的 implementation-level Technical Decision，可以由主 Agent直接调整。

例如：

```text
复用现有 helper
调整模块内部职责
减少不必要的 abstraction
调整 validation 所在层
更合理地使用项目已有 pattern
修正 File Changes
补充遗漏的边界行为
完善 Testing
调整低成本实现顺序
```

只要这些修改：

```text
不改变 Requirement
不改变高层方向
不形成重大长期 trade-off
```

就不需要逐项询问用户。

---

## 32. Major Technical Decisions

如果 `/improve` 提出的修改属于重大 Technical Decision，则必须由用户确认。

包括但不限于：

```text
引入新的核心 subsystem
引入重要 dependency
显著改变架构边界
形成新的长期技术路线
显著增加系统复杂度
产生明显长期维护成本
难以回滚
存在重要 trade-off
影响兼容性
显著改变数据模型
显著改变关键接口
```

流程：

```text
发现重大 Technical Decision
↓
调查事实
↓
说明当前 design
↓
说明 proposed improvement
↓
说明关键 trade-off
↓
给出推荐
↓
请求用户确认
↓
等待
```

用户确认后才能写入 design。

---

## 33. Do Not Reopen Decisions Without Evidence

`/improve` 的目的不是重新把所有 `/design` Decision 讨论一遍。

已经确认的技术方向不得仅因为：

```text
另一个 Agent 更喜欢另一种写法
另一个 abstraction 看起来更漂亮
某个模式更符合所谓 best practice
```

就重新打开。

重新挑战一个已确认 Decision 应至少有：

```text
新的项目事实
新的技术限制
遗漏的重要依赖
明显风险
明显复杂度问题
兼容性问题
实现不可行性
可验证的更优方案
```

---

## 34. Fact vs Suggestion

主 Agent 必须区分：

```text
Project Fact
Prototype-validated Fact
Agent Observation
Technical Suggestion
Requirement Change
Major Technical Decision
Assumption
```

例如：

```text
“当前 service 已经处理权限”
```

属于 Fact。

```text
“因此应该继续复用该 service”
```

属于 Technical Suggestion。

这两者不得混为一谈。

---

## 35. No Silent Assumptions

subagent 或主 Agent 的推断不得静默变成 design 中的事实。

如果一个建议依赖某个关键假设：

```text
先尝试调查
```

如果仍然无法确认，并且该假设会明显影响 design：

```text
进行必要验证
或
明确暴露未知项
```

不得直接写成确定事实。

---

## 36. Prototype Validation

`/improve` 允许通过 prototype 验证重要建议。

prototype 的唯一目的包括：

```text
验证某个改进方案是否可行
确认第三方行为
确认接口兼容性
验证架构假设
确认真实 runtime behavior
验证会影响 design 的技术事实
降低重要不确定性
```

prototype 是：

```text
design validation
```

不是：

```text
early implementation
```

---

## 37. When Prototype Is Worthwhile

不得为了“更保险”而对所有建议编写 prototype。

只有当：

```text
问题无法通过静态调查确认
+
结果会明显影响是否修改 design
```

时才应该进行实验。

典型情况：

```text
第三方 library 行为不明确
接口兼容性无法从文档确认
runtime 行为会改变架构选择
性能特征会决定方案是否成立
当前 abstraction 的限制只能通过运行验证
```

---

## 38. Prototype Isolation

所有会修改代码的验证必须与用户当前工作区隔离。

可以根据环境使用：

```text
git worktree
临时 branch
临时 clone
独立目录
其他安全隔离方式
```

Skill 不要求固定使用其中某一种。

核心要求只有一个：

> 用户当前工作区不得因为 `/improve` prototype 发生变化。

---

## 39. Prototype Base

默认 prototype 应基于：

```text
当前 branch HEAD
```

而不是：

```text
main
master
默认 branch
远程最新 commit
```

因为 `/improve` 应验证的是当前用户真正准备实现的设计环境。

---

## 40. Relevant Uncommitted Changes

如果当前工作区存在与 design 相关的未提交修改，并且这些修改会影响 prototype 的有效性：

```text
创建隔离环境
↓
复制与当前 design 相关的必要修改
↓
进行验证
```

不得：

```text
无条件复制整个工作区
忽略明显相关的未提交修改
修改用户原工作区
```

---

## 41. Prototype Cleanup

所有 `/improve` prototype 必须在结束前清理。

包括：

```text
临时代码
临时文件
实验配置
临时 branch
临时 worktree
临时 clone
实验生成物
```

不得把 prototype：

```text
保留给 /implement
提交到正式项目
作为 implementation 起点
```

正式代码必须由 `/implement` 完成。

---

## 42. What to Improve in the Design Document

`/improve` 可以根据发现修改 design 中任何 implementation-level 内容，例如：

```text
Implementation Approach
File Changes
Data Flow
Control Flow
Interface Changes
Data Model Changes
Error Handling
Compatibility
Migration
Security
Performance
Concurrency
Caching
Dependencies
Implementation Order
Testing
Validation
```

前提是这些修改不越过 `/discuss` 的边界。

---

## 43. Preserve Design Style

改进 design 时应保持 `/design` 已建立的文档原则。

最终 design 应：

```text
只保留最终采用方案
保持 implementation-oriented
基于真实项目
避免无关 brainstorming
避免决策过程流水账
避免重复
避免不必要细节
删除无意义章节
保持简单任务简单
```

`/improve` 不应因为进行了多 Agent 审查，就把所有 Agent 的思考过程写进正式 design。

---

## 44. Do Not Record Review History by Default

正式 design 不应记录：

```text
Agent 1 建议了什么
Agent 2 不同意什么
Agent 3 为什么选择另一种方案
多 Agent 投票结果
完整 review transcript
所有 rejected suggestions
```

最终 design 仍然描述：

```text
最终应该如何实现
```

而不是：

```text
Agent 是怎么讨论出来的
```

如果某个重大 trade-off 对理解最终方案长期重要，可以保留必要的决策说明，但不得记录完整讨论过程。

---

## 45. Update Only What Needs Improvement

`/improve` 不应为了制造“改进感”而全面重写 design。

如果原 design 某部分已经准确：

```text
保留
```

如果只是一个章节需要改：

```text
只改相关章节
```

目标是：

```text
meaningful improvement
```

不是：

```text
maximum textual change
```

---

## 46. Testing Review

`/improve` 必须检查 Testing 是否覆盖 design 中真正重要的行为。

重点检查：

```text
核心 expected behavior
权限边界
错误路径
兼容性
旧行为回归
重要数据变化
关键状态变化
重要 edge case
migration 后行为
重要 integration
```

但仍然不需要提前写：

```text
具体测试函数
具体 assertion
完整测试代码
每条命令
```

这些属于 `/implement`。

---

## 47. File Changes Review

`/improve` 应检查 `File Changes`：

```text
文件路径是否真实
是否遗漏受影响文件
是否包含其实不需要改的文件
每个文件职责是否准确
文件之间依赖是否清楚
是否存在更简单的修改范围
是否过早规定低层 symbol
```

如果建议增加新文件：

```text
必须有真实设计需要
```

不能因为某种 framework convention 就自动增加。

---

## 48. Architecture Review

对于 architecture，应重点判断：

```text
是否复用已有 subsystem
是否重复已有 abstraction
是否新增不必要层级
职责是否放在正确边界
模块耦合是否被不必要增加
是否产生循环依赖
是否让未来 implementation 更难
是否为了假想需求过度设计
```

原则：

> Prefer the simplest design that fully satisfies the confirmed requirements and fits the real project.

---

## 49. Compatibility Review

如果 design 涉及：

```text
旧 API
旧数据
旧配置
已有客户端
已有 URL
已有数据库
已有用户行为
```

`/improve` 应检查兼容策略是否真实、完整。

不得因为“新设计更干净”而静默破坏已经确认的兼容要求。

---

## 50. Dependency Review

`/improve` 应识别：

```text
模块依赖
数据依赖
执行顺序
migration 依赖
external dependency
runtime dependency
配置依赖
```

并检查 design 是否正确表达这些关系。

design 不应只是：

```text
一组互不相关的文件修改列表
```

而应反映真实实现依赖。

---

## 51. Remove Overengineering

如果发现 design 存在：

```text
没有需求依据的扩展点
未来可能用到但当前不需要的 abstraction
没有真实 use case 的通用化
不必要的 dependency
不必要的 subsystem
不必要的 configuration
不必要的 compatibility layer
```

`/improve` 应优先考虑删除。

不得默认认为：

```text
更通用
=
更好
```

---

## 52. Completion Validation

修改完成后，主 Agent 必须重新检查完整 design。

至少确认：

```text
仍然满足全部 confirmed Requirements
没有改变已确认 scope
没有改变用户可见行为
没有静默改变高层方向
关键项目事实有依据
重大 Technical Decision 已得到用户确认
Agent 冲突已经解决
没有引入新的明显矛盾
没有遗漏新的依赖
File Changes 与方案一致
Testing 与最终方案一致
prototype 已清理
用户工作区安全
design 当前内容完整
```

---

## 53. Final Confirmation

`/improve` 不得在 Agent 自己认为修改完成后直接结束。

流程：

```text
完成改进
↓
完成必要验证
↓
清理 prototype
↓
重新检查 design
↓
保持：
status: draft
↓
向用户概括重要改进
↓
请求最终确认
↓
等待用户
```

---

## 54. User Feedback

用户可以：

```text
确认
要求撤销某项改进
要求继续修改
指出遗漏
否定某个 Technical Decision
增加新的约束
改变 Requirement
```

如果反馈仍属于 implementation design：

```text
更新同一个 design 文件
↓
必要时重新调查
↓
必要时重新验证
↓
重新检查
↓
再次请求确认
```

如果反馈改变需求或高层方向：

```text
停止 /improve
↓
要求返回 /discuss
```

---

## 55. Confirmed Status

只有用户明确确认当前 improved design 后：

```yaml
status: confirmed
```

此时 `/improve` 才正式完成。

不得因为：

```text
所有 Agent 都完成了
没有更多建议
prototype 成功
design 已修改
主 Agent 认为方案很好
```

就自动设置为 `confirmed`。

---

## 56. No-Change Result

`/improve` 不要求每次都必须修改 design。

如果：

```text
多个独立 Agent 已审查
必要项目事实已调查
没有发现值得采用的实质改进
```

则可以得出：

```text
当前 design 不需要修改
```

在这种情况下：

```text
原文件保持不变
status 保持 confirmed
```

不应为了证明 `/improve` 做过工作而制造无意义修改。

---

## 57. Partial Improvement Is Not Completion

如果仍然存在：

```text
未解决的重大 Technical Decision
Agent 之间的重要实质冲突
阻塞性的关键未知项
未完成的重要 prototype
需求层冲突
高层方向冲突
```

则 `/improve` 不能完成。

必须先解决对应问题。

---

## 58. Final Output

`/improve` 完成时，应简洁说明：

```text
design 文件路径
是否发生修改
最重要的改进
重要技术 Decision，如果有
验证过的重要事实，如果有
最终 status
```

不需要：

```text
复制完整 design
列出每个 Agent 的完整输出
展示内部分析过程
展示所有 rejected suggestions
```

---

## 59. Prohibited Behaviors

### 禁止处理未确认的 design

`status` 不是 `confirmed` 时，不得开始正式 `/improve`。

---

### 禁止把 `/improve` 变成第二次 `/design`

不得从零重新设计整个功能，只因为可以想到另一套方案。

---

### 禁止重新承担 `/discuss`

Requirement、scope 和高层方向变化必须返回 `/discuss`。

---

### 禁止擅自改变已确认需求

任何改进都必须服从 confirmed Requirements。

---

### 禁止擅自改变高层方向

高层方向只能在新的事实证明原方向存在问题时被挑战，并且应返回 `/discuss`。

---

### 禁止擅自决定重大 Technical Decision

重大架构和长期 trade-off 必须由用户确认。

---

### 禁止主 Agent 静默裁决重要 Agent 冲突

实质冲突必须交给用户决定。

---

### 禁止使用多数投票替代技术判断

多个 Agent 同意不代表自动正确。

---

### 禁止让 subagent 互相影响

并行 Agent 必须独立工作。

---

### 禁止固定角色导致审查视角被限制

每个 Agent 都必须完整审查 design。

---

### 禁止只审查文字不看项目事实

当建议依赖真实项目状态时，应进行必要调查。

---

### 禁止为了完整重新研究整个仓库

调查必须围绕当前 design 和实际改进问题。

---

### 禁止凭 framework 经验猜项目

文件、模块、API 和行为应来自真实调查。

---

### 禁止为了“改进”强行修改

没有实质问题时可以不修改。

---

### 禁止无意义重写

已经正确的 design 内容应尽量保留。

---

### 禁止增加无需求依据的复杂度

不得为了所谓 future-proof、best practice 或 abstraction purity 过度设计。

---

### 禁止把所有 subagent 建议写进 design

subagent 输出只是候选意见。

---

### 禁止记录完整审查过程

正式 design 应记录最终方案，而不是 Agent conversation。

---

### 禁止静默接受未经验证的重要假设

重要假设应调查、验证或明确暴露。

---

### 禁止 prototype 变成 implementation

实验代码只能用于设计验证。

---

### 禁止影响用户当前工作区

不得 stash、reset、clean、覆盖或删除用户工作。

---

### 禁止保留 prototype

实验完成后必须清理。

---

### 禁止创建 improved design 副本

修改原 design 文件。

---

### 禁止内容变化后继续保留 `confirmed`

实际修改开始后必须转为：

```yaml
status: draft
```

---

### 禁止未经用户重新确认结束

修改后的 design 必须重新得到用户确认。

---

### 禁止自动进入 `/implement`

`/improve` 完成后停止。

下一步由用户手动运行：

```text
/implement
```

---

## 60. Recommended Execution Flow

完整流程：

```text
用户运行 /improve
↓
确定当前任务对应的 design
↓
读取 design
↓
检查：
status: confirmed
↓
否
└── 停止
    ↓
    要求完成 /design

是
↓
理解 Goal / Requirements / Implementation Approach / File Changes / Testing
↓
理解已有重要 Technical Decision
↓
检查当前 branch HEAD
↓
检查相关未提交修改
↓
确定并行 Agent 数量
├── 用户指定 1-5
│   └── 使用指定数量
├── 用户未指定
│   └── 默认 3
├── 环境可用数量不足
│   └── 使用实际可用数量
└── 不支持 subagent
    └── 主 Agent 单独执行
↓
向多个 Agent 独立提供同一完整审查任务
↓
每个 Agent：
    读取完整 design
    ↓
    按需调查真实项目
    ↓
    独立寻找实质改进
    ↓
    独立返回建议
↓
主 Agent 收集全部结果
↓
去重和合并
↓
识别：
Fact
Suggestion
Requirement Change
Ordinary Technical Decision
Major Technical Decision
Assumption
Conflict
↓
发现 Requirement / 高层方向问题？
├── 是
│   └── 说明问题
│       ↓
│       停止 /improve
│       ↓
│       要求返回 /discuss
│
└── 否
    ↓
检查 Agent 之间是否存在重要实质冲突
├── 是
│   └── 整理方案和 trade-off
│       ↓
│       给出推荐
│       ↓
│       请求用户决定
│       ↓
│       等待
│
└── 否
    ↓
检查是否存在重大 Technical Decision
├── 是
│   └── 调查事实
│       ↓
│       给出方案、trade-off 和推荐
│       ↓
│       请求用户决定
│       ↓
│       等待
│
└── 否
    ↓
识别需要验证的重要建议
↓
可以静态确认？
├── 是
│   └── 调查项目
│
└── 否
    ↓
    是否值得 prototype？
    ├── 否
    │   └── 不把未经验证的重要假设写成事实
    │
    └── 是
        ↓
        创建隔离环境
        ↓
        复制必要的相关未提交修改，如果需要
        ↓
        进行最小 prototype
        ↓
        获取验证结果
        ↓
        清理 prototype
↓
确定最终要采用的改进
↓
如果没有实质改进
├── 保持原文件不变
├── 保持 status: confirmed
└── /improve 完成
↓
如果需要修改
↓
将原 design：
status: confirmed
改为：
status: draft
↓
直接更新同一个 design 文件
↓
不创建 improved 副本
↓
重新验证：
Requirements
Architecture
File Changes
Dependencies
Compatibility
Testing
Assumptions
Conflicts
↓
确认所有 prototype 已清理
↓
确认用户当前工作区没有被实验影响
↓
向用户概括重要改进
↓
请求最终确认
├── 用户要求修改
│   └── 更新同一个 design
│       ↓
│       必要时重新调查或验证
│       ↓
│       再次请求确认
│
├── 用户改变 Requirement / 高层方向
│   └── 停止 /improve
│       ↓
│       返回 /discuss
│
└── 用户确认
    ↓
    更新：
    status: confirmed
    ↓
    /improve 完成
```

---

## 61. Mental Model

`/improve` 不应该像：

```text
重新写一遍 design
```

也不应该像：

```text
让几个 Agent 投票选方案
```

也不应该像：

```text
生成一份 design review 报告后结束
```

更接近：

```text
Start from a confirmed design
↓
Independently challenge it
↓
Use multiple independent agents when available
↓
Investigate the real system where needed
↓
Separate facts from suggestions
↓
Resolve meaningful conflicts
↓
Validate important improvements
↓
Integrate only worthwhile changes
↓
Revalidate the whole design
↓
Get user confirmation again
```

最终目标是：

> 在不重新讨论已确认需求、不提前进行正式实现的前提下，通过独立、多视角、基于真实项目的审查，把已经可以实现的 design 进一步打磨成更可靠、更简单、更完整，并尽可能降低 `/implement` 阶段返工风险的最终设计。