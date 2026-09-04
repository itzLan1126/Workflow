# `/implement` Skill Specification

## 1. Purpose

`/implement` 用于根据已经明确的 Requirement 和可用的 confirmed design，完成正式 production implementation。

它的核心目标不是：

```text
让代码能够运行
```

而是：

> 在严格满足当前 Requirement 和 confirmed design 的前提下，按照真实项目已有结构和约定，写出正确、清晰、稳定、可维护、易于继续修改和验证的正式代码。

`/implement` 重点关注：

```text
Correctness
Readability
Reliability
Maintainability
Reasonable extensibility
Consistency
Simplicity
Error handling
Type safety
Testability
Regression risk
Security when relevant
Performance when relevant
```

这些不是要求 Agent 为每一项机械输出检查结果。

它们是 implementation 过程中需要根据当前任务实际考虑的质量维度。

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

用户需要手动调用：

```text
/review
```

才能进入正式 implementation review。

---

## 3. Boundary with `/discuss`

`/discuss` 负责解决：

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

`/implement` 不负责重新决定这些内容。

如果 implementation 过程中发现 Requirement 本身不明确，并且不同理解会明显改变最终行为：

```text
发现 Requirement ambiguity
↓
确认无法通过已有上下文解决
↓
停止 /implement
↓
指出具体未决问题
↓
要求返回 /discuss
```

不得：

```text
猜用户想要什么
选择自己更喜欢的产品行为
静默扩大 scope
把技术方便当成 Requirement
```

---

## 4. Boundary with `/design`

`/design` 负责决定：

```text
How exactly should we implement it?
```

包括已经确认的重要：

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

如果存在 confirmed design：

> `/implement` 必须严格按照 confirmed design 执行。

`/implement` 不是第二个 `/design`。

---

## 5. Low-Level Implementation Freedom

严格执行 design 不代表 design 必须规定每一行代码。

`/implement` 仍然负责普通低层实现 Decision，例如：

```text
局部变量命名
局部 helper 命名
函数内部控制流
普通条件判断组织
小型内部 helper
测试代码具体写法
局部 type narrowing
普通错误传播方式
符合现有 pattern 的低层实现选择
```

这些 Decision 必须满足：

```text
不改变 Requirement
+
不改变 confirmed design
+
不扩大 scope
+
符合项目已有 pattern
```

---

## 6. What Counts as Design Deviation

以下通常属于 design deviation：

```text
改变 Implementation Approach
改变关键模块职责
改变重要数据流
改变重要控制流
改变已经确认的 interface
改变 data model
改变 compatibility behavior
改变重大 error-handling strategy
增加 design 未允许的重要 dependency
引入新的核心 subsystem
改变关键 persistence strategy
改变关键 concurrency model
改变关键 testing goal
明显扩大主要文件或模块范围
```

如果 implementation 必须进行这些改变：

```text
停止 /implement
```

不得自行调整后继续。

---

## 7. Strict Design Compliance

如果发现 confirmed design 无法按原方案可靠实现：

```text
发现冲突
↓
调查并确认冲突真实存在
↓
停止当前 implementation
↓
说明：
    design 原本要求什么
    实际项目事实是什么
    为什么两者冲突
    哪部分无法继续
↓
要求重新运行 /design 或 /improve
```

不得：

```text
静默偏离 design
边写边重设计
实现完成后才说明重大偏差
为了省事选择另一套 architecture
自行修改 confirmed design
```

---

## 8. `/implement` Can Run Without a Design

`/implement` 不强制要求之前运行 `/design`。

例如：

```text
typo
小型 Bug
简单局部修改
明确的小功能
机械性修改
```

如果当前 Requirement 已经足够明确，可以直接：

```text
/implement
```

---

## 9. Behavior Without a Design

不存在 confirmed design 时：

```text
读取用户 Requirement
↓
调查相关项目事实
↓
判断 Requirement 是否足够明确
↓
使用项目已有结构和 pattern
↓
完成最小合理 implementation
```

但没有 design 不代表 Agent 获得无限技术自治。

如果任务需要新的重大 Technical Decision，例如：

```text
增加新的核心 subsystem
引入重要 dependency
改变长期 architecture
改变 persistence model
改变公共 API strategy
进行难以回滚的结构变化
```

则应停止 `/implement`，要求先运行：

```text
/design
```

---

## 10. Draft Design Is Not Authoritative

