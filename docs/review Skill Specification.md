# `/review` Skill Specification

## 1. Purpose

`/review` 用于在 implementation 完成以后，对一个明确的 code change 进行独立、只读、defect-first 的正式审查。

它的核心目标不是：

```text
给代码提尽可能多的建议
```

而是：

> 根据 Requirement、confirmed design、真实 implementation、repository rules 和必要验证，发现当前 change 实际引入或明显恶化的、具有实际影响并且有证据支持的问题。

`/review` 主要回答：

```text
当前 implementation 是否满足 Requirement？
如果存在 confirmed design，implementation 是否遵守 design？
当前 change 是否引入 correctness defect？
是否产生 regression？
是否存在真实 security 问题？
是否存在真实 performance 问题？
是否破坏重要 responsibility、contract 或 maintainability？
相关测试是否真正覆盖当前行为？
现有 verification 是否足够？
是否存在会影响判断的重要 verification gap？
```

`/review` 不负责：

```text
重新讨论 Requirement
重新设计 implementation
寻找更漂亮的 architecture
正式修改代码
自动修复 finding
commit
push
创建 PR
merge
repository-wide audit
UI / visual design review
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

`/implement` 完成后不得自动进入 `/review`。

用户必须手动调用：

```text
/review
```

才进入正式 implementation review。

`/review` 完成以后也不得自动进入：

```text
/implement
```

即使发现 finding，也只能报告并结束。

修复必须作为新的 implementation task，由用户重新运行：

```text
/implement
```

完成修复后，如果用户需要重新审查，则再次手动调用：

```text
/review
```

---

## 3. Boundary with `/discuss`

`/discuss` 负责决定：

```text
Goal
Scope
Expected behavior
User-visible behavior
Requirement
Important constraints
Compatibility requirements
High-level direction
```

`/review` 不负责重新决定这些内容。

如果 `/review` 发现 implementation 与 Requirement 冲突：

```text
Requirement 已明确
+
implementation 不符合 Requirement
```

这通常属于：

```text
finding
```

而不是新的 `/discuss`。

例如：

```text
Requirement:
删除操作必须可以恢复

