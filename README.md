# skillforge

给自己攒的一套 agent skill，遵循 [Agent Skills 规范](https://agentskills.io/specification)：一个目录一个 skill，`SKILL.md` 带 YAML frontmatter，支撑文件按需加载。

不是「教程合集」。每条 skill 的目标是：把 agent 从「看起来答得像样」推到「给出的东西能直接落地」——
每个结论都带数值、每条命令都能跑、每条规则都能说出它防的是哪个错误。

## 装

```bash
git clone https://github.com/hexinzxq/skillforge.git
cd skillforge

./install.sh                          # 软链到 ~/.claude/skills
./install.sh --project ~/code/app     # 装进某个项目的 .claude/skills
./install.sh --only frontend-design   # 只装一个
./install.sh --vendor                 # 连 vendor/ 里那 61 个一起装
./install.sh --copy                   # 复制而不是软链
./install.sh --list                   # 看这仓库里有什么
./install.sh --remove                 # 卸掉（只删自己建的软链）
```

软链是默认的：改了仓库里的文件，agent 下次读到的就是新版。

默认只装 `skills/` 里自己写的那个；`--vendor` 才把收录的 61 个一起装上。
同名的以自己写的为准（比如 `test-driven-development` 在 superpowers 和
agent-skills 里各有一份，只装排在前面那个），`--list` 会把两边的都列出来。

## 有什么

### 自己写的

| skill | 什么时候用 | 产出 |
|---|---|---|
| [`frontend-design`](skills/frontend-design/SKILL.md) | 要做界面、要好看、要「企业级不像模板」 | 先出一份设计计划（语气/配色/版式/动效各定一句），再写码；带 AI 味黑名单和交付前自检清单 |

### 收录的（[vendor/](vendor/README.md)）

别人的东西不掺进来但也不藏着，原样抄在 `vendor/` 下、保留原许可：

| 目录 | 来源 | 收了多少 |
|---|---|---|
| `vendor/superpowers` | [obra/superpowers](https://github.com/obra/superpowers) | 15 个，方法论向：先规划再动手、系统化调试、验证后再收工 |
| `vendor/agent-skills` | [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills) | 25 个，工程向：代码评审、错误恢复、安全加固、性能优化、前端 UI |
| `vendor/find-skills` | [vercel-labs/skills](https://github.com/vercel-labs/skills) | 1 个，元技能：按任务去生态里找现成 skill |
| `vendor/agent-skills-standard` | [HoangNguyen0403/agent-skills-standard](https://github.com/HoangNguyen0403/agent-skills-standard) | 20 个，语言与框架级规范，从上游 299 条里挑的 |

## 全部 skill 速查

六十二个，一句话一个。加新 skill 时记得往这张表补一行。

### 自己写的

| skill | 一句话 |
|---|---|
| [frontend-design](skills/frontend-design/) | 出界面先给设计计划（配色/版式/动效各定一句）再写码，专治 AI 模板味 |

### 通用工程规范（agent-skills-standard）

| skill | 一句话 |
|---|---|
| [common-accessibility](vendor/agent-skills-standard/common/common-accessibility/) | WCAG 2.2 AA：语义标签、键盘可达、对比度 |
| [common-api-design](vendor/agent-skills-standard/common/common-api-design/) | REST 约定：状态码、分页、幂等、OpenAPI |
| [common-best-practices](vendor/agent-skills-standard/common/common-best-practices/) | 函数别超长、守卫子句早返回、命名说人话 |
| [common-code-review](vendor/agent-skills-standard/common/common-code-review/) | PR 评审分档，按严重度给意见 |
| [common-debugging](vendor/agent-skills-standard/common/common-debugging/) | 用科学方法排错：先证据再改码 |
| [common-documentation](vendor/agent-skills-standard/common/common-documentation/) | 注释写意图，README 写怎么跑 |
| [common-error-handling](vendor/agent-skills-standard/common/common-error-handling/) | 错误分层、包装上下文、别吞异常 |
| [common-git-collaboration](vendor/agent-skills-standard/common/common-git-collaboration/) | 分支、提交、PR 的规矩 |
| [common-performance-engineering](vendor/agent-skills-standard/common/common-performance-engineering/) | 先测量再优化：异步、内存、吞吐 |
| [common-security-standards](vendor/agent-skills-standard/common/common-security-standards/) | 鉴权、输入校验、密钥处理 |

### TypeScript / React / Next.js（agent-skills-standard）

| skill | 一句话 |
|---|---|
| [typescript-language](vendor/agent-skills-standard/typescript/typescript-language/) | strict、泛型、联合类型、tsconfig |
| [typescript-best-practices](vendor/agent-skills-standard/typescript/typescript-best-practices/) | 类、函数、模块的惯用写法 |
| [react-component-patterns](vendor/agent-skills-standard/react/react-component-patterns/) | 组合优于继承，组件怎么拆 |
| [react-hooks](vendor/agent-skills-standard/react/react-hooks/) | effect 边界、依赖数组、自定义 hook |
| [react-performance](vendor/agent-skills-standard/react/react-performance/) | 重渲染定位、memo、瀑布流 |
| [react-testing](vendor/agent-skills-standard/react/react-testing/) | RTL 测行为不测实现 |
| [nextjs-app-router](vendor/agent-skills-standard/nextjs/nextjs-app-router/) | 路由段、嵌套 layout、error boundary |
| [nextjs-data-fetching](vendor/agent-skills-standard/nextjs/nextjs-data-fetching/) | fetch 缓存与 revalidate 怎么配 |
| [nextjs-optimization](vendor/agent-skills-standard/nextjs/nextjs-optimization/) | 图片、字体、脚本、Core Web Vitals |
| [nextjs-server-components](vendor/agent-skills-standard/nextjs/nextjs-server-components/) | RSC 与 `'use client'` 的边界放哪 |

### 工程流程（addyosmani/agent-skills）

| skill | 一句话 |
|---|---|
| [api-and-interface-design](vendor/agent-skills/api-and-interface-design/) | 接口和模块边界的稳定性设计 |
| [browser-testing-with-devtools](vendor/agent-skills/browser-testing-with-devtools/) | 借 Chrome DevTools MCP 在真浏览器里验 |
| [ci-cd-and-automation](vendor/agent-skills/ci-cd-and-automation/) | CI/CD 流水线与质量门禁 |
| [code-review-and-quality](vendor/agent-skills/code-review-and-quality/) | 多维度评审，合并前必过 |
| [code-simplification](vendor/agent-skills/code-simplification/) | 行为不变的前提下把代码变简单 |
| [constraint-driven-development](vendor/agent-skills/constraint-driven-development/) | 把质量底线写成合同，防悄悄降标 |
| [context-engineering](vendor/agent-skills/context-engineering/) | 新会话或换任务时先整理上下文 |
| [debugging-and-error-recovery](vendor/agent-skills/debugging-and-error-recovery/) | 从失败测试和崩溃里找根因 |
| [deprecation-and-migration](vendor/agent-skills/deprecation-and-migration/) | 老系统下线与用户迁移 |
| [documentation-and-adrs](vendor/agent-skills/documentation-and-adrs/) | 写 ADR，把决策理由留在库里 |
| [doubt-driven-development](vendor/agent-skills/doubt-driven-development/) | 重要决定先被新鲜上下文挑一遍刺 |
| [frontend-ui-engineering](vendor/agent-skills/frontend-ui-engineering/) | 生产级、可访问、响应式的界面 |
| [git-workflow-and-versioning](vendor/agent-skills/git-workflow-and-versioning/) | 提交、分支、拆未完成的工作 |
| [idea-refine](vendor/agent-skills/idea-refine/) | 把模糊想法逼成锋利可做的概念 |
| [incremental-implementation](vendor/agent-skills/incremental-implementation/) | 小步交付，每步都能验 |
| [interview-me](vendor/agent-skills/interview-me/) | 一次问一个问题，挖出你真正想要的 |
| [observability-and-instrumentation](vendor/agent-skills/observability-and-instrumentation/) | 日志、指标、追踪、告警怎么加 |
| [performance-optimization](vendor/agent-skills/performance-optimization/) | 前端到数据库的性能瓶颈 |
| [planning-and-task-breakdown](vendor/agent-skills/planning-and-task-breakdown/) | 把需求拆成能按顺序做的任务 |
| [security-and-hardening](vendor/agent-skills/security-and-hardening/) | 输入处理、认证、存储的加固 |
| [shipping-and-launch](vendor/agent-skills/shipping-and-launch/) | 上线前该有的东西清单 |
| [source-driven-development](vendor/agent-skills/source-driven-development/) | 每个决定先对官方文档核一遍 |
| [spec-driven-development](vendor/agent-skills/spec-driven-development/) | 没 spec 就先写 spec |
| [test-driven-development](vendor/agent-skills/test-driven-development/) | 红绿重构 |
| [using-agent-skills](vendor/agent-skills/using-agent-skills/) | 开工前先判断这活该用哪个 skill |

### 方法论（superpowers）

| skill | 一句话 |
|---|---|
| [brainstorming](vendor/superpowers/brainstorming/) | 动手前弄清楚对方到底要什么 |
| [diagnosing-superpowers](vendor/superpowers/diagnosing-superpowers/) | 会话跑歪了，复盘是哪一步错了 |
| [dispatching-parallel-agents](vendor/superpowers/dispatching-parallel-agents/) | 两个以上互不依赖的任务并行丢出去 |
| [executing-plans](vendor/superpowers/executing-plans/) | 自己按计划一步步实现 |
| [finishing-a-development-branch](vendor/superpowers/finishing-a-development-branch/) | 收尾时决定这份工作怎么合进去 |
| [receiving-code-review](vendor/superpowers/receiving-code-review/) | 接评审意见，先判断对不对再改 |
| [requesting-code-review](vendor/superpowers/requesting-code-review/) | 合并前请人过一遍 |
| [subagent-driven-development](vendor/superpowers/subagent-driven-development/) | 拆任务给子 agent 并行做 |
| [systematic-debugging](vendor/superpowers/systematic-debugging/) | 先提假设再动手改 |
| [test-driven-development](vendor/superpowers/test-driven-development/) | 写实现之前先写测试 |
| [using-git-worktrees](vendor/superpowers/using-git-worktrees/) | 给功能开一个隔离的工作区 |
| [using-superpowers](vendor/superpowers/using-superpowers/) | 开局先找 skill 再开口 |
| [verification-before-completion](vendor/superpowers/verification-before-completion/) | 说"做完了"之前先跑验证命令 |
| [writing-plans](vendor/superpowers/writing-plans/) | 多步任务先写计划再碰代码 |
| [writing-skills](vendor/superpowers/writing-skills/) | 写和改 skill 本身的标准 |

### 元技能（vercel）

| skill | 一句话 |
|---|---|
| [find-skills](vendor/find-skills/) | 描述任务，去生态里找现成的 skill 装上 |

## 三条共同规矩

1. **先测量再判断。** 不给「感觉有点挤」「优化一下性能」这种话，给 8px→12px、4.1:1→6.2:1、42 个用例里 3 个失败。
2. **能跑的东西才叫产出。** 有脚本就真跑脚本，不把命令写在 markdown 里让人自己试。
3. **说清为什么，不堆清单。** 每条规则后面跟一句它防的是什么错误——这样下一个人知道什么时候可以破例。

## 规范怎么保证

`tools/validate_skills.py` 用 stdlib 实现了规范里的硬约束，CI 每次都跑：

```bash
python3 tools/validate_skills.py
python3 -m unittest discover -s tests -t .
```

检查的是：`SKILL.md` 存在且是 UTF-8、frontmatter 被 `---` 包住、`name` 与目录同名且是 kebab-case（≤64，`claude` 保留）、`description` 1–1024 且必须写出「什么时候用」、`compatibility` ≤500、`metadata` 的值必须是字符串（`version: 1` 会被 YAML 吃成整数，报错提醒加引号）、只允许规范里的六个字段、**正文里提到的 `references/` `scripts/` 路径必须真的存在**。

最后一条是自己加的：skill 最常见的腐烂方式不是写错，是改名之后正文还指着旧路径，agent 照着读结果读到空气。

## 加一条新 skill

```bash
mkdir -p skills/my-skill
$EDITOR skills/my-skill/SKILL.md
python3 tools/validate_skills.py
```

`description` 是唯一会被提前加载的部分，所以它得同时回答「干什么」和「什么时候用」，并且用用户真会说的话当触发词。正文每多一行，就多占一次上下文——细节放 `references/`，正文只留判断和流程。

## License

MIT（`vendor/` 下各目录保留上游自己的许可）