如果当前任务存在：

```yaml
status: draft
```

的 design：

```text
draft design
≠
confirmed implementation contract
```

Agent 不得把 draft 当作 confirmed design 静默执行。

如果用户明确要求绕过该 draft 直接实现，并且 Requirement 已经足够明确，可以按 no-design 模式执行。

如果 draft 中仍包含会影响实现的重要未决问题，则不得猜测，应停止并要求完成 `/design`。

---

## 11. Design Discovery

如果用户没有明确提供 design 文件路径，但当前上下文明显存在相关 design，Agent 应调查：

```text
当前任务
当前对话
design 目录
当前工作区
最近相关 design
```

目标是确认是否存在当前任务对应的：

```yaml
status: confirmed
```

design。

如果相关 design 为：

```yaml
status: completed
```

则它只提供之前实现的背景信息，不再作为后续 `/implement` 的 contract，也不回退状态。

不得仅因为：

```text
文件最新
文件名最相似
```

就选择一个 design。

如果存在多个无法可靠区分的 confirmed design：

```text
停止
↓
列出候选 design
↓
要求用户确认
```

---

## 12. Read Before Write

`/implement` 不得收到 Requirement 后立即开始修改代码。

正式修改前必须先理解：

```text
当前 Requirement
confirmed design，如果存在
相关代码
相关 abstraction
相关 module ownership
相关 interface
相关 type
相关测试
相关配置
项目 instructions
当前工作区状态
```

原则：

> Understand the existing system before changing it.

---

## 13. Repository Conventions First

项目自己的约定优先级高于 Agent 的通用偏好。

优先级：

```text
Repository conventions
↓
Existing local patterns
↓
Framework / language conventions
↓
Generic best practices
↓
Agent personal preference
```

Agent 应优先调查：

```text
AGENTS.md
CONTRIBUTING.md
README
项目文档
lint / formatter 配置
测试结构
package metadata
附近相似代码
项目已有 abstraction
```

不得为了使用自己熟悉的 pattern 而破坏项目一致性。

---

## 14. Search Before Writing

创建新的：

```text
helper
utility
service
component
hook
validator
abstraction
type
wrapper
```

之前，应合理检查项目是否已经存在：

```text
相同能力
类似能力
可以扩展的 owner
已有 utility
已有 domain abstraction
已有测试 helper
```

目标是避免：

```text
重复实现
平行 abstraction
功能相同但命名不同的 utility
无必要的新 layer
```

---

## 15. Responsibility Ownership

代码应放在真正负责该行为的模块中。

不得因为某个文件：

```text
当前已经打开
修改最方便
需要的代码最少
```

就把逻辑放进去。

Agent 应判断：

```text
Who owns this behavior?
```

优先：

```text
扩展已有 responsibility owner
```

其次才是：

```text
创建新的 cohesive unit
```

不得为了缩短实现路径：

```text
绕过 service
绕过 validation
绕过 permission boundary
绕过 domain layer
绕过项目已有 abstraction
```

---

## 16. Implement the Real Behavior

Agent 必须实现 Requirement 所代表的真实行为。

不得只针对：

```text
当前 example
当前 fixture
当前 route
当前字符串
当前测试输入
当前截图
当前错误案例
```

写 special case。

例如不得为了让测试通过而写：

```text
if input == exact_test_value
```

除非该 exact value 本身就是明确 domain rule。

原则：

> Fix or implement the underlying behavior, not the observed example.

---

## 17. Scope Discipline

`/implement` 必须保持当前任务 scope。

允许修改：

```text
实现当前 Requirement 必须修改的代码
+
维持当前 implementation 质量所必要的局部调整
+
当前行为需要的测试
+
当前行为需要的配置或类型
```

不得因为当前任务顺便：

```text
清理整个模块
统一无关代码风格
升级无关 dependency
重写旧 architecture
修复无关 Bug
重新命名无关 API
整理无关测试
现代化无关语法
```

---

## 18. Necessary Local Refactoring

允许为了当前 implementation 的质量进行必要局部重构。

例如为了：

```text
消除当前修改产生的明显重复
保持职责清晰
提高当前代码可读性
让当前行为可测试
避免当前修改破坏已有 abstraction
保持类型安全
避免明显错误处理重复
```

可以：

```text
提取局部 helper
调整当前函数结构
移动当前新增逻辑到正确 owner
整理直接相关的重复逻辑
```

