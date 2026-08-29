# `/design` Skill Specification

## 1. Purpose

`/design` 用于在需求已经足够明确以后，调查真实项目状态，并形成一份可以直接指导 `/implement` 的实现设计。

它的核心目标是：

> 在正式实现之前，把所有会明显影响实现方式的重要技术问题解决清楚，并将最终方案保存为真实、具体、可验证的 design 文档。

`/design` 主要回答：

- 当前项目实际上是如何工作的？
- 已确认需求应该如何落到现有系统中？
- 最终采用什么实现方案？
- 哪些模块和文件需要变化？
- 每个文件承担什么修改职责？
- 关键数据、控制流和模块关系如何变化？
- 是否涉及接口、类型、数据结构或兼容性变化？
- 哪些边界情况必须在实现时处理？
- 实现完成后需要验证什么？
- 当前设计是否真的可行？
- 是否仍然存在会阻碍 `/implement` 的技术未知项？

`/design` 不负责：

- 重新讨论已经明确的产品需求
- 无限制 brainstorming
- 正式实现功能
- 完成最终代码
- commit
- push
- 创建 PR
- 代替 `/improve` 对完整 design 进行独立改进
- 代替 `/review` 审查最终实现

---

## 2. Boundary with `/discuss`

`/discuss` 负责：

```text
What are we building?
Why?
What behavior do we want?
What is in scope?
What is out of scope?
What constraints matter?
What major decisions have been confirmed?
What high-level direction should we follow?
```

`/design` 负责：

```text
How exactly should we implement it?
```

因此：

```text
/discuss
↓
明确需求和高层方向
↓
/design
↓
形成具体实现设计
```

`/design` 可以深入：

```text
模块
文件
组件职责
数据流
控制流
接口
类型
数据结构
兼容性
错误处理
测试目标
实现依赖
```

但不应该重新扩大需求范围。

---

## 3. Design Depth

`/design` 应达到：

```text
关键实现决策已经明确
+
另一个 Agent 可以理解设计并开始实现
+
低层代码细节仍然可以由 /implement 决定
```

即采用：

> Implementation-ready at the architectural and file-responsibility level, but not code-complete.

`/design` 应明确：

- 架构方向
- 模块职责
- 关键数据流
- 关键控制流
- 文件级修改范围
- 接口变化
- 关键类型或数据结构变化
- 兼容性要求
- 重要错误处理
- 关键边界条件
- 测试目标
- 重要实现依赖

`/design` 不需要提前决定：

- 每个变量名
- 每个局部 helper
- 每个函数内部如何逐行实现
- 普通函数如何拆分
- 无关紧要的内部 abstraction
- 具体测试代码
- 每一条测试命令

---

## 4. Start Condition

`/design` 不强制要求之前已经运行 `/discuss`。

启动 `/design` 后，Agent 必须先判断：

```text
当前需求是否已经足够明确，可以进入实现设计？
```

如果已经明确：

```text
直接进入 /design
```

如果仍然存在会明显影响以下内容的需求层 Decision：

- Goal
- Scope
- Expected behavior
- User-visible behavior
- Compatibility requirement
- Important constraint
- High-level product direction

则：

```text
停止 /design
↓
指出具体缺失的需求 Decision
↓
说明为什么它会影响设计
↓
要求先通过 /discuss 解决
```

`/design` 不应该自己变成 `/discuss`。

---

## 5. Investigate Before Designing

`/design` 必须先调查真实项目，再形成方案。

不得：

```text
根据框架经验猜文件路径
根据常见做法猜项目结构
假设某个 API 已经存在
假设某个模块负责某项功能
假设项目使用某种设计模式
```

必须优先调查：

```text
项目结构
相关模块
相关页面
相关组件
现有 API
service
database schema
类型定义
配置
测试
项目文档
package metadata
Git history
类似功能
现有 design pattern
当前工作区修改
```