Implementation:
直接永久删除数据库记录
```

如果证据明确：

```text
这是 Requirement violation
→ 报告 finding
```

但如果 Requirement 本身存在真实 ambiguity：

```text
两种合理理解都会改变 finding 是否成立
+
无法通过已有 specification、design、issue 或 repository context 解决
```

则不得猜测。

应：

```text
记录 Requirement verification gap
+
必要时指出无法可靠判断对应 candidate finding
```

如果用户需要解决需求本身，应返回：

```text
/discuss
```

`/review` 不应该自己改变 Requirement。

---

## 4. Boundary with `/design`

`/design` 负责：

```text
How exactly should we implement it?
```

包括：

```text
Implementation Approach
模块职责
文件职责
关键数据流
关键控制流
Interface Changes
Data Model Changes
Compatibility
Error Handling
Dependencies
Testing goals
重大 Technical Decisions
```

如果当前任务存在以下任一状态的 design：

```yaml
status: confirmed
# 或
status: completed
```

则该 design 是重要 review basis。`completed` 还表示用户已经确认对应实现完成。

`/review` 应检查：

```text
actual implementation
vs
confirmed design
```

包括：

```text
Implementation Approach 是否一致
模块职责是否一致
关键数据流是否一致
关键控制流是否一致
interface 是否符合 design
data model 是否符合 design
compatibility behavior 是否符合 design
error-handling strategy 是否符合 design
dependency 是否符合 design
testing goal 是否得到实现
```

如果 implementation 出现未经确认的重大 design deviation，并且该 deviation 会产生实际风险或违反 implementation contract，则可以形成 finding。

但 `/review` 不负责：

```text
设计新的替代 architecture
重新完成 /design
把自己更喜欢的方案当成 defect
```

---

## 5. Boundary with `/improve`

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

`/improve` 可以寻找：

```text
更简单的方案
更可靠的 architecture
遗漏的 design 内容
更合理的 abstraction
潜在 implementation 风险
```

`/review` 不应该重新执行这些工作。

`/review` 不问：

```text
有没有更优雅的方案？
是否应该重构整个 subsystem？
未来是否可以采用另一种 architecture？
有没有更好的 abstraction？
```

除非当前 implementation 已经因此形成一个：

```text
具体
真实
由当前 change 引入
具有实际影响
可执行
有证据支持
```

的 defect。

---

## 6. Boundary with `/implement`

`/implement` 负责：

```text
写出 Agent 当前认为正确且高质量的 production implementation
+
完成合理 verification
```

`/review` 负责：

```text
独立重新审查 actual implementation
```

因此：

```text
/implement 自己检查 implementation
≠
/review
```

`/review` 不能因为：

```text
/implement 已经运行了测试
/implement 已经检查了 diff
/implement 认为代码正确
```

就降低审查标准。

同样：

```text
/review 存在
```

也不是 `/implement`：

```text
少写测试
省略 verification
留下已知问题
降低代码质量
```

的理由。

---

## 7. Core Principle: Defect First

`/review` 必须采用：

```text
defect-first review
```

核心问题是：

```text
当前 change 实际引入了什么值得修复的问题？
```

不是：

```text
我还能想到哪些建议？
```

candidate finding 必须经过验证。

不得为了让 review 看起来有价值而制造 finding。

原则：

> No finding is better than an unsupported finding.

---

## 8. Review a Specific Change

`/review` 审查的是：

```text
specific code change
```

而不是默认进行：

```text
repository-wide code audit
```

合法 review target 可以包括：

```text
Pull Request
commit
commit range
branch
tag
patch
working tree
```

文件路径可以作为：

```text
review target 内的 filter
```

但单独指定一个文件时，也必须理解该文件属于哪个 change。

---

## 9. Explicit Review Target

如果用户明确指定：

```text
PR
commit
range
branch
tag
patch
working tree
```

则优先使用用户指定 target。

例如：

```text
/review PR #123
/review commit abc123
/review main..feature-x
/review current working tree
```

不得无理由改成其他 comparison target。

---

## 10. Default Review Target Resolution

如果用户只运行：

```text
/review
```

没有明确 target，则按照以下顺序解析。

### 10.1 Working tree 有修改

如果存在：

```text
staged changes
unstaged changes
相关 untracked files
```

则默认：

```text
review current working tree
```

review target 包括：

```text
staged
+
unstaged
+
与当前 change 相关的 untracked files
```

不得忽略 untracked implementation file。

---

### 10.2 Working tree clean

如果 working tree 没有 change：

```text
确定当前 branch 的真实 comparison base
↓
计算 merge-base
↓
review 当前 branch 相对 base 的完整 change
```

目标是审查：

```text
如果当前 branch 合并到真实 base
最终会引入什么 change
```

而不是机械比较：

```text
HEAD~1
```

---

## 11. Resolve the Actual Base

确定 branch comparison base 时，应优先调查：

```text
configured upstream
当前 branch tracking information
repository workflow
merge-base
PR base，如果存在
```

不得仅因为仓库存在：

```text
main
master
develop
```

就默认其中某一个是 base。

原则：

```text
actual integration base
>
generic default branch assumption
```

---

## 12. Invalid or Empty Target

开始正式 review 前必须确认：

```text
review target 可以解析
+
comparison base 可以可靠确定，如果需要
+
target 非空
```

如果 ref 无效：

```text
停止
↓
说明 invalid target
```

如果 target 为空：

```text
停止
↓
说明没有 code change 可以 review
```

不得：

```text
空 diff
→ 开始 review 整个 repository
```

---

## 13. Ambiguous Review Target

如果存在多个合理 target，并且无法可靠确定用户指的是哪一个：

```text
停止
↓
列出最少必要的候选 target
↓
要求用户确认
```

不得：

```text
根据时间最新选择
根据 branch 名看起来最像选择
根据 Agent best guess 静默选择
```

---

## 14. Establish Review Basis

确定 review target 后，Agent 应建立 review basis。

优先包括：

```text
Requirement
confirmed design，如果存在
repository rules
existing behavior
actual change
tests
relevant documentation
```

review 不是：

```text
只看 diff 的 style critique
```

而是：

```text
intended behavior
vs
actual implementation
```

---

## 15. Requirement Discovery

Agent 应尽可能从已有上下文找到 intended behavior。

可以调查：

```text
当前用户请求
/discuss 结果
issue
PR description
commit message
linked specification
repository documentation
tests
existing behavior
```

优先级：

```text
Explicit Requirement
↓
confirmed specification / design
↓
repository rules
↓
existing established behavior
↓
generic engineering expectations
```

不得用 generic preference 覆盖明确 Requirement。

---

## 16. Requirement Conformance

如果存在可靠 Requirement：

```text
/review 必须验证 Requirement conformance
```

例如检查：

```text
要求的行为是否真正实现
是否遗漏主要 scope
是否出现错误 user-visible behavior
是否破坏 compatibility requirement
是否实现了错误权限规则
```

Requirement violation 可以形成 finding，只要符合 finding criteria。

---

## 17. Missing Requirement

如果无法找到足够可靠的 Requirement 或 specification：

```text
仍然继续 defect review
```

不得因为：

```text
没有 design
没有 issue
没有 PR description
```

就拒绝 review。

但最终必须记录：

```text
Requirement conformance was not verified.
```

并把它作为：

```text
Verification Gap
```

不得假装已经验证 Requirement。

---

## 18. Confirmed Design Discovery

如果当前上下文明显存在 related design，Agent 应调查：

```text
当前任务
当前对话
design 目录
当前工作区
相关 specification
```

目标是确认是否存在：

```yaml
status: confirmed
# 或
status: completed
```

的当前任务 design。

不得仅根据：

```text
文件最新
名字最相似
```

静默选择。

---

## 19. Design Compliance

如果存在 `status: confirmed` 或 `status: completed` design：

```text
/review 必须验证 design compliance
```

重点检查 design 中已经确认的重要内容。

例如：

```text
architecture direction
module ownership
file responsibility
data flow
control flow
interface
type / schema
compatibility
error handling
dependency
testing goal
```

但 design compliance review 不应该机械比较：

```text
每一句 design
vs
每一行 code
```

只需要检查：

```text
会明显影响 implementation contract 的内容
```

---

## 20. Draft Design

如果相关 design 为：

```yaml
status: draft
```

则：

```text
draft design
≠
authoritative implementation contract
```

`/review` 可以把 draft 当作辅助上下文。

但不得把 draft 中未确认内容作为：

```text
finding 的唯一依据
```

如果当前 implementation 是否正确取决于 draft 中尚未确认的 Decision：

```text
记录 verification gap
```

而不是猜测。

---

## 21. Repository Rules

正式审查前必须调查 applicable repository rules。

例如：

```text
AGENTS.md
CONTRIBUTING.md
README
repository-specific instructions
lint rules
formatter rules
testing conventions
framework conventions
module-specific rules
```

changed path 可能受到不同的局部规则约束。

明确 repository rule：

```text
>
Agent personal preference
```

---

## 22. Read-Only Review

`/review` 必须严格：

```text
read-only
```

不得修改 production workspace。

这是 `/review` 与 `/implement` 的核心边界之一。

---

## 23. Allowed Review Actions

`/review` 可以：

```text
读取文件
读取 diff
搜索代码
调查 Git history
查看 branch / commit / tag
查看 repository rules
查看 tests
查看 schema
查看 config
查看 types
查看 migrations
查看 public contracts
运行已有 test
运行 typecheck
运行 lint / static check
运行 build
运行非破坏性的 focused reproduction
读取 tool output
创建不修改 repository 的临时分析数据，如果环境需要
```

所有操作必须服务于：

```text
理解 change
或
验证 candidate finding
```

---

## 24. Forbidden Mutations

`/review` 不得：

```text
修改 source file
修改 test file
修改 config
自动修复 lint
自动格式化代码
安装 dependency
升级 dependency
生成正式 migration
修改 lockfile
commit
push
merge
rebase
创建 PR
post review comment
resolve review thread
stash
reset
clean
强制 checkout
覆盖用户工作
删除 untracked file
```

---

## 25. Review and Fix Must Stay Separate

如果用户要求：

```text
review and fix
```

则仍应先完整完成 `/review`。

`/review` 本身不进入修复阶段。

正确关系：

```text
/review
↓
输出 findings
↓
结束