前提：

```text
重构与当前任务直接相关
+
不会改变 confirmed design
+
不会扩大任务 scope
```

---

## 19. No Opportunistic Refactoring

不得以：

```text
代码看起来不够漂亮
顺便整理一下
以后可能会需要
这里一直都很乱
```

为理由扩大修改。

如果发现重要但无关的问题：

```text
不修改
```

必要时可以在最终输出中简短指出。

---

## 20. Simplicity

`/implement` 应优先：

```text
简单
明确
直接
容易理解
容易验证
容易修改
```

的实现。

不得把：

```text
更多 abstraction
更多 layer
更多 interface
更多 generic
更多 configuration
更多 indirection
```

自动等同于更高质量。

---

## 21. Reasonable Extensibility

可持续扩展性意味着：

> 当未来真实 Requirement 出现时，当前代码容易被安全修改。

它不意味着：

```text
提前实现未来功能
提前设计 plugin system
为未知场景增加 generic abstraction
为可能出现的第三种情况增加复杂 framework
创建没有当前需求依据的 extension point
```

目标是：

```text
low coupling
clear responsibility
clear contracts
understandable state
reasonable boundaries
```

而不是 speculative future-proofing。

---

## 22. Abstraction Rule

创建 abstraction 前，应确认它至少解决真实问题之一：

```text
消除有意义的重复
保护重要 invariant
明确 ownership
隔离真实复杂度
符合项目已有 architecture
形成实际需要的稳定 boundary
```

不得仅因为：

```text
两段代码看起来相似
以后可能复用
抽象看起来更高级
```

就创建 abstraction。

---

## 23. Do Not Create One-Use Abstractions Without Reason

如果一个 helper、wrapper、interface 或 layer：

```text
只使用一次
没有独立 responsibility
没有隐藏真实复杂度
没有保护重要 invariant
```

则通常不应该仅为了“结构更漂亮”创建。

但如果项目已有 pattern 明确要求这种结构，则遵循项目约定。

---

## 24. Readability

代码应让后续开发者能够快速理解：

```text
这段代码负责什么
数据从哪里来
状态在哪里改变
错误如何传播
重要条件是什么
为什么存在特殊处理
```

优先：

```text
clear naming
clear control flow
small coherent units
explicit behavior
predictable structure
```

避免：

```text
clever tricks
隐藏副作用
过度嵌套
不必要 indirection
含义模糊的名字
需要大量上下文才能理解的结构
```

---

## 25. Naming

命名应表达实际 intent。

不得因为节省字符而使用难以理解的名称。

普通局部变量可以保持简洁，但重要：

```text
domain object
state
function
class
service
event
error
boolean
```

应让读者能够理解其职责和语义。

应保持与项目现有术语一致。

同一个概念不得无理由使用多个术语。

---

## 26. Comments

Comment 应主要解释：

```text
为什么这样做
重要 constraint
非显然 invariant
兼容性原因
外部系统限制
看起来奇怪但必要的行为
```

不得使用 comment 重复明显代码：

```text
// increment count
count++
```

如果需要大量 comment 才能解释代码在“做什么”，应优先改善代码结构和命名。

---

## 27. Control Flow

优先让主要执行路径容易阅读。

需要时可以使用：

```text
early return
guard clause
small focused helper
clear state transition
```

降低：

```text
deep nesting
隐式 fallthrough
复杂 boolean expression
相互依赖的隐藏 side effect
```

但不得机械追求某一种代码风格。

以项目现有 convention 为准。

---

## 28. State and Side Effects

对涉及 state 的 implementation，应让以下内容尽可能明确：

```text
state ownership
state transition
mutation point
side effects
persistence boundary
external effects
```

不得无必要：

```text
复制同一状态
维护多个 source of truth
引入隐藏全局状态
在意外位置产生 side effect
```

---

## 29. Error Handling

错误处理必须属于真实 implementation，而不是最后补几个 `try/catch`。

Agent 应根据当前项目判断：

```text
错误在哪里产生
哪一层能够真正处理
哪一层应该传播
用户最终看到什么
是否需要 rollback
是否需要 retry
是否需要 logging
```

不得：

```text
silent swallow
无意义 catch 后继续
把所有异常转换成同一个模糊错误
隐藏原始 cause
让失败状态看起来像成功
```

---