设计中的事实必须尽可能来自真实项目。

---

## 6. Current State Understanding

在形成设计前，Agent 必须理解：

```text
当前行为是什么
相关代码在哪里
已有 abstraction 是什么
已有依赖关系是什么
当前数据如何流动
当前功能如何被测试
新需求会影响哪些现有行为
```

但这些调查结果不一定全部写进最终 design。

最终文档只保留理解实现方案所必要的信息。

---

## 7. Working Tree Awareness

`/design` 调查项目时必须考虑：

```text
当前分支 HEAD
+
当前工作区中的未提交修改
```

未提交修改可能属于用户正在进行的相关工作，不能因为它们尚未 commit 就忽略。

Agent 不得：

```text
stash 用户修改
reset 用户修改
checkout 覆盖用户修改
clean 用户文件
自动恢复用户工作区
```

---

## 8. Fact vs Technical Decision

`/design` 需要区分：

```text
Fact
Technical Decision
Requirement Decision
```

### 8.1 Fact

Fact 是可以通过项目调查或验证获得的信息。

例如：

```text
某个 API 是否已经存在
某个组件当前在哪里使用
当前 schema 有哪些字段
某个 library 当前版本是什么
现有测试覆盖什么
某个函数实际返回什么类型
```

对于 Fact：

> Agent 应自己调查或验证，不得优先询问用户。

---

### 8.2 Technical Decision

Technical Decision 是多个实现方案都可能满足需求，需要选择工程方向的情况。

例如：

```text
复用现有 service 还是增加 abstraction
同步还是异步处理
扩展现有 subsystem 还是增加新模块
在哪一层进行 validation
如何组织模块职责
```

普通 Technical Decision 默认由 Agent 自行判断。

---

### 8.3 Requirement Decision

如果问题实际上会改变：

```text
功能应该做什么
谁能使用
哪些行为属于 scope
是否兼容旧行为
用户看到什么结果
```

则它不属于 `/design`。

应返回 `/discuss`。

---

## 9. Technical Autonomy

`/design` 不应该因为每一个工程选择都询问用户。

普通工程决策由 Agent 自主完成。

例如：

```text
复用哪个现有 helper
内部模块如何拆分
使用项目已有哪种 pattern
文件内部如何组织
低成本、可逆的技术选择
实现顺序
```

Agent 应根据：

- 当前架构
- 项目约定
- 复杂度
- 可维护性
- 一致性
- 风险
- 当前需求

做出判断。

---

## 10. Major Technical Decisions

如果一个 Technical Decision：

- 会明显改变长期架构
- 会引入新的核心 subsystem
- 会引入重要依赖
- 会显著增加系统复杂度
- 会带来长期维护成本
- 很难回滚
- 存在明显的重要 trade-off
- 会影响兼容性
- 两个方案都会形成不同长期技术路线

则 Agent 不得自行决定。

流程：

```text
识别重大技术 Decision
↓
调查事实
↓
给出合理选项
↓
说明关键 trade-off
↓
给出推荐
↓
询问用户
↓
等待确认
↓
继续 design
```

---

## 11. Challenging `/discuss` Decisions

`/design` 可以发现 `/discuss` 阶段没有发现的新技术事实。

例如：

```text
/discuss 已确认：
继续扩展现有权限系统

/design 调查后发现：
当前权限系统无法合理支持需求
```

此时不得：

```text
静默推翻原 Decision
```

应该：

```text
指出新发现的事实
↓
说明为什么原方向可能不再成立
↓
提出新的高层方向
↓
说明 trade-off
↓
给出推荐
↓
暂停 /design
↓
由用户确认
```

用户确认后再继续。

---

## 12. Do Not Reopen Settled Decisions Without Evidence

已经在 `/discuss` 中确认的需求或高层方向，不得仅因为 Agent 更喜欢另一种方案就重新讨论。

只有存在：