新的 /implement
↓
修复
```

不得：

```text
找到第一个问题
↓
立刻修改代码
↓
继续 review 修改后的版本
```

---

## 26. Do Not Install Dependencies

不得为了 review：

```text
npm install
pnpm install
yarn install
pip install
cargo add
brew install
```

或其他会修改环境、lockfile 或项目状态的 dependency operation。

如果 verification 因 dependency 不可用而无法执行：

```text
记录 Verification Gap
+
说明 residual risk
```

---

## 27. Protect User Work

`/review` 必须保护用户当前工作状态。

不得：

```text
stash 用户修改
reset 用户修改
clean 用户文件
覆盖用户修改
切换用户当前 worktree 的 branch
强制 checkout
删除 untracked file
恢复用户未要求恢复的内容
```

如果为了查看其他 ref 必须切换 branch：

```text
优先使用不会改变用户工作区的方法
```

例如：

```text
git show
git diff
git cat-file
独立只读工作树，如果环境已经安全提供
```

---

## 28. Read the Complete Change

不得只抽查：

```text
几个 changed files
最大的文件
最复杂的函数
用户提到的某一段
```

必须先理解：

```text
complete review target
```

才能形成最终结论。

原则：

> Read the complete change before concluding the review.

---

## 29. Continue After Finding a Defect

找到第一个 finding 后不得停止。

流程必须继续：

```text
发现 finding
↓
记录 candidate
↓
继续检查剩余 review target
↓
完成完整 change coverage
```

原因：

```text
一个 defect
≠
完整 review
```

---

## 30. Changed File Context

对每个 changed path，不应只看 diff hunk。

必须读取足够 surrounding code，以理解：

```text
当前函数真实职责
现有 abstraction
状态来源
错误路径
调用关系
接口 contract
测试方式
```

调查深度取决于：

```text
判断当前 change 所需的真实上下文
```

---

## 31. Follow Affected Call Paths

必要时必须继续调查：

```text
callers
downstream consumers
```

例如：

```text
函数 return type 改变
↓
检查 caller 是否仍按旧 contract 使用
```

或者：

```text
API response 改变
↓
检查 consumer 是否兼容
```

不要因为 caller 没有出现在 diff 中就忽略。

---

## 32. Tests and Test Helpers

应检查：

```text
相关已有 tests
新增 tests
修改 tests
test helpers
fixtures
mocks
integration setup
```

重点判断：

```text
测试是否真正验证当前 behavior
测试是否只验证 implementation detail
测试是否遗漏重要 regression
测试是否被错误修改来适配错误行为
```

---

## 33. Types, Schemas, and Contracts

相关时应检查：

```text
Type definitions
Database schema
API schema
Serialization format
Config schema
Public interface
Migration
Protocol contract
```

很多 regression 可能发生在：

```text
changed implementation
+
unchanged consumer
```

之间。

---

## 34. Error Paths

相关时必须调查：

```text
error handling
error propagation
fallback
retry
cleanup after error
partial failure
transaction rollback
```

不得只审查 happy path。

---

## 35. Cleanup Paths

涉及资源时应检查：

```text
file handle
socket
database connection
subscription
timer
listener
temporary state
lock
transaction
```

是否正确 cleanup。

---

## 36. Concurrency Paths

如果 change 涉及：

```text
async state
parallel work
thread
queue
lock
cache
transaction
distributed state
```

则必须合理检查：

```text
race condition
lost update
duplicate operation
deadlock
ordering
atomicity
stale state
```

不得在不涉及 concurrency 的 change 中机械寻找 concurrency issue。

---

## 37. Trust Boundaries

如果 change 涉及：

```text
user input
authentication
authorization
external request
file path
database query
HTML rendering
deserialization
secret
permission
```

则应检查相关 trust boundary。

---

## 38. Review Dimensions

以下维度用于寻找 candidate findings：

```text
Correctness
Regression
Requirement compliance
Design compliance
Security
Performance
Maintainability
Testing
```

这些是：

```text
search prompts
```

不是：

```text
output quotas
```

不要求每个维度都必须输出 finding。

---

## 39. Correctness

应寻找真实 correctness defect，例如：

```text
错误条件判断
错误 return value
missing case
null / undefined handling
empty input
overflow
off-by-one
state inconsistency
race condition
错误 error propagation
错误 fallback
type-safety defect
transaction bug
incorrect cleanup
```

只报告能够被实际 change 支持的问题。

---

## 40. Regression

`/review` 应主动考虑：

```text
当前 change 是否破坏已有行为？
```

例如：

```text
旧 API consumer
旧数据
已有 configuration
existing permission
existing workflow
backward compatibility
existing test contract
```

但不得把所有可能的历史行为都假设为必须兼容。

必须有：

```text
Requirement
design
existing established behavior
或 repository evidence
```

支持兼容判断。

---

## 41. Security

仅在相关时寻找：

```text
authentication flaw
authorization flaw
SQL injection
XSS
CSRF
SSRF
path traversal
secret exposure
insecure deserialization
unsafe file access
trust-boundary bypass
permission bypass
```

安全 finding 仍必须符合普通 finding criteria。

不得因为：

```text
security 很重要
```

就降低证据标准。

---

## 42. Performance

仅在 change 真实影响 performance-sensitive path 时考虑：

```text
N+1 query
unbounded query
unbounded loop
resource leak
明显 algorithmic regression
大量不必要 allocation
missing index for newly introduced query
重复 expensive work
blocking operation in critical path
```

不得把：

```text
理论上可以更快
```

当成 finding。

必须证明存在：

```text
meaningful performance impact
```

---

## 43. Maintainability

maintainability finding 必须是：

```text
具体
由当前 change 引入或明显恶化
会增加真实错误或维护风险
作者知道后大概率会修
```

例如：

```text
违反明确 responsibility boundary
复制会发生 divergence 的关键逻辑
非显然行为缺少必要说明
changed behavior 缺少关键 test
命名导致真实行为被误解
```

不得报告：

```text
我更喜欢另一种命名
文件有点长
可以再抽象一层
可以使用 design pattern
```

这类纯 preference。

---

## 44. Testing Findings

缺少测试不是自动 finding。

只有当：

```text
当前 change 改变重要 behavior
+
缺少测试会造成真实 regression 风险
+
repository testing pattern 表明该 behavior 应被验证
```

时，才可能形成：

```text
missing test finding
```

不得机械要求：

```text
每个新函数一个 test
每个 branch 一个 test
coverage 必须达到任意数字
```

除非 repository 明确要求。

---

## 45. Finding Criteria

一个 candidate finding 只有同时满足以下条件，才允许正式报告。

### 45.1 Change causality

问题必须：

```text
由当前 reviewed change 引入
```

或：

```text
被当前 change materially worsened
```

---

### 45.2 Meaningful impact

问题必须对至少一个方面产生实际影响：

```text
correctness
security
performance
maintainability
Requirement compliance
design compliance
regression
```

---

### 45.3 Evidence

必须存在：

```text
代码证据
或
focused verification
```

能够证明受影响：

```text
scenario
call path
behavior
```

---

### 45.4 Discrete

finding 必须是：

```text
具体问题
```

而不是：

```text
整个 architecture 不够好
代码质量一般
这里可能有风险
测试应该更多
```

---

### 45.5 Actionable

作者应能够理解：

```text
哪里错了
什么时候会出错
为什么是当前 change 导致
```

并能够采取明确修复行动。

---

### 45.6 Worth fixing

合理开发者知道以后：

```text
大概率愿意修复
```

否则不应进入 findings。

---

## 46. Excluded Findings

不得正式报告：

```text
纯 speculative concern
没有证据的潜在风险
pre-existing problem
没有被当前 change 恶化的历史 Bug
intentional behavior change
generic best practice
cosmetic preference
formatting preference
style preference
ambitious architecture redesign
repository-wide technical debt
未来可能出现的问题
与当前 change 无关的问题
```

---

## 47. Pre-existing Problems

如果调查中发现 pre-existing issue：

```text
默认不报告为 finding
```

因为 `/review` 的对象是：

```text
当前 change
```

只有当 pre-existing condition 用于解释：

```text
为什么当前 change 会失败
```

时，可以在 finding 的证据中提到。

例如：

```text
旧代码已经依赖 invariant X
+
当前 change 破坏 X
→ finding 属于当前 change
```

---

## 48. Intentional Behavior Changes

如果 behavior change：

```text
由 Requirement 明确要求
+
符合 confirmed design
```

不得因为它改变旧行为就报告为 regression。

`changed behavior` 本身：

```text
≠
defect
```

---

## 49. Tooling-Detected Issues

如果问题已经能够被项目现有 mandatory tooling：

```text
稳定
明确
自动
```

检测，并且 review 只是在重复工具输出：

```text
通常不需要作为独立 finding
```

例如单纯：

```text
formatter issue
lint 自动明确报错
```

但如果 tooling failure 暴露的是一个：

```text
真实 behavioral defect
```

则可以报告真实问题，而不是只报告：

```text
lint failed
```

---

## 50. Evidence Before Finding

每个 finding 必须先回答：

```text
什么 scenario 触发？
实际错误 behavior 是什么？
为什么是当前 change 导致？
代码证据在哪里？
是否需要运行验证？
```

无法回答时：

```text
candidate finding
→ 丢弃
```

---

## 51. Static Evidence First

优先通过：

```text
代码
类型
调用链
已有 test
schema
config
contract
```

建立证据。

如果静态证据已经明确：

```text
不需要为了形式额外运行测试
```

例如明显：

```text
函数在 null 输入必然 dereference
```

且 call path 已确认允许 null，则代码本身已经能够形成有效证据。

---

## 52. Focused Verification

如果静态证据不足：

```text
运行最小相关非破坏性 verification
```

例如：

```text
focused unit test
specific integration test
targeted type check
targeted lint
small reproduction
specific build target
```

原则：

> Use the smallest verification that can reliably confirm or reject the candidate finding.

---

## 53. Do Not Write Fake Tests

`/review` 是 read-only。

因此不得为了证明 finding：

```text
修改正式 test file
新增 repository test
改 fixture
改 production code
```

如果可以通过：

```text
已有 test command
临时非侵入 reproduction
现有 runtime invocation
```

验证，则可以使用。

---

## 54. Repository-Standard Verification

除了 focused finding validation，`/review` 还应根据：

```text
change 类型
change 风险
repository convention
已有 CI / validation pattern
```

运行与当前 change 相称的标准验证。

可能包括：

```text
relevant test suite
typecheck
lint
build
integration test
```

---

## 55. Do Not Run Everything Mechanically

不得机械认为：

```text
review
=
full test
+
full lint
+
full build
+
所有 integration test
```

验证范围应与：

```text
change scope
风险
项目规模
已有 convention
```

相称。

例如：

```text
小型局部 utility 修改
→ targeted tests + relevant typecheck
```

不一定需要：

```text
整个 monorepo 全量 build
```

---

## 56. Expand Verification When Needed

可以逐步扩大 verification。

例如：

```text
focused test
↓
发现可能影响同模块其他行为
↓
module test suite
↓
仍存在 broader regression risk
↓
更广相关 test
```

扩大必须有理由。

不得：

```text
为了显得彻底无限扩大验证范围
```

---

## 57. Verification Failure

如果 verification 失败：

```text
先判断失败是否由当前 change 引入
```

可能情况：

```text
当前 change 导致
→ candidate finding