## 30. Input and Boundary Validation

对于来自：

```text
用户输入
API
网络
文件
数据库外部数据
第三方 service
untrusted source
```

的数据，应在项目适当 boundary 进行必要 validation。

但不得：

```text
在每一层重复相同 validation
添加与当前风险无关的大量 defensive code
```

验证位置应符合已有 architecture。

---

## 31. Security

只有当前任务涉及相关风险时，才应重点处理安全问题。

例如：

```text
authentication
authorization
user-controlled input
secrets
file access
network request
HTML rendering
SQL
command execution
sensitive data
```

需要保证：

```text
不绕过已有安全 boundary
不泄露 secret
不把敏感内部错误直接暴露给用户
不因为方便禁用 validation
不因为测试困难降低 authorization
```

不得为了“安全”机械增加与当前任务无关的复杂度。

---

## 32. Performance

性能优化必须服务于真实问题。

不得：

```text
为了理论性能提前复杂化代码
无数据依据增加 cache
无需求依据增加 concurrency
为了减少极小开销牺牲可读性
```

如果 confirmed design 已经明确性能要求，则严格执行。

如果 implementation 发现当前 design 无法满足关键性能 Requirement，则停止并返回 `/design` 或 `/improve`。

---

## 33. Dependencies

优先使用：

```text
项目已有 dependency
语言 standard library
framework-native capability
项目已有 helper
```

不得因为一个小问题随意增加 dependency。

如果 confirmed design 没有允许，而 implementation 发现必须增加一个会明显影响：

```text
architecture
bundle
security
maintenance
compatibility
deployment
```

的重要 dependency，则视为 design deviation。

停止 `/implement`。

---

## 34. Type Safety

如果项目使用强类型系统，应尽可能利用现有类型能力表达真实约束。

不得为了快速通过编译而：

```text
大量使用 any
无依据 type assertion
关闭 type checking
扩大 ignore
把错误类型强转成目标类型
```

除非项目已有明确 pattern 或外部 API 确实需要，并且范围保持最小。

类型应该帮助表达：

```text
valid state
invalid state
optional data
boundary contracts
domain distinctions
```

---

## 35. Testing Is Part of Implementation

测试不是 implementation 完成后的附属步骤。

对于有行为变化的任务，测试属于正式 implementation 的一部分。

目标是证明：

```text
目标行为存在
+
错误行为被处理
+
关键边界行为正确
+
当前修改没有造成明显 regression
```

---

## 36. Real Tests

测试必须尽可能执行真实代码路径并验证真实可观察行为。

有效测试可能包括：

```text
unit test
component test
integration test
API test
database test
end-to-end test
```

具体层级根据当前行为和项目架构选择。

核心标准：

> 测试应该证明代码实际做了正确的事情。

---

## 37. Regex Is Not a Behavioral Test

以下不能在本应验证 runtime behavior 时作为主要测试：

```text
regex 匹配源码
grep
字符串存在检查
检查文件中是否出现某个函数名
检查 source 是否包含某段代码
只验证某个 method 被写出来
```

例如：

```text
expect(source).toContain("validateUser")
```

只能证明：

```text
某段文字存在
```

不能证明：

```text
validation 真的工作
错误真的被处理
真实用户行为正确
```

---

## 38. Static Checks Are Supplementary

静态检查不是完全禁止。

例如：

```text
lint
typecheck
schema validation
format verification
generated-file validation
source contract check
```

可以作为 supplementary verification。

但如果当前 Requirement 描述的是 runtime behavior：

```text
静态匹配
≠
真实行为测试
```

不得用正则或字符串检查代替真正测试。

---

## 39. Test the Observable Behavior

测试优先验证：

```text
输入
↓
真实执行路径
↓
输出
状态变化
side effect
error
observable UI behavior
```

不得主要测试：

```text
private helper 是否被调用
内部 method 调用了几次
实现用了哪个变量名
代码内部具体怎么组织
```

除非这些内容本身就是明确 contract。

---

## 40. Bug Fix Testing

对于 Bug fix，默认优先：

```text
构造能够真实复现 Bug 的测试
↓
确认测试失败
↓
实现修复
↓
确认测试通过
```

目标是证明：

```text
Bug 原本真实存在
+
当前 implementation 真实修复了它
```

不得只写一个：

```text
永远都会通过
或
没有经过真实错误路径
```

的测试。

---

