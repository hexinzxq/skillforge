# agent-skills-standard（精选 20 条）

上游：[HoangNguyen0403/agent-skills-standard](https://github.com/HoangNguyen0403/agent-skills-standard)（MIT，全量 299 条，覆盖 20+ 语言和框架）。

整包 73MB、299 条，全抄进来只会让仓库变重、让 agent 迷路。这里只留**一个前端工程师日常真会碰到**的 20 条，按「通用 → 语言 → 框架」排。

## 收录清单

| 组 | skill | 管什么 |
|---|---|---|
| 通用 | `common-best-practices` | 函数长度、守卫子句、命名、早返回 |
| 通用 | `common-code-review` | 评审分档、严重度、可合并判断 |
| 通用 | `common-debugging` | 假设树、最小复现、证据先行 |
| 通用 | `common-error-handling` | 错误分类、包装上下文、别吞异常 |
| 通用 | `common-api-design` | 状态码、分页、幂等、OpenAPI 一致性 |
| 通用 | `common-security-standards` | 鉴权、输入校验、密钥处理 |
| 通用 | `common-performance-engineering` | 异步模式、N+1、测量先于优化 |
| 通用 | `common-accessibility` | 语义标签、焦点管理、对比度 |
| 通用 | `common-documentation` | ADR、README、注释该写什么 |
| 通用 | `common-git-collaboration` | 分支、提交、rebase 与冲突处理 |
| TS | `typescript-language` | strict、`unknown` 优于 `any`、satisfies |
| TS | `typescript-best-practices` | 类型建模、泛型边界、模块组织 |
| React | `react-component-patterns` | 组件拆分、组合优于继承 |
| React | `react-hooks` | 依赖数组、闭包陷阱、自定义 hook 边界 |
| React | `react-performance` | 重渲染定位、memo、拆 state |
| React | `react-testing` | 测行为不测实现、查询优先级 |
| Next.js | `nextjs-app-router` | 路由段、layout、loading/error |
| Next.js | `nextjs-server-components` | 服务/客户端边界、序列化限制 |
| Next.js | `nextjs-data-fetching` | fetch 缓存、并行取数、瀑布流 |
| Next.js | `nextjs-optimization` | 图片、字体、bundle 拆分 |

## 它最值得学的是加载方式

不是某一条规则写得有多细，而是**分层路由**：

```
AGENTS.md（约 20 行路由）
  → 正在改 *.ts？读 typescript/_INDEX.md
    → _INDEX.md 里是「文件匹配 / 关键词匹配」的命中表
      → 只读命中的那条 SKILL.md（约 500 token）
```

改一个 `.ts` 文件时只加载 6 条相关 skill，而不是 27 条。全量塞 prompt 是 5000+ token，而且模型会「记混」。

自己写 skill 时值得照抄这个结构：**索引在前、正文按需**。

## 用

```bash
# 单独拷进项目
cp -R vendor/agent-skills-standard/common/common-code-review ~/code/app/.claude/skills/

# 或者整套同步上游（推荐，能跟着更新）
npx agent-skills-standard@latest init
npx agent-skills-standard@latest sync
```

上游的 `ags` CLI 还带校验和锁文件（`.skills-lock.json`），能查出 skill 文件被改过或有缺失。

## 许可

MIT，见本目录 `LICENSE`。