pre-existing failure
→ 不作为当前 finding

environment failure
→ Verification Gap

irrelevant unrelated failure
→ 不作为当前 finding
```

不得：

```text
看到 red test
→ 自动报告当前 change 有 Bug
```

---

## 58. Verification Gaps

如果重要 verification 无法完成，例如：

```text
dependency 不可用
service 不可访问
database 不可用
required fixture 缺失
build environment 不存在
外部 API 不可访问
相关 Requirement 不可获得
```

则：

```text
不得伪造验证结果
```

必须记录：

```text
Verification Gap
+
Residual Risk
```

---

## 59. Residual Risk

Verification Gap 不能只写：

```text
没有运行 X
```

还应说明：

```text
因此什么行为仍然没有得到验证？
```

例如：

```text
未运行 database integration test。

Residual Risk:
新的 transaction rollback behavior 没有经过真实 database 验证。
```

保持简短且具体。

---

## 60. Risk-Based Agent Count

`/review` 不固定每次使用相同数量的 Agent。

应根据 change 风险动态决定。

### 普通 change

例如：

```text
范围小
行为明确
风险低
局部修改
熟悉 pattern
```

默认：

```text
1 个 Agent
```

---

### 高风险 change

例如：

```text
核心业务路径
authentication / authorization
security-sensitive code
data migration
persistence
concurrency
复杂 state
public API
大范围 refactor
跨模块 change
高 regression risk
implementation 与 design 映射复杂
Agent 自己对 change 不确定
```

默认：

```text
3 个 Agent
```

---

## 61. Maximum Agent Count

如果用户明确指定 multi-agent 数量：

```text
1 到 5
→ 使用用户指定数量