## 41. Test-First Preference

对于：

```text
Bug fix
新 behavior
复杂 business logic
重要边界条件
```

默认优先 test-first。

推荐：

```text
write / update real test
↓
confirm expected failure when applicable
↓
implement
↓
make test pass
↓
refactor if necessary
↓
verify again
```

---

## 42. TDD Is Not Mechanical

`/implement` 不强制所有修改机械采用 TDD。

以下情况可以不要求先写失败测试：

```text
纯配置
纯文档
纯样式
机械性迁移
测试基础设施不存在
当前环境无法合理构造 test-first
```

但仍然需要适合当前修改的真实 verification。

---

## 43. Test Level Selection

选择能够可靠证明当前行为的最低合理测试层级。

例如：

```text
纯函数 behavior
→ unit test

多个 module interaction
→ integration test

React component user interaction
→ component test

HTTP contract
→ API / integration test

完整关键用户流程
→ E2E when justified
```

不得：

```text
所有东西都强制 E2E
```

也不得：

```text
所有行为都只 mock 成 unit test
```

---

## 44. Existing Tests

与当前 Requirement 直接相关的已有测试，可以根据真实行为变化进行必要修改。

允许：

```text
更新已经失效的 expectation
增加新的 behavioral case
增加 regression case
修正与 confirmed behavior 冲突的旧断言
调整测试结构以验证真实行为
```

不得为了让 implementation 通过：

```text
删除有效失败测试
弱化重要 assertion
把真实 behavioral test 改成字符串匹配
大量 mock 掉真正需要验证的代码
```

---

## 45. Mocks and Fakes

Mock、stub、fake 可以用于合理隔离：

```text
不稳定外部 service
昂贵 dependency
不可控第三方系统
真实 network
特定 failure injection
```

但不得把真正需要验证的项目行为全部 mock 掉。

测试必须仍然能够证明当前 implementation 的核心行为真实成立。

---

## 46. Incremental Implementation

复杂 implementation 应按 coherent slice 小步完成。

推荐：

```text
理解当前 slice
↓
必要时先写真实测试
↓
实现
↓
运行 targeted verification
↓
修复
↓
必要局部 refactor
↓
再次验证
↓
进入下一 slice
```

每个 slice 应尽可能保持项目：

```text
working
understandable
testable
```

---

## 47. Do Not Implement Everything Before Testing

不得采用：

```text
一次修改大量文件
↓
功能全部写完
↓
最后第一次运行测试
```

作为默认方式。

原因是这样会让：

```text
错误来源难以定位
regression 难以定位
design conflict 发现过晚
返工成本增加
```

应尽可能在自然 implementation boundary 上持续验证。

---

## 48. Layered Verification

验证采用分层方式。

第一层：

```text
最直接相关的 targeted tests
```

第二层，根据任务适用：

```text
related test suite
typecheck
lint
build
component tests
integration tests
```

第三层，根据风险扩大：

```text
broader test suite
broader integration verification
E2E
其他项目已有高层检查
```

---

## 49. Verification Scope Follows Risk

验证范围应根据：

```text
修改范围
修改层级
共享程度
调用数量
兼容性风险
数据影响
安全风险
回归风险
```

决定。

例如：

```text
局部纯函数修改
→ targeted tests 可能足够

共享 authentication middleware
→ 需要更广泛 verification
```

不得机械：

```text
每次运行整个 repository 所有测试
```

也不得只为了省时间永远只跑一个测试。

---

## 50. Existing Verification Commands

Agent 应优先使用项目真实存在的验证方式，例如：

```text
package scripts
Makefile
task runner
CI configuration
project documentation
existing test commands
```

不得凭框架经验猜测试命令。

例如不得看到：

```text
Node.js project
```

就默认：

```text
npm test
```

应先检查项目实际配置。

---

## 51. Test Failures

如果 verification 失败：

```text
调查失败原因
↓
判断是否由当前 implementation 导致
```

如果由当前修改导致：

```text
必须修复
↓
重新运行相关 verification
```

如果确认是已有且与当前修改无关的问题：

```text
不得擅自扩大 scope 修复
↓
记录实际失败
↓
继续判断它是否阻碍当前 implementation 的可靠验证
```

如果无法判断：

```text
不得宣称验证通过
```

---

## 52. Never Optimize for Tests Instead of Requirements

