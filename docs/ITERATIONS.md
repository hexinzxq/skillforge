# 迭代记录

每次真实改动一条：时间 · 改了什么 · 为什么 · 怎么验证的。只记能复盘的，不记「优化了一下体验」。

## 2026-10-30 · 第 1 天 · 立项

- **22:40 立仓** — 从「重做一个市面 AI 产品」改成「攒自己的 skill 库」。原因：调研里 41 条候选，榜首全是 agent skills 包（claude-seo、karpathy-skills、impeccable），说明这类东西正在成为真实需求；而且 skill 有明确的规范边界（frontmatter 六个字段、progressive disclosure），**能靠校验器保证质量**，比再做一个 CRUD 应用更适合每天 5 次小步迭代。
- **22:44 定结构** — `skills/<name>/SKILL.md` + `references/` + `scripts/`，没有构建链、没有依赖。原因：skill 是要被 agent 反复读的，越少工具链越不容易腐烂。
- **22:45 写 ui-critique** — 五镜头（层级 / 间距节奏 / 对比度 / 密度 / 状态覆盖）+ 一张带数值的问题表。
  为什么这么写：市面上的 UI 评审 skill 大多输出「建议增加留白」这种没法执行也没法反驳的话。约束成「每行必须有实测值和替换值」，agent 就没法糊弄。
  附带 `scripts/contrast.py`（WCAG 比值，stdlib）：对比度是最容易靠眼睛骗自己的那一项。
- **22:46 写 design-tokens** — OKLCH 生成器 + 语义角色命名表。
  为什么是 OKLCH 不是 HSL：HSL 调亮度会偏色，一条 ramp 走下来色相飘；OKLCH 保持感知色相，色度到色域边界时二分收敛。生成器同时输出 `tokens.css` / `tokens.json` 并**自己检查对比度对**，不过 4.5:1 就 exit 1——这样 CI 能拦。
  踩坑：第一版 `border-strong` 用 L=0.80，对 surface-1 只有 1.69:1，UI 边框要求 ≥3:1。改成 0.62（亮）/ 0.56（暗）后 3.27 / 3.77。这条错误本身留在了提交历史里，是有意的。
- **22:47 写 commit-craft** — 先跑 `scripts/commit_context.sh` 拿「分支 + 最近 15 条 subject + diffstat + 小 diff」，不读整个文件。原因：写 commit 消息最常见的浪费是把整个仓库读一遍。
- **22:48 写 debug-probe** — 假设树按先验排序（最近改动 > 输入 > 环境 > 残留状态 > 并发 > 上游 bug），一个假设一个探针，失败也要记。附 `references/probe-patterns.md` 探针目录。
- **22:49 写 test-gap** — 先列行为清单再跑覆盖率，每个新测试必须能说出「如果代码错成 X 它会失败」。
- **22:50 校验器** — `tools/validate_skills.py`，stdlib 手写 YAML 子集解析。规范里六条硬约束全覆盖，另外加了一条自家规矩：**正文里提到的 `references/` `scripts/` 路径必须存在**。理由：skill 腐烂的方式几乎都是路径漂移，agent 读到空气也不会报错。
  踩坑：`metadata.version: 1` 在真 YAML 里是整数，规范要字符串。我给裸数字/布尔值打了个 `Bare(str)` 标记，校验器据此报错提醒加引号；`1.0.0` 有两个点，仍是字符串，不误报。19 个用例覆盖这些边界。
- **22:51 安装器** — `install.sh`：默认软链（改了仓库即生效），`--project` / `--only` / `--copy` / `--remove` / `--list` / `--dry-run`。`--remove` 只删自己建的软链，别人的目录不碰。

## 待验证

- 拿两个真实项目跑一遍 `ui-critique`，看它给的数值是不是真能改——评审 skill 最怕的是「说得头头是道但没有一条能落地」。
- `design-tokens` 在彩色品牌（黄、绿）下的 ramp 是否还成体系，只测了 5 个色。
- `test-gap` 的「说出它防哪个 bug」这一步，在真实仓库上会不会变成凑字数。