超过 5
→ 最多使用 5 个
```

如果环境实际可用 Agent 少于目标数量：

```text
使用实际可用数量
```

如果环境完全不支持 subagent：

```text
主 Agent 单独完成完整 /review
```

不得因为：

```text
没有 subagent
```

拒绝 review。

---

## 62. Independent Multi-Agent Review

多个 Agent 必须独立审查完整 change。

结构：

```text
Review Target
        ↓
 ┌──────┼──────┐
 ↓      ↓      ↓
Agent 1 Agent 2 Agent 3
 ↓      ↓      ↓
独立读取完整 change
独立调查
独立分析
独立验证
独立提出 candidate findings
 └──────┼──────┘
        ↓
     Main Agent
```

---

## 63. No Fixed Agent Roles

不得预先固定：

```text
Agent 1 = correctness
Agent 2 = security
Agent 3 = performance
Agent 4 = maintainability
```

所有 Agent 都审查完整 change。

每个 Agent 都可以寻找：

```text
Requirement violation
design deviation
correctness defect
regression
security issue
performance issue
maintainability regression
testing gap
```

---

## 64. Agent Isolation

subagent 之间不得：

```text
读取彼此输出
互相讨论
基于另一个 Agent 的 finding 继续推理
提前形成共识
```

主 Agent 应成为：

```text
第一个统一读取所有 Agent 输出的角色
```

这样可以保留独立性。

---

## 65. Same Review Standard for All Agents

每个 Agent 必须使用相同的 finding criteria。

不得允许某个 Agent：

```text
宽松报告 suggestion
```

另一个 Agent：

```text
严格 defect-only
```

所有 candidate finding 都必须满足同一标准。

---

## 66. Main Agent Aggregation

所有 Agent 完成后，主 Agent 负责：

```text
读取全部 candidate findings
↓
识别重复问题
↓
合并相同 finding
↓
检查 evidence
↓
确认 change causality
↓
确认实际 impact
↓
必要时自己重新调查代码
↓
必要时运行 focused verification
↓
丢弃不满足 finding criteria 的 candidate
↓
确定 severity
↓
生成最终 findings
```

不得把 subagent 输出直接拼接后返回用户。

---

## 67. Repeated Findings

如果多个 Agent 独立发现同一问题：

```text
这是值得重点验证的信号
```

但：

```text
Agent 数量
≠
finding 正确性
```

即使 5 个 Agent 都报告同一个问题，主 Agent 仍必须确认：

```text
是否真实
是否由当前 change 引入
是否有实际影响
是否有可靠 evidence
```

不得用多数投票替代验证。

---

## 68. Conflicting Agent Findings

如果 Agent 对 candidate finding 存在冲突：

```text
Agent 1:
这是 P1 Bug