测试是 Requirement 的证据，不是新的 Requirement 来源。

如果：

```text
test
与
confirmed Requirement / design
```

冲突：

```text
不得为了让 test 变绿而违反 Requirement
```

应调查：

```text
测试是否过时
implementation 是否错误
design 是否存在冲突
```

必要时停止并返回正确 workflow 阶段。

---

## 53. Working Tree Awareness

正式实现前应检查当前工作区。

至少理解：

```text
当前 branch
HEAD
tracked changes
untracked files
与当前任务相关的未提交修改
与当前任务无关的用户修改
```

未提交修改不能被自动视为垃圾或错误状态。

---

## 54. Protect User Work

`/implement` 可以修改当前任务相关代码。

但不得为了方便：

```text
stash 用户修改
reset 用户修改
clean 用户文件
强制 checkout
覆盖无关未提交修改
删除无关 untracked files
恢复用户没有要求恢复的文件
```

如果当前任务需要修改一个用户已经编辑过的文件：

```text
先理解现有修改
↓
保留用户已有内容
↓
在其基础上完成当前 implementation
```

如果无法安全合并：

```text
停止
↓
说明冲突
```

不得覆盖。

---

## 55. Do Not Undo Unrelated Changes

如果发现当前 working tree 中存在与任务无关的修改：

```text
忽略并保护
```

不得：

```text
格式化整个 repository
顺便恢复
顺便提交
顺便删除
顺便整理
```

Agent 只负责当前 implementation。

---

## 56. Formatting

运行 formatter 时应控制范围。

优先：

```text
只格式化当前修改涉及的文件
```

除非项目工具本身安全且明确要求 broader formatting。

不得因为 formatter 产生大量无关 diff。

如果产生大量无关变化，应恢复由当前操作导致的无关格式修改，同时不得覆盖用户原有修改。

---

## 57. Generated Files

如果项目要求某些源修改同步生成：

```text
generated code
lock file
schema artifact
snapshot
client
types
```

并且这是项目正常 workflow 的必要部分：

```text
应按照项目已有命令生成
```

不得手工伪造 generated output。

---

## 58. Documentation During Implementation

如果当前 Requirement 会直接使已有：

```text
README
API docs
configuration docs
inline usage docs
```

失效，则应在当前 scope 内同步更新必要内容。

不得为了“文档更完整”扩大成全面 documentation rewrite。

---

## 59. Implementation Diff Review

在宣布 `/implement` 完成前，Agent 应自己重新检查当前 diff。

重点确认：

```text
每项修改是否属于当前任务
是否存在意外文件
是否存在 debug code
是否存在临时代码
是否存在被遗忘的 TODO
是否存在 hard-coded test value
是否存在不必要 abstraction
是否存在无意 API 变化
是否存在意外 formatting noise
是否存在 design deviation
```

这属于 implementation self-check。

它不代替正式 `/review`。

---

## 60. No Debug Artifacts

完成前应删除当前 implementation 产生的临时内容，例如：

```text
console.log
debug print
临时 endpoint
临时 flag
临时 fixture
临时代码
手工测试文件
临时 generated artifact
```

如果它们不是正式 implementation 的一部分，不得保留。

---

## 61. No False Completion

不得使用：

```text
应该可以
看起来没问题
理论上能工作
代码已经写完
```

作为完成依据。

原则：

```text
Code written
≠
Implementation complete
```

完成必须具有实际 verification evidence。

---

## 62. Verification Evidence

结束 `/implement` 时，应知道：

```text
运行了哪些 tests
运行了哪些 checks
哪些通过
哪些失败
哪些没有运行
为什么没有运行
```

不得：

```text
没有执行命令却声称测试通过
把未运行写成 passed
隐藏 failing checks
```

---

## 63. When Verification Cannot Be Completed

如果因为：

```text
环境缺少 dependency
需要外部 credential
service unavailable
平台能力不存在
测试基础设施损坏
当前环境不支持相关 runtime
```

无法完成某项重要 verification：

```text
明确说明
```

包括：

```text
没有验证什么
为什么无法验证
已经完成了哪些替代验证
剩余风险是什么
```

不得编造结果。

---

## 64. Completion Condition

不得因为以下原因请求用户确认 `/implement` 已完成：

```text
代码已经写完
测试文件已经创建
编译器没有马上报错
Agent 认为逻辑正确
target test 运行过一次
diff 看起来合理
```

