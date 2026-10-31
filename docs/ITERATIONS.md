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

## 2026-10-31 · 第 2 天 · 把 CI 从红救回来

- **08:05 发现 CI 连红三次** — 昨晚 01:27–01:32 那次大改（`skills/` 换成单个 frontend-design、新增 `vendor/` 四套上游库）之后，CI 一直是 failure，没人看。
  原文：`python3: can't open file '.../skills/design-tokens/scripts/gen_tokens.py': [Errno 2] No such file or directory` → `Process completed with exit code 2`。
  为什么没发现：本地只跑了 validator 和 unittest，那两个确实还是绿的；红的是 workflow 里写死路径的第三步。**在本地跑「我改的那部分」，不等于跑了一遍 CI。**
- **08:10 校验器加 vendor 模式** — `vendor/**/SKILL.md` 现在也扫（递归，因为上游按语言/框架分了子目录）。规则分两档：结构性错误（name 缺失/与目录不符、description 缺失、frontmatter 解析失败、正文为空）仍然失败，风格问题（缺 `Use when`、正文过长、缺 metadata.version）降级为警告——那是别人写的东西，要修得回上游修。
  结果：61 个 vendor skill，0 个结构错误，50 条风格警告。其中 27 条是正文超过 220 行（上游把全部细节塞在 SKILL.md 里），20 条拿不到 version。
- **08:14 50 条警告压成一行** — 一次打印 50 行警告的检查等于没有检查，人只会往下滚。现在按类别归并成 `vendor: 50 convention warning(s) — 27 long body, 20 no metadata.version, 2 no trigger phrase, 1 dangling reference`，`--vendor-detail` 才展开。
- **08:16 修掉一个假阳性** — 代码块里的路径是模板不是链接（`scripts/tool.sh` 这种讲解例子），扫描前先剥掉 ` ``` ` 块。之前 upstream `writing-skills` 就因为这个被误报。
- **08:18 修掉一个真漏洞** — 原来「缺 metadata.version」的警告写在 `if meta is not None:` 里面，所以**整块 metadata 都没写**的时候反而不警告。写测试的时候撞出来的（断言 `1 no metadata.version` 却拿到空字符串）。现在 `meta` 不存在也警告。
- **08:20 CI 重写** — 删掉指向已删除脚本的步骤；installer 那步改成「软链装 → `test -L` → remove → `test ! -e` → 复制装 → `test -f`」。原来只测了 `--copy`，而 `--remove` 的语义（只删自己建的软链）根本没被覆盖。
- **08:35 加对比度脚本** — `skills/frontend-design/scripts/contrast.py`（stdlib）。
  为什么：SKILL.md 原来写「Check contrast before shipping; approximate ratio = (L1+0.05)/(L2+0.05)」——把算术交给模型是最不该交的东西，而这条正好是 palette 最常见的翻车点。现在改成「跑脚本，别心算」，并让命名约定变成测试：每个 `--<role>-contrast` 自动对 `--<role>` 检查，`text`/`muted` 对 `bg`，`border` 对 `bg` 走 3:1。
  验证：`--css tests/fixtures/tokens-good.css` → `all pairs pass` exit 0；`tokens-bad.css` → 2 条失败 exit 1。16 个用例钉住参考值（黑白 21:1、同色 1:1、对称性、3 位 hex、alpha 截断）与退出码，CI 里也加了一步「好例通过 + 坏例必须失败」（用 `!` 前置）。
  顺带发现：我昨天「good」示例里的 `--border: #c9ccd4` 对白底只有 **1.61:1**，远低于 UI 边界要求的 3:1。换成 `#7b8494` 后 3.77:1。这就是写脚本的意义——肉眼完全看不出这条已经挂了。
- **08:52 校验器开始编译脚本** — `scripts/` 下的 `.py` / `.sh` 现在会被 compile 一遍，检查 shebang 是否与语言一致。
  为什么：一个跑不起来的脚本比没有脚本更坏——agent 会先怀疑自己的命令，而不是怀疑脚本。之前 `contrast.py` 就算写坏了 CI 也绿。
  填之前先撞了一次：校验器把 `scripts/__pycache__/contrast.cpython-314.pyc` 也读了，报 `is not UTF-8`。修法是只认 `.py/.sh/.bash/.zsh`、跳过 `__pycache__` 和隐藏文件——顺带说明为什么仓库里只放源码，不放产物。
  验证：6 个新用例（语法错误、缺 shebang、shell 脚本写成 python shebang、正常脚本、pyc 与 pycache 被忽略、vendor 模式下降级为警告），全套 52 个用例通过。
