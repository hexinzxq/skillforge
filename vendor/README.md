# vendor — 收录别人的 skill

这里的 skill 不是我写的，是从 GitHub 上挑的、真在生产里用的那几套，原样抄下来（保留各自的 LICENSE），方便对照和借鉴。

补进来是因为：自己写 skill 最大的风险是「闭门造车」——写出一堆看着有道理、实际没人这么干的东西。把工业界的版本放在旁边，就知道分寸在哪。

| 目录 | 来源 | 许可 | 收了多少 | 值什么 |
|---|---|---|---|---|
| `superpowers/` | [obra/superpowers](https://github.com/obra/superpowers) | MIT (c) 2025 Jesse Vincent | 15 个 | 把「先想清楚再动手」写成流程：brainstorming、writing-plans、systematic-debugging、verification-before-completion、test-driven-development |
| `agent-skills/` | [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills) | MIT (c) 2025 Addy Osmani | 25 个 | Google 工程师的生产级工程技能：code-review-and-quality、debugging-and-error-recovery、security-and-hardening、performance-optimization、frontend-ui-engineering |
| `find-skills/` | [vercel-labs/skills](https://github.com/vercel-labs/skills) | MIT (c) 2026 Vercel, Inc. | 1 个 | 元技能：你描述任务，它去生态里找现成的 skill 装上，而不是自己瞎造 |
| `agent-skills-standard/` | [HoangNguyen0403/agent-skills-standard](https://github.com/HoangNguyen0403/agent-skills-standard) | MIT (c) 2026 Hoang Nguyen | 20 个（全量 299） | 语言和框架级规范：TS、React、Next.js 各挑核心几条，另加 10 条通用工程规范；值得学的是它的分层路由加载 |

## 用法

```bash
# 挑一个装进项目
cp -R vendor/agent-skills/code-review-and-quality ~/code/app/.claude/skills/

# 或者软链，跟着上游更新
ln -s "$(pwd)/vendor/superpowers/brainstorming" ~/.claude/skills/brainstorming
```

`skills/` 下的是自己写的，`vendor/` 下的是抄来的——别混，改的时候也别改 vendor 里的，要改就复制到 `skills/` 再改。

## 许可

每个目录里都保留了上游的 LICENSE。再分发或改造时，照原许可走。