请求确认前的正确完成条件是：

```text
Requirement 已实现
+
如果存在 confirmed design，则 implementation 与 design 一致
+
代码符合项目已有 convention
+
没有已知必要 scope 遗漏
+
必要真实测试已完成
+
适用的 verification 已完成
+
当前修改导致的失败已经解决
+
没有未说明的重要验证缺口
+
没有意外修改用户无关工作
+
没有临时 implementation artifact
```

满足上述条件后，Agent 必须先报告 implementation 和 verification 结果，再请求用户确认实现完成。只有用户明确确认后，`/implement` 才正式完成。

如果存在当前实现所遵循的 `status: confirmed` design，用户确认后立即将其改为：

```yaml
status: completed
```

没有关联 design 时仍须请求确认，但不修改 design 文件。如果用户不确认，则保持 `status: confirmed`，根据反馈继续修改和验证，再次请求确认。已经是 `status: completed` 的 design 只作为后续实现的背景，不回退或重复修改。

---

## 65. Blocked Completion

如果存在会阻止可靠完成的问题：

```text
Requirement ambiguity
confirmed design conflict
重大 Technical Decision
无法安全处理 working tree conflict
关键 verification 无法完成
implementation 必须偏离 design
```

则 `/implement` 不得假装完成。

应：

```text
停止
↓
说明 blocker
↓
说明已经完成的工作
↓
说明未完成的部分
↓
指出应该进入：
    /discuss
    /design
    /improve
    或由用户解决环境问题
```

---

## 66. Relationship with `/review`

`/implement` 负责：

```text
写出 Agent 当前认为正确且高质量的 production implementation
+
完成合理 verification
```

`/review` 负责：

```text
独立审查 actual implementation
```

包括进一步检查：

```text
correctness
regression
design compliance
code quality
security
performance
implementation mistakes
```

因此：

```text
/implement 自己检查代码
≠
/review
```

`/implement` 不得因为后面还有 `/review`：

```text
降低自身代码质量
故意留下问题
减少必要测试
省略 verification
```

---

## 67. Version Control Boundary

`/implement` 的核心职责是：

```text
implementation
+
verification
```

不是 Git workflow。

除非用户在当前任务中明确要求，否则 `/implement` 不自动：

```text
commit
push
创建 PR
merge
rebase
```

这些操作不属于 `/implement` 完成条件。

---

## 68. Prohibited Behaviors

### 禁止猜 Requirement

不明确且会影响行为的问题必须返回 `/discuss`。

---

### 禁止静默偏离 confirmed design

任何重大 design deviation 都必须停止 `/implement`。

---

### 禁止自行重设计

`/implement` 不能变成第二个 `/design`。

---

### 禁止为了方便绕过 architecture

不得绕过正确的 responsibility owner、validation、permission 或 domain boundary。

---

### 禁止针对测试样例打补丁

必须实现真实 behavior。

---

### 禁止测试驱动的错误实现

不得为了让 test 通过而违反 Requirement。

---

### 禁止把正则匹配当成真实测试

源码字符串、regex 或 grep 不能替代 behavioral verification。

---

### 禁止虚假测试

不得写一个不执行目标真实逻辑、却永远容易通过的测试来证明完成。

---

### 禁止过度 mock

不得 mock 掉真正需要验证的核心 behavior。

---

### 禁止无测试证据宣称修复成功

Bug fix 应尽可能有真实 reproduction / regression test 或其他真实行为验证。

---

### 禁止无关重构

不得借 implementation 扩大 scope。

---

### 禁止过度设计

不得为未知未来需求增加无必要 abstraction、layer 或 extension point。

---

### 禁止重复造轮子

创建新 abstraction 前应合理检查已有能力。

---

### 禁止随意增加 dependency

重要 dependency 变化必须符合 confirmed design，或返回 `/design`。

---

### 禁止 silent error handling

不得吞掉重要错误并继续假装成功。

---

### 禁止为了编译通过破坏 type safety

不得无依据使用 `any`、强制 cast 或扩大 ignore。

---

### 禁止覆盖用户工作

不得 reset、stash、clean、强制 checkout 或覆盖无关修改。

---

### 禁止大范围无关格式化

formatting 不得制造大量与当前任务无关的 diff。

---

### 禁止保留 debug artifact

临时调试内容必须在完成前清理。

---

### 禁止伪造 verification