Agent 2:
这是 intended behavior
```

主 Agent 应：

```text
重新检查 Requirement
重新检查 design
重新检查代码
必要时运行 verification
```

然后自行判断：

```text
finding 是否成立
```

`/review` 不是 Technical Decision 投票流程。

---

## 69. One Review Pass per Invocation

每次：

```text
/review
```

只执行：

```text
一轮正式 review
```

即使使用多个 Agent：

```text
多个并行 Agent
=
同一轮 review
```

不是多轮。

---

## 70. No Automatic Review Loop

不得：

```text
第一轮 review
↓
自动进入第二轮
↓
自动进入第三轮
```

如果发现 findings：

```text
报告
↓
结束 /review
```

修复后用户可以重新调用：

```text
/review
```

新的 `/review` 才属于新一轮。

---

## 71. Review the Current Code

如果 review target 是 PR、branch 或 working tree，且存在已有 review comment：

```text
旧 comment
≠
当前 finding 的证据
```

Agent 必须根据：

```text
current code
current diff
current thread state
```

重新验证 claim。

过时 comment 只能作为：

```text
context
```

不得直接复制。

---

## 72. Severity Levels

正式 finding 使用：

```text
P0
P1
P2
P3
```

---

### P0: Critical

适用于具有可信风险的：

```text
可利用严重漏洞
不可恢复数据丢失
普遍性系统故障
灾难性安全问题
```

默认行动：

```text
Block the merge
```

P0 应非常少见。

不得为了强调问题严重程度滥用 P0。

---

### P1: High

适用于：

```text
common path
critical path
```

上的严重 defect，并造成显著：

```text
用户影响
数据影响
security impact
performance impact
```

默认行动：

```text
Fix before the merge
```

---

### P2: Medium

适用于：

```text
局部 defect
有限范围 regression
有实际影响的 maintainability regression
非核心路径上的确定问题
```

默认行动：

```text
Fix in this pull request
or
create a clear follow-up task
```

---

### P3: Low

适用于：

```text
低影响
但具体
真实
值得修正
```

的问题。

默认行动：

```text
Optional improvement
```

P3 仍然必须满足完整 finding criteria。

它不是：

```text
suggestion bucket
```

---

## 73. Severity Based on Impact

Severity 必须基于：

```text
触发概率
影响范围
影响严重程度
是否处于关键路径
数据风险
安全风险
恢复难度
```

而不是：

```text
代码看起来有多糟
Agent 有多不喜欢实现
修复代码需要多少行
```

---

## 74. Finding Format

每个 finding 使用：

```text
[P1] Imperative finding title: path/to/file.ext:line
```

标题应：

```text
简短
具体
直接表达需要修复的问题
```

避免：

```text
Potential issue
Consider improving this
Code quality problem
Possible bug
```

---

## 75. Finding Body

每个 finding 后只写一个简短段落。

必须说明：

```text
affected scenario
incorrect behavior
为什么当前 change 会导致
```

如果修复方向不明显，可以补充：

```text
简短 remedy direction
```

不得把 finding 写成长篇 design proposal。

---

## 76. Finding Location

finding 应定位到：

```text
最小且有用的 line range
```

优先引用：

```text
与当前 diff 重叠的最小范围
```

不得引用：

```text
整个文件
整个函数
几十行不相关代码
```

如果实际 defect 在 unchanged consumer 中，但由 changed contract 导致，应优先定位：

```text
引入错误 contract 的 changed code
```

并在正文解释 consumer。

---

## 77. Findings Order

Findings 必须按：

```text
P0
↓
P1
↓
P2
↓
P3
```

排序。

相同 severity 内可按：

```text
impact
或
代码顺序
```

组织。

---

## 78. No Duplicate Findings

同一个 root cause 不得因为：

```text
影响多个文件
多个 Agent 重复发现
多个 test 失败
```

拆成多个重复 finding。

应优先形成：

```text
一个 root-cause finding
```

并在正文中说明主要影响。

只有真正独立的 defect 才分开。

---

## 79. No Findings

如果没有任何 candidate 满足 finding criteria：

```text
No findings.
```

不得为了避免空 review 而降低标准。

---

## 80. Final Output Structure

最终输出保持严格精简。

结构：

```text
Findings

Overall Assessment

Verification Gaps
```

---

## 81. Findings Section

如果存在 findings：

```text
Findings

[P1] ...
...

[P2] ...
...
```

如果没有：

```text
Findings