```text
新的项目事实
新的技术限制
明显冲突
不可行性
严重工程风险
```

时才可以挑战已确认 Decision。

---

## 13. Prototype Validation

`/design` 允许编写 prototype。

其目的只能是：

```text
确认重要技术事实
验证方案是否实际可行
确认第三方行为
验证接口兼容性
验证架构假设
降低 design 中的重要不确定性
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

## 14. When to Use a Prototype

Agent 不应该为了“更加保险”而对所有 design 编写 prototype。

只有当某个未知项：

- 无法通过静态调查确认
- 会明显影响最终方案
- 会影响关键接口
- 会影响架构方向
- 会影响兼容性
- 会导致大量返工风险

时，才值得进行实验验证。

---

## 15. Prototype Isolation

所有会修改代码的 design 验证必须与用户当前工作区隔离。

核心要求：

> 用户当前工作区、当前分支和未提交修改不得因为 `/design` 的 prototype 发生变化。

隔离方式不固定。

可以根据环境选择：

```text
临时 Git branch
git worktree
临时 clone
独立目录
其他安全隔离方式
```

不得要求固定使用某一种机制。

---

## 16. Prototype Base

默认 prototype 的代码基础是：

```text
当前分支 HEAD
```

不是：

```text
默认分支
main
master
远程最新 commit
```

例如：

```text
当前分支：
feature/search

HEAD:
abc123

/design prototype
↓
以 abc123 为基础创建隔离环境
```

---

## 17. Uncommitted Changes in Prototype

当前工作区中的未提交修改必须被 `/design` 理解。

如果这些修改会影响当前 design，并且 prototype 需要基于这些修改才能有效验证：

```text
当前 HEAD
↓
创建隔离环境
↓
复制与当前 design 相关的未提交修改
↓
进行验证
```

注意：

> 只复制与当前 design 相关的修改。

不得无条件把整个工作区所有未提交内容复制过去。

---

## 18. Protect User Work

`/design` 不得为了 prototype：

```text
stash 用户工作
reset 用户工作
强制 checkout
删除未跟踪文件
覆盖当前修改
修改用户当前 branch
切换用户当前 worktree 的 branch
```

设计验证必须对用户当前开发状态无侵入。

---

## 19. Prototype Cleanup

所有 prototype 和实验性修改必须在 `/design` 结束前清理。

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

最终不得把 prototype 当作 `/implement` 的起点保留下来。

正式 implementation 必须由 `/implement` 执行。

---

## 20. Cleanup Verification

在 `/design` 即将结束前，Agent 应确认：

```text
用户原工作区没有因为 design 验证发生变化
prototype 已清理
临时环境已清理
临时 branch 已清理，如果创建过
正式项目中只留下允许保留的 design 文档修改
```

如果无法安全确认清理完成，不得宣称 `/design` 已完成。

---

## 21. Design Document

`/design` 的正式产物是 Markdown design 文档。

Design 必须：

- 基于真实项目
- 与当前代码状态一致
- 与已确认需求一致
- 足够具体
- 可以指导 `/implement`
- 不包含未经说明的重要猜测
- 不提前实现代码
- 不包含无关 brainstorming

---

## 22. Design Storage

优先使用项目已有的 design 文档目录。

Agent 应调查仓库是否已经存在类似：

```text
docs/designs/
docs/design/
design/
designs/
docs/rfcs/
rfcs/
architecture/
```

如果项目已有明确 design 文档约定：

```text
使用现有目录
```

如果没有：

```text
默认使用 docs/designs/
```

---

## 23. Design File Naming

Design 文件名称使用：

```text
YYYY-MM-DD-<design-name>.md
```

例如：

```text
2026-08-27-user-search.md
2026-08-27-auth-refactor.md
2026-09-03-project-permissions.md
```

`<design-name>` 应：

- 简短
- 能识别当前任务
- 使用项目常见命名风格
- 避免无意义名称，例如 `new-design.md`

---

## 24. Duplicate File Names

如果同一天已经存在：

```text
2026-08-27-user-search.md
```

不得覆盖。

自动创建：

```text
2026-08-27-user-search-2.md
```

再次冲突：

```text
2026-08-27-user-search-3.md
```

依次增加数字后缀。

---

## 25. Do Not Overwrite Old Designs

每次独立运行 `/design` 都创建新的 design 文件。

不得因为发现同主题旧 design 就自动更新旧文件。

例如：

```text
2026-08-20-user-search.md
2026-08-27-user-search.md
```

可以同时存在。

旧 design 代表过去的设计状态。

新 design 代表当前 `/design` 的结果。

---

## 26. Design Template

`/design` Skill 自带 design 模板。

建议 Skill 结构：

```text
design/
├── SKILL.md
└── assets/
    ├── design.md
    └── design.zh-CN.md