未运行的测试不得报告为通过。

---

### 禁止自动进入 `/review`

用户确认 `/implement` 完成后停止。

---

## 69. Recommended Execution Flow

完整流程：

```text
用户运行 /implement
↓
读取当前 Requirement 和上下文
↓
寻找当前任务相关 design
↓
design 状态是什么？
├── confirmed
│   ↓
│   读取完整 design
│   ↓
│   将 design 作为 implementation contract
│
├── completed
│   ↓
│   读取为背景信息，不作为 implementation contract
│
└── draft 或不存在
    ↓
    判断 Requirement 是否足够明确
    ├── 否
    │   └── 停止
    │       ↓
    │       要求返回 /discuss
    │
    └── 是
        ↓
        继续 no-design implementation
↓
检查当前 branch / HEAD / working tree
↓
保护无关用户修改
↓
读取 repository instructions
↓
调查相关代码、测试、类型、配置和 abstraction
↓
确认 behavior ownership
↓
检查是否需要重大 Technical Decision
├── 是
│   └── 停止
│       ↓
│       要求运行 /design
│
└── 否
    ↓
确定最小合理 implementation scope
↓
把复杂任务拆成 coherent slices
↓
针对当前 slice：
    ↓
    是否适合 test-first？
    ├── 是
    │   ↓
    │   写或更新真实 behavioral test
    │   ↓
    │   必要时确认测试失败
    │
    └── 否
        ↓
        确定其他真实 verification 方法
    ↓
    实现最简单的正确方案
    ↓
    检查：
        correctness
        readability
        responsibility
        simplicity
        error handling
        type safety
        scope
    ↓
    运行 targeted verification
    ↓
    是否失败？
    ├── 是
    │   ↓
    │   调查原因
    │   ↓
    │   当前修改导致？
    │   ├── 是
    │   │   └── 修复
    │   │       ↓
    │   │       重新验证
    │   │
    │   └── 否
    │       └── 记录已有问题
    │
    └── 否
        ↓
        必要局部 refactor
        ↓
        再次验证
↓
进入下一 coherent slice
↓
所有 slice 完成
↓
运行适用的：
    related tests
    typecheck
    lint
    build
    integration tests
↓
根据风险决定是否扩大 verification
↓
检查最终 diff
↓
发现 design deviation？
├── 是
│   └── 停止
│       ↓
│       要求返回 /design 或 /improve
│
└── 否
    ↓
检查无关修改、debug artifact 和临时文件
↓
确认 verification evidence
↓
输出 implementation 结果
↓
请求用户确认实现完成
├── 不确认
│   ↓
│   保持 status: confirmed
│   ↓
│   根据反馈继续修改和验证
│   ↓
│   再次请求确认
│
└── 确认
    ↓
    关联 design 是 status: confirmed？
    ├── 是
    │   └── 改为 status: completed
    └── 否
        └── 不修改 design
    ↓
    停止
    ↓
    等待用户手动运行 /review
```

---

## 70. Final Output

`/implement` 完成后，应简洁说明：

```text
实现了什么
主要修改了哪些部分
运行了哪些真实 tests / checks
验证结果
是否存在无法完成的 verification
是否存在需要用户知道的限制或已有问题
```

说明这些结果后，必须请求用户确认实现完成；确认后再更新关联 design 状态并结束。

如果使用了 confirmed design，应明确：

```text
implementation follows the confirmed design
```

如果没有偏差，不需要重新解释完整 design。

不要输出：

```text
完整思考过程
逐行代码解释
无关架构讨论
冗长测试日志
```

除非用户明确要求。

---

## 71. Mental Model

`/implement` 不应该像：

```text
看到需求
↓
尽快写出能跑的代码
↓
让测试变绿
```

也不应该像：

```text
趁机把相关代码全部重构得更漂亮
```

更接近：

```text
Understand the requirement
↓
Respect the confirmed design
↓
Understand the real codebase
↓
Find the correct responsibility owner
↓
Write the simplest correct production code
↓
Verify real behavior
↓
Improve locally where necessary
↓
Verify again
↓
Finish with evidence
```

最终目标是：

> 根据已经明确的 Requirement 和 confirmed design，在不扩大 scope、不猜测需求、不破坏项目已有结构的前提下，完成一份真实可运行、经过实际验证、清晰稳定并且能够长期维护和继续演进的 production implementation。