No findings.
```

不得增加：

```text
Suggestions
Nice to have
Things I liked
Future improvements
Architecture ideas
Style notes
```

---

## 82. Overall Assessment

Findings 后给出：

```text
brief overall assessment
```

只需要概括：

```text
发现多少 validated defects
整体 Requirement / design compliance 是否发现明显问题
review 是否完成完整 target coverage
```

保持简短。

不得重新复制所有 findings。

---

## 83. Verification Gaps

只报告：

```text
material verification gaps
```

例如：

```text
Requirement 不可获得
无法运行关键 integration test
无法访问 required database
无法确认 external service behavior
```

每个 gap 应说明：

```text
gap
+
residual risk
```

如果没有 material gap：

```text
可以省略该 section
```

---

## 84. No Separate Merge Verdict

不额外输出：

```text
Approve
Request Changes
Merge
Do not merge
Safe to merge
Merge status
```

原因：

```text
P0 到 P3 已经表达 recommended action
```

并且 `/review` target 不一定是 PR。

---

## 85. No Positive-Observation Padding

不得为了让报告显得平衡而添加：

```text
代码整体写得很好
测试写得不错
架构比较清晰
值得表扬的是
```

除非这些内容对解释：

```text
overall assessment
```

确实必要。

`/review` 的重点是：

```text
validated findings
```

---

## 86. No Generic Suggestions

不得在 findings 后附加：

```text
以后可以考虑
可以进一步优化
建议重构
建议增加 abstraction
可以提高可读性
```

这类 generic suggestion。

如果它不满足 finding criteria：

```text
不输出
```

---

## 87. No Repository-Wide Audit

`/review` 不主动审计：

```text
整个 repository architecture
整个安全体系
全部 dependency
所有历史 technical debt
全部测试覆盖率
所有大型文件
全仓命名一致性
```

调查只能围绕：

```text
review target
+
其实际 affected call path
```

---

## 88. No Opportunistic Architecture Review

如果当前 change 只是：

```text
局部 Bug fix
```

不得借 review 讨论：

```text
整个 module 是否应该重写
service 是否应该拆分
是否应该换 framework
是否应该增加新 subsystem
```

除非当前 change 已经造成一个具体 defect。

---

## 89. No Style Policing

不得将纯 style preference 报告为 finding。

例如：

```text
我更喜欢 early return
这里可以用 map
这个函数可以更短
变量名还可以更漂亮
可以抽 helper
可以换 design pattern
```

除非它已经造成：

```text
真实误解
责任边界破坏
逻辑 divergence
实际 maintainability regression
```

---

## 90. No Speculative Future Problems

不得报告：

```text
如果以后用户达到一千万可能有问题
未来可能需要扩展
将来可能增加第三种角色
以后可能需要 plugin
```

除非这些未来要求已经是：

```text
当前明确 Requirement
```

---

## 91. No Unsupported Security Alarm

不得仅因为代码涉及：

```text
auth
database
user input
network
```

就声称存在 security issue。

必须证明：

```text
具体攻击路径
或
具体 boundary violation
```

达到 finding 标准。

---

## 92. No Unsupported Performance Alarm

不得仅因为存在：

```text
loop
query
allocation
serialization
```

就报告 performance issue。

必须证明：

```text
当前 change
+
真实 relevant path
+
meaningful impact
```

---

## 93. No Test-Only Reasoning

不得仅因为：

```text
测试失败
```

就停止分析。

必须判断：

```text
test 是否正确
test 是否相关
失败是否由当前 change 导致
失败是否代表真实 behavior defect
```

同样：

```text
tests passed
```

也不能自动证明 implementation 正确。

---

## 94. No False Verification

未运行的 command 不得报告：

```text
passed
```

没有完整检查的 target 不得声称：

```text
full review completed
```

没有确认 Requirement 时不得声称：

```text
Requirement compliant
```

---

## 95. No Majority Voting

multi-agent review 中不得：

```text
3 个 Agent 认为有 Bug
2 个 Agent 认为没有
→ 自动判定有 Bug
```

正确流程：

```text
主 Agent 验证 evidence
↓
独立判断
```

---

## 96. No Automatic Fix

任何 finding 都不得触发：

```text
edit
patch
format
test rewrite
config change
dependency update
```

`/review` 结束时 workspace 应保持：

```text
与 review 开始前一致
```

除了非持久性的正常运行结果。

---

## 97. Workspace Integrity Check

完成 review 前，应合理确认：

```text
没有因为 /review 修改 tracked file
没有删除用户文件
没有改变 branch
没有 stash
没有 reset
没有留下 Agent 创建的正式 artifact
```

如果某个验证工具自己产生 build artifact，而这是项目正常行为：

```text
不主动删除用户原有 artifact
```

也不得用危险 cleanup 命令清理。

---

## 98. Completion Condition

不得因为：

```text
已经找到一个 Bug
已经读完 diff
subagent 都完成了
测试通过
没有想到更多问题
```

就认为 `/review` 已完成。

正确完成条件是：

```text
review target 已可靠确定
+
comparison base 已可靠确定，如果适用
+
review target 非空
+
Requirement 已尽可能确定
+
confirmed design 已尽可能确定
+
applicable repository rules 已读取
+
完整 change 已检查
+
必要 affected call paths 已调查
+
相关 tests / types / schema / contracts 已按需检查
+
candidate findings 已逐一验证
+
targeted verification 已按需执行
+
与 change 相称的 repository-standard checks 已按需执行
+
material verification gaps 已记录
+
multi-agent 结果已去重并由主 Agent 重新判断，如果适用
+
所有 validated findings 已报告
+
没有把 speculative concern 当作 finding
+
workspace 没有被 /review 修改
```

---

## 99. Blocked Review

如果出现：

```text
review target 无法确定
comparison base 无法可靠确定
review target 无效
review target 为空
代码无法访问
repository 状态无法安全读取
```

并且这些问题会阻止可靠 review：

```text
停止
↓
说明 blocker
↓
说明已经确认的内容
↓
说明缺失信息
```

不得假装完成 review。

但以下情况默认不会阻止 defect review：

```text
没有 confirmed 或 completed design
没有完整 Requirement
部分 verification 无法运行
```

这些应根据情况作为：

```text
Verification Gap
```

处理。

---

## 100. Relationship with a Second `/review`

如果第一次 `/review` 发现：

```text
[P1]
[P2]
```

用户通过 `/implement` 修复后再次运行：

```text
/review
```

新的 `/review`：

```text
重新确定当前 review target
重新读取当前 code
重新验证当前 implementation
```

不得直接假设：

```text
之前 findings 已修复
```

也不得只检查旧 findings。

必须再次覆盖：

```text
当前完整 change
```

因为修复本身可能引入新的 defect。

---

## 101. Prohibited Behaviors

### 禁止修改代码

`/review` 必须保持 read-only。

---

### 禁止自动修复 finding

修复属于新的 `/implement`。

---

### 禁止自动进入 `/implement`

`/review` 输出后必须结束。

---

### 禁止 repository-wide audit

只审查当前 specific change 及其必要影响链。

---

### 禁止只看 diff hunk

必须读取足够 surrounding context。

---

### 禁止找到第一个 Bug 后停止

必须完成完整 review target。

---

### 禁止猜 review target

target 或 base 无法可靠确定时必须停止询问。

---

### 禁止猜 Requirement

无法确定时记录 verification gap。

---

### 禁止把 draft design 当作正式 contract

只有 `status: confirmed` 或 `status: completed` design 具有正式 design-compliance 权威。

---

### 禁止把个人偏好当作 finding

generic style、architecture preference 不属于 defect。

---

### 禁止报告 speculative concern

finding 必须有 evidence。

---

### 禁止报告无关历史问题

pre-existing issue 默认不属于当前 review。

---

### 禁止把 intended behavior change 当 regression

必须先确认 Requirement 和 design。

---

### 禁止为了找 finding 降低标准

允许最终结果为：

```text
No findings.
```

---

### 禁止把 subagent 输出直接返回

主 Agent 必须重新验证、去重和判断。

---

### 禁止使用 Agent 数量投票

重复发现只能提高验证优先级。

---

### 禁止固定角色切分 multi-agent review

所有 Agent 独立审查完整 change。

---

### 禁止默认无限增加 Agent

普通 change 默认单 Agent，高风险 change 默认多 Agent，最大 5 个。

---

### 禁止自动多轮 review

每次 `/review` 只运行一轮。

---

### 禁止机械运行所有测试

verification 必须与当前 change 相称。

---

### 禁止伪造 verification

未运行的检查不得报告成功。

---

### 禁止安装 dependency

dependency 缺失导致无法验证时记录 gap。

---

### 禁止危险 Git 操作

不得：

```text
stash
reset
clean
force checkout
rebase
merge
```

---

### 禁止修改 branch state

不得为了 review 切换用户当前 worktree branch。

---

### 禁止把 failed tooling 自动当 finding

必须分析 root cause。

---

### 禁止把 passing tests 当正确性证明

tests 是 evidence 的一部分，不是完整 review。

---

### 禁止输出无意义建议

最终输出保持 defect-first。

---

### 禁止额外 merge verdict

P0 到 P3 已提供处理优先级。

---

## 102. Recommended Execution Flow

完整流程：

```text
用户运行 /review
↓
是否明确指定 review target？
├── 是
│   ↓
│   使用用户指定 target
│
└── 否
    ↓
    working tree 是否有 change？
    ├── 是
    │   ↓
    │   review staged
    │   + unstaged
    │   + relevant untracked files
    │
    └── 否
        ↓
        确定当前 branch 的 actual base
        ↓
        计算 merge-base
        ↓
        review branch change