```

Agent 每次执行：

```text
根据 design 文档语言读取 assets/design.zh-CN.md 或 assets/design.md
↓
根据当前任务填写
↓
删除不适用的可选章节
↓
生成最终 design
```

项目自己的模板不覆盖 Skill 内置模板规则。

---

## 27. Required Sections

每个 design 必须包含：

```text
Goal
Requirements
Implementation Approach
File Changes
Testing
```

这五项不得删除。

---

## 28. `Goal`

`Goal` 描述：

```text
当前 design 要实现什么
```

应简洁说明最终目标。

不得：

- 重复完整需求讨论
- 写背景故事
- 填充空泛目标
- 混入实现步骤

---

## 29. `Requirements`

`Requirements` 提炼已经确认、并且会影响实现的要求。

来源可以包括：

```text
用户当前需求
/discuss 已确认内容
项目已有兼容性要求
项目中可以验证的重要约束
```

只保留会影响 design 的 requirement。

不得完整复制 `/discuss` 全过程。

---

## 30. `Implementation Approach`

这是 design 的核心章节。

应描述最终采用的实现方案，包括需要时的：

```text
整体架构
模块职责
数据流
控制流
关键 interaction
关键技术机制
与现有系统的集成方式
关键状态变化
关键边界行为
```

它应该描述：

```text
最终方案是什么
```

而不是：

```text
Agent 思考过什么
```

---

## 31. Final Approach Only

Design 文档只记录最终采用的方案。

不得默认记录：

```text
方案 A
方案 B
方案 C
为什么没选方案 B
完整 brainstorm
完整 trade-off 历史
```

设计过程中的 alternatives 可以用于 Agent 思考或与用户决策。

但最终 design 应保持执行导向。

---

## 32. `File Changes`

`File Changes` 必须列出：

```text
真实文件路径
+
每个文件承担的修改职责
```

例如：

```md
## File Changes

### `src/auth/service.ts`

- 扩展现有认证流程以支持新的访问行为。
- 保持当前公共接口兼容。

### `src/auth/types.ts`

- 增加实现该功能所需的类型定义。
```

不得只列：

```text
src/auth/service.ts
src/auth/types.ts
```

也不要求提前设计到：

```text
新增 resolveRole()
修改 validateSession()
第 42 行增加 if
```

除非具体 symbol 本身就是理解设计所必须的。

---

## 33. File Paths Must Be Real

`File Changes` 中出现的路径必须来自实际项目调查。

不得：

```text
根据常见 Next.js 项目猜 app/api/
根据 React 经验猜 components/
根据 Django 经验猜 views.py
```

如果文件尚不存在，可以明确写：

```text
New file
```

但新增文件必须来自设计需要，而不是模板习惯。

---

## 34. `Testing`

`Testing` 只描述：

```text
实现完成以后需要验证什么
```

例如：

```text
验证登录用户可以完成新操作。
验证未登录用户保持现有拒绝行为。
验证旧数据仍然能够正常读取。
验证现有相关流程没有回归。
```

`Testing` 不需要规定：

```text
具体测试文件
具体测试函数
具体测试框架调用
具体命令
具体 assertion
完整 test case
```

这些属于 `/implement`。

---

## 35. Optional Sections

模板可以提供可选章节，例如：

```text
Current State
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
Background Jobs
Dependencies
Implementation Order
Validation
```

只有当前任务实际需要时才保留。

---

## 36. Remove Unused Sections

对于不适用的可选章节：

不得：

```md
## Migration

N/A
```

也不得：

```md
## Security
```

留下空标题。

应该直接从当前 design 中删除整个章节。

---

## 37. Template Is a Guide, Not a Questionnaire

即使 Skill 使用模板，也不得机械填写所有内容。

模板作用是：

```text
避免遗漏重要设计内容
```

不是：

```text
强迫所有 design 拥有相同结构
```

最终 design 应根据任务复杂度调整。

---

## 38. Simple Designs

对于很小的任务，design 可以很短。

例如：

```text
Goal
Requirements
Implementation Approach
File Changes
Testing
```

每部分只有少量必要内容。

不得因为存在模板就把简单修改扩展成数页文档。

---

## 39. Complex Designs

复杂功能可以根据需要增加：

```text
Data Flow
Interface Changes
Data Model Changes
Compatibility
Migration
Security
Performance
Implementation Order
```

但每个章节都必须有真实内容。

---

## 40. No Unnecessary Detail

设计中的一个细节只有在会明显帮助 `/implement` 时才值得写。

例如通常不需要：

```text
变量名称
private helper 名称
具体 for loop
具体 React hook 排列
具体 SQL formatting
测试函数名字
```

除非这些细节本身构成重要接口或架构约束。

---

## 41. Handle Unknowns

`/design` 不要求消灭所有未知项。

Agent 应区分：

```text
阻塞 design 的未知项
非阻塞的低层未知项
```

阻塞 design 的未知项必须：

```text
调查
验证
或通过用户 Decision 解决
```

低层未知项可以留给 `/implement`。

---

## 42. No Silent Assumptions

以下内容必须区分：

```text
已确认 Requirement
项目中验证的 Fact
prototype 验证的 Fact
Agent 的技术判断
尚未验证的假设
```

重要假设不得静默写成事实。

如果某个假设会影响关键设计，应先验证或解决。

---

## 43. Detect Contradictions

`/design` 必须检查：

```text
需求之间是否冲突
需求与现有系统是否冲突
设计方向之间是否冲突
当前工作区修改是否与设计冲突
```

例如：

```text
Requirement:
完全保持旧 API 行为