↓
验证：
    target 有效
    target 非空
    base 可靠，如果适用
↓
读取 repository instructions
↓
确定 Requirement
↓
寻找 related confirmed 或 completed design
↓
建立 review basis：
    Requirement
    confirmed 或 completed design，如果存在
    repository rules
    existing behavior
↓
检查当前 change 风险
↓
决定 Agent 数量：
    普通 change
    → 1 Agent

    高风险 / 核心 / 不确定 change
    → 3 Agents

    用户指定
    → 1 到 5
↓
读取完整 diff
↓
对每个 changed path：
    读取足够 surrounding code
    ↓
    检查相关 caller / consumer
    ↓
    检查 tests / helpers
    ↓
    按需检查：
        types
        schemas
        config
        migrations
        contracts
        error path
        cleanup path
        concurrency path
        trust boundary
↓
寻找 candidate findings：
    Requirement compliance
    design compliance
    correctness
    regression
    security
    performance
    maintainability
    testing
↓
对每个 candidate：
    是否由 current change 引入或明显恶化？
    ├── 否
    │   └── 丢弃
    │
    └── 是
        ↓
        是否有 meaningful impact？
        ├── 否
        │   └── 丢弃
        │
        └── 是
            ↓
            是否有代码 evidence？
            ├── 是
            │   ↓
            │   继续
            │
            └── 否
                ↓
                运行最小非破坏性 verification
                ↓
                是否得到支持？
                ├── 否
                │   └── 丢弃
                │
                └── 是
                    ↓
                    继续
            ↓
            是否 discrete / actionable / worth fixing？
            ├── 否
            │   └── 丢弃
            │
            └── 是
                ↓
                validated finding
↓
继续完成剩余 review target
↓
运行与当前 change 相称的 repository-standard verification：
    relevant tests
    typecheck
    lint
    build
    integration checks
↓
处理 verification failures：
    current-change defect
    → candidate finding

    pre-existing
    → 不报告

    environment / unavailable
    → Verification Gap
↓
如果使用 multi-agent：
    主 Agent 汇总
    ↓
    去重
    ↓
    重新验证
    ↓
    丢弃 unsupported findings
↓
为 validated findings 分配：
    P0
    P1
    P2
    P3
↓
按 severity 排序
↓
确认 workspace 未被修改
↓
输出：

    Findings

    Overall Assessment

    Verification Gaps
↓
结束 /review
```

---

## 103. Final Principle

`/review` 的质量不取决于：

```text
发现多少问题
输出多长
运行多少测试
使用多少 Agent
```

而取决于：

```text
是否审查了正确的 change
+
是否理解真实 Requirement
+
是否考虑 confirmed design
+
是否理解完整 implementation
+
是否追踪必要影响链
+
是否只报告真实 defect
+
是否为 finding 提供可靠 evidence
+
是否避免 speculative noise
+
是否保持 review 独立且 read-only
+
是否诚实说明 verification gap
```

最终原则：

> Review the actual change, prove the defect, report only what is worth fixing.