Design:
删除旧 endpoint
```

这种 design 不得继续完成。

必须先解决冲突。

---

## 44. Detect Dependencies

Agent 应识别设计中的依赖关系。

例如：

```text
新增权限判断
↓
需要身份信息
↓
依赖 session 层
↓
影响 API handler
↓
影响测试目标
```

设计应按照真实依赖组织方案，而不是把文件当作互不相关的修改列表。

---

## 45. Implementation Order

只有当实现顺序本身重要时，才增加 `Implementation Order`。

例如：

```text
schema 必须先扩展
↓
service 才能使用新字段
↓
API 才能暴露新行为
```

如果文件修改之间没有关键顺序，则删除该章节。

---

## 46. Compatibility

如果需求涉及：

```text
旧 API
旧数据
已有客户端
已有配置
已有 URL
已有数据库
已有用户行为
```

design 必须明确兼容性处理。

如果不存在兼容性问题，则不需要为了模板增加 Compatibility 章节。

---

## 47. Design Validation

Agent 应在保存最终 design 前检查：

```text
文件路径是否真实
关键事实是否有依据
方案是否符合当前项目架构
是否满足 Requirements
是否遗漏关键受影响模块
是否存在明显冲突
是否有无法支持的假设
是否需要 prototype
Testing 是否覆盖主要行为
```

---

## 48. Draft Status

Design 文件创建后，初始状态必须是：

```yaml
status: draft
```

状态属于 design 文件本身。

不得只依赖聊天上下文记住是否确认。

---

## 49. Final Path from the Beginning

Draft design 直接写入最终文件路径。

例如：

```text
docs/designs/2026-08-27-user-search.md
```

不得先使用：

```text
user-search.draft.md
user-search-temp.md
user-search-final.md
```

---

## 50. Update the Same Draft During Confirmation

在当前 `/design` 会话中，如果用户提出修改：

```text
更新当前 design 文件
```

不得因为一次反馈创建：

```text
-2
-3
-final
-final-final
```

数字后缀只用于：

> 新的一次独立 `/design` 与已有文件重名。

不是当前 draft 的修订版本号。

---

## 51. Final Confirmation

`/design` 不得在 Agent 自己认为设计完成时直接结束。

必须执行：

```text
设计完成
↓
保存 draft design
↓
清理 prototype
↓
向用户概括关键设计
↓
请求最终确认
↓
等待用户
```

---

## 52. User Feedback

用户可以：

```text
确认
要求修改
否定某项设计
提出新的约束
指出遗漏
修改已确认 Decision
```

如果用户提出修改：

```text
判断修改属于 design 还是 discuss
```

如果属于 implementation design：

```text
更新 design
↓
重新检查
↓
再次请求确认
```

如果实际上改变需求：

```text
停止 /design
↓
要求返回 /discuss
```

---

## 53. Confirmed Status

只有用户明确确认以后：

```yaml
status: confirmed
```

Agent 更新当前 design 文件。

此时 `/design` 才正式完成。

---

## 54. Completion Condition

不得因为以下原因认为 `/design` 已完成：

```text
模板填完了
文件已经创建
已经写了很多内容
Agent 想不到更多问题
prototype 成功了
```

正确完成条件是：

```text
需求足够明确
+
真实项目已经调查
+
关键技术决策已经解决
+
重大 trade-off 已经确认
+
必要验证已经完成
+
prototype 已全部清理
+
design 文件真实有效
+
用户已经最终确认
+
status = confirmed
```

---

## 55. Final Output

`/design` 完成时，Agent 应简洁说明：

```text
design 文件位置
关键实现方向
重要文件影响
必要的技术注意事项
确认状态
```

不需要重新复制完整 design 内容。

---

## 56. Relationship with `/improve`

`/design` 的目标是：

```text
形成 Agent 当前认为合理、完整、可执行的设计
```

不应该故意留下明显问题等待 `/improve`。

`/improve` 的存在不是降低 `/design` 质量要求的理由。

流程：

```text
/design
↓
尽最大合理努力形成高质量 design
↓
用户确认
↓
/improve
↓
独立寻找可以进一步改进的地方
```

---

## 57. Relationship with `/implement`

`/implement` 应能够根据 confirmed design：

```text
理解目标
理解需求
理解最终方案
知道修改范围
知道各文件职责
知道关键行为
知道需要验证什么
```

但 `/implement` 仍然拥有低层代码实现自由。

---

## 58. Relationship with `/review`

`/design` 不负责审查最终代码。

即使 design 中进行了 prototype，也不能认为：

```text
prototype 可行
=
最终 implementation 正确
```

正式代码质量、实现偏差和回归问题属于 `/review`。

---

## 59. Prohibited Behaviors

### 禁止凭经验猜项目

必须先调查真实实现。

---

### 禁止重新承担 `/discuss`

需求层问题必须返回 `/discuss`。

---

### 禁止擅自改变已确认需求

技术设计必须服从已确认 requirement。

---

### 禁止无依据推翻高层方向

只有新事实能够挑战已确认 Decision。

---

### 禁止把普通工程细节全部问用户

普通技术 Decision 属于 Agent 的职责。

---

### 禁止擅自决定重大长期架构 trade-off

重大 Decision 必须由用户确认。

---

### 禁止为了完整而过度设计

简单任务保持简单。

---

### 禁止提前实现

prototype 只能用于验证设计。

---

### 禁止保留 prototype

所有验证性代码必须清理。

---

### 禁止影响用户当前工作区

不得 stash、reset、clean 或覆盖用户修改。

---

### 禁止忽略相关未提交修改

当前真实工作区属于 design 的调查对象。

---

### 禁止把无效 prototype 当作验证

如果当前未提交修改会影响 design，prototype 必须在隔离环境中复制相关修改。

---

### 禁止覆盖旧 design

每次独立 `/design` 创建新文件。

---

### 禁止制造无意义版本文件

当前 draft 修改始终更新同一文件。

---

### 禁止生成空章节

不适用的可选章节直接删除。

---

### 禁止使用 `N/A` 填满模板

模板不是表格问卷。

---

### 禁止记录无关 brainstorming

最终 design 只记录最终方案。

---

### 禁止把低层实现细节写成硬约束

除非它们确实属于关键设计。

---

### 禁止未经用户确认结束

最终 confirmation 是 `/design` 的必要步骤。

---

## 60. Recommended Execution Flow

完整流程：

```text
用户运行 /design
↓
读取用户需求和已有上下文
↓
判断需求是否足够明确
├── 否
│   └── 指出需求层未决问题
│       ↓
│       要求回到 /discuss
│
└── 是
    ↓
调查当前项目
↓
读取当前分支 HEAD
↓
检查当前工作区未提交修改
↓
理解相关现有实现
↓
识别 Fact / Technical Decision / Requirement Decision
↓
自行调查 Fact
↓
如果出现 Requirement Decision
    └── 返回 /discuss
↓
解决普通 Technical Decision
↓
如果出现重大 Technical Decision
    └── 向用户提供选项、推荐和 trade-off
        ↓
        等待确认
↓
检查已确认高层方向是否仍然成立
↓
如果新事实挑战原方向
    └── 向用户说明
        ↓
        等待确认
↓
识别重要技术未知项
↓
能通过静态调查确认
    └── 继续调查
↓
需要实验验证
    └── 从当前 HEAD 创建隔离环境
        ↓
        如果相关未提交修改影响设计
            └── 复制相关修改
        ↓
        编写 prototype
        ↓
        运行验证
        ↓
        获取事实
↓
形成最终实现方案
↓
读取 Skill 内置 design template
↓
填写所有必填章节
↓
填写需要的可选章节
↓
删除不适用章节
↓
确定 design 保存目录
├── 项目已有约定
│   └── 使用现有目录
└── 没有
    └── docs/designs/
↓
生成 YYYY-MM-DD-<design-name>.md
↓
如果重名
    └── 添加 -2 / -3 / ...
↓
写入 status: draft
↓
清理所有 prototype 和隔离环境
↓
验证用户工作区未被改变
↓
向用户概括设计
↓
请求最终确认
├── 用户要求修改
│   └── 更新同一个 design 文件
│       ↓
│       必要时重新调查或验证
│       ↓
│       再次请求确认
│
└── 用户确认
    ↓
更新：
status: confirmed
↓
/design 完成
```

---

## 61. Mental Model

`/design` 不应该像：

```text
根据需求猜一个 implementation plan
```

也不应该像：

```text
提前把功能实现一遍
```

更接近：

```text
Understand the real system
↓
Resolve implementation-level uncertainty
↓
Validate important assumptions
↓
Make key engineering decisions
↓
Produce an implementation-ready design
↓
Get user confirmation
```

最终目标是：

> 在正式修改代码之前，把需求转换成一份建立在真实项目之上、经过必要验证、关键技术决策明确、能够可靠指导 `/implement` 的设计。
