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
- **12:47 contrast.py 认识 oklch()/rgb()/hsl() 了** — 起因是拿真实世界的 token 表实测：抓了 Tailwind v4 的 `theme.css`（510 行），颜色全是 `--color-red-500: oklch(63.7% 0.237 25.331)` 这种写法。拿一份 shadcn 风格的 oklch 表跑脚本，得到 `no --custom-property: #hex declarations found`，exit 1——一份完全合法的现代 token 表被判成「没有颜色」。只认 hex 的检查器在 2026 年等于没用。
  修法：`parse_color()` 统一入口，函数色先剥 alpha 段（`/ 50%` 丢弃，对比度对不透明底测）再拆参数；`rgb()` 支持数字/百分制/逗号；`hsl()` 走六分位公式；`oklch()` 用 Ottosson 的 OKLab→线性 sRGB 矩阵 + gamma 编码，纯 stdlib 四十行。
  验证方式比「看起来对」硬：拿两个有官方 sRGB 对照值的 oklch 做锚点——Tailwind red-500 算出 `(251,44,54)` 正是文档里的 `#fb2c36`，shadcn 的 `oklch(0.145 0 0)` 算出 `(10,10,10)` 正是 `#0a0a0a`；再加灰轴自洽（C=0 时 luminance 必须 = L³）。
  顺带把报错改诚实：表里有颜色但命名不符合约定时（比如 `--background/--foreground`），exit 2 并列出见到的角色名让用户加 `--pair`，而不是装作没看见。9 个新用例，全套 61 个通过。
- **13:47 双作用域表不再静默混读，shadcn 的 `-foreground` 约定成为一等公民** — 继续拿真实文件测：shadcn 仓库的 `apps/v4/app/globals.css`（462 行）。两个新发现，都来自证据：
  1. 真实表是 `:root`（L99）+ `.dark`（L143）**双作用域同名变量**。旧的扁平 last-wins 读法会静默只取 `.dark`——浅色主题从来没被检查过；更糟的场景是 `.dark` 只覆盖部分变量时会把浅色 fg 配深色 bg，算出垃圾比值还报 PASS。现在 `read_tokens()` 先按块解析，发现同名 token 出现在多个作用域就拒绝（列出重名清单，提示 `--block :root / .dark`），`--block` 用选择器子串匹配。fixture 故意让两个作用域一个 PASS 一个 FAIL，测试证明作用域选择真的改变结论。
  2. shadcn 全网最被抄的命名是 `--card-foreground` / `--primary-foreground`，而我们只认自家的 `-contrast` → 真实表零自动配对。现在 `-foreground` 后缀与 `foreground on background` 都自动派生，跑真实 shadcn 表直接得到 13–14 对检查。
  顺带修掉一个假阳性：`.dark` 的 border 是 `oklch(1 0 0 / 10%)`，旧版把 alpha 丢弃当纯白算，报 19.8:1 PASS——渲染出来其实是 1.24:1。现在 `ratio()` 把 fg 的 alpha 按成对 bg 合成（`rgba(...,0.1)` 逗号旧语法这个 alpha 在第 4 参数、不在 `/` 段，是测试抓出来的）。
  **在 shadcn 真实值上的发现**：浅色 `muted-foreground` 4.35:1（差 0.15）、浅色 `destructive-foreground` 4.37:1、深色 `destructive-foreground on destructive` **1.66:1**（红底红字）。测量代替猜测的意义就在这。
  验证：10 个新用例（拒绝混读、--block 各作用域、作用域改变结论、无匹配报错、-foreground 派生、混合约定共存、三种 alpha 语法合成、parse_color 锚点不变），全套 71 个通过；validator 干净。

## 2026-11-01

- **13:40 sloplint：把「不要 AI 味」变成能跑的检查** — 昨天调研发现 hallmark（周涨 11,766 星）有个 `sloplint.mjs`，把设计规则做成对生成代码的扫描。我们 SKILL.md 的 ship checklist 里「No default AI tells」那条一直是靠模型自觉——同一批规则，人家能跑，我们只能读。补上。
  做了什么：`skills/frontend-design/scripts/sloplint.py`（stdlib），扫 HTML/CSS，两种严重级：
  - FAIL（exit 1，机械性损坏）：`transition: all`、动画动画 layout 几何（width/height/top/left/margin/padding）、`outline: none` 且全文件无 `:focus-visible`、`100vh`、html/body 上的 `overflow-x: hidden`（掩盖真实溢出）、`<img>` 缺 `alt`。
  - TELL（exit 0，可留痕豁免）：token 块外出现字面颜色、`text-transform: uppercase` + 字距（eyebrow tell）。
  分级的理由：FAIL 是「确定坏了」，TELL 是「模型的默认手感」，后者需要理由才能豁免，但不能一刀切拦死。
  细节打磨：token 声明（`--bg: #fff`）里的字面颜色豁免——否则每个主题文件都报；`html/body` 不再算主题块（拿证据说话：它们该用 var()）；`--strict` 让 TELL 也算失败，给已经有 token 层的项目用。
  验证：新 fixture `tests/fixtures/slop-good.html`（0 findings）与 `slop-bad.html`（6 FAIL + 2 TELL），16 个新用例（每条规则、退出码、strict、quiet、缺文件、编译），全套 87 个通过；validator 干净；CI 加一步「好例通过 + 坏例必须失败」。
  文档：`references/slop-tells.md` 写清规则表、严重级、豁免协议（留痕+理由）、以及脚本故意不查的东西（设计是否独特、状态缺失、emoji 当图标——这些要人看）；SKILL.md ship checklist 改成「跑 sloplint 且 tells 已留痕豁免」两行，正文没超预算。
- **18:40 sloplint 拿真实文件验精度，修两处** — 写一版只是开始，拿 8 个真实 CSS 跑一遍才知道规则准不准（自己的 agentledger 前端、workspace 里的博客样式、DSH 侧边栏插件的 6 个 CSS module，共约 2000 行）。结果：
  1. **误报**：博客 `.project { transition: border-left-color .2s, background .2s }` 被报「动画 layout 几何」。原因是子串匹配：`border-left-color` 里含 `left`。改成按逗号切出每个 transition 目标、跳过时间值、对**完整属性名**做 fullmatch（`border-left-color` 是绘制属性，不重排粉）。补回归用例。
  2. **判太狠**：agentledger 的 `input { outline: none }` 配的是 `:focus { border-color: accent }`——键盘用户其实看得见焦点，只是鼠标点击也会闪。原来一刀切 FAIL 不对。改成三态：有 `:focus-visible` 通过；只有 `:focus` 算 TELL（focus-not-visible）；两者都没有才 FAIL。
  另一条值得记：插件里 4 处 `uppercase + letter-spacing` 被判 eyebrow，那是表格表头/徽章的正常用法——说明这条只能算 TELL 不能算 FAIL，分级是对的。
  验证：89 个用例通过（+2 回归），validator 干净，两个真实文件复测：博客 0 findings、agentledger 10 个 TELL 0 FAIL。

## 2026-11-02

- **08:12 断网日补记** — 11-01 的 5 次迭代在 18:50 后全卡在本地（GitHub `SSL_ERROR_SYSCALL` 四小时，重试 10+ 次全失败）。今早 08:00 线路恢复，`683a857..303a4ab` 一次推完，CI 绿。教训：推送失败不是「工作没做」，但**恢复后第一件事必须是推**，所以把 `pending_push` 写进了 `state/current_week.json`，让下一个窗口先看它再谈迭代。
- **08:20 扫页面却不看页面自己的样式表** — 拿本地两个真实页面跑 sloplint：`blog/index.html` 一条结果都没有，`resume.html` 报了 6 条 literal-color（真的，简历页没 token 块，手写颜色——属于可豁免的 tell）。但 blog 静默不是因为干净：它第 12 行是 `<link rel="stylesheet" href="assets/styles.css">`，设计全在外部 CSS 里，而脚本只读传进来的文件。「lint 这个页面」却漏掉它的样式表，等于对现代站点没有任何用。
  修法：解析 HTML 里的 `<link rel="stylesheet">`，把本地相对路径的 CSS 一起扫（跳过 http(s)、`//`、`data:`——不联网）；按 resolve 后的绝对路径去重，同一份 CSS 被两个页面引用也只报一次。摘要行加了 `(N file(s) scanned)`，不然「干净」到底是没查还是没问题分不清——这点是这次翻出来的第二个教训：**工具必须说清楚它查了什么**。
  验证：新 fixture `slop-linked.html` + `slop-linked.css`（`transition: all` + 字面 `#ffffff`），跑 HTML 会报出 CSS 里的 transition-all 并显示 2 files；远程样式表只算 1 file。99 个测试通过。
- **08:41 1,053 条假阳性教会我一件事：不知道就不要报** — 把 sloplint 拿去跑本机 36 个真实 CSS 文件（DSH 插件的 client 样式、自己的 blog/admin 样式），`dangling-var` 一口气报 **1,053 条 FAIL**，全是 `--dsw-*` 这类宿主运行时注入的 token——扫描集里当然没有声明，因为它们根本不在文件里。
  之前「只要本次扫描出现过 token 声明才检查」的守门条件形同虚设：集合里有一个文件声明了 token，其余所有文件的外来 token 就全部中枪。这条规则当时就不可用。
  改法：undeclared 只在一处构成**证据**时才报——这个名字与某个已声明 token 的编辑距离 ≤2，也就是拼错了。`--accent-constrast` 会被抓（并告诉你它像 `--accent-contrast`），`--dsw-alias-label-tertiary` 不会——宿主注入和拼错在静态分析里几乎只能靠这个区分。
  第二次测量：1053 → 1，剩下那条是插件 CSS **注释里**写着 `var(--dsw-font-markdown-*)`（作者在解释 token 用法）。于是加了 CSS 注释剥离（保留换行数，行号不会飘），36 个文件 → **0 条**。
  这条的教训比代码值钱：**假阳性率高的检查等于没有检查**，而唯一的修法是真数据。101 测试通过。
- **12:48 真实 Bootstrap 的调色板一半是算出来的** — 拿 Bootstrap 当前 main 的 `dist/css/bootstrap.css`（496 KB）测 contrast.py，第一层就卡住：83 处 `light-dark(...)`，加上 `color-mix(in oklch, var(--bs-white) 94%, oklch(60% 0.24 240deg))` 这种两层间接——脚本只认字面量，351 个 token 里能读的只有零头。真实世界现在就是这么写颜色的。
  补了三样：`var()` 链解析（最多四层，环和缺引用会被点名为「未检查」而不是算通过）；`color-mix()` 按 OKLab 矩阵做真插值（oklch 走色相弧，srgb 走线性插值，百分比按 CSS 规则归一）；`light-dark(a, b)` 拆成两套主题各自检查。顺带发现 `240deg` 这种带单位色相以前直接抛 ValueError——真实文件里很常见。
  一个必须诚实的地方：`light-dark` 只有一个 token 有时会让整套表被拆成两套，而不是 light/dark 有差异的行打印两遍会凭空造出重复条目。现在只有两边真的不同才加 `light:`/`dark:` 前缀。
  还撞出两个 bug：① `_scopes` 用「选择器的最后一个词」当块名，` :root,\n[data-bs-theme=light] {` 这种多选择器块会被命名成最后一个，`--block :root` 直接找不到；② 注释里的 `:root light + .dark` 会被 BLOCK_RE 当成选择器，`--block light` 反而匹配到注释文字。前者保留完整选择器，后者先剥注释（保留换行，行号不飘）。
  最后是**推断的边界**：一开始我把 `--<role>-fg` 和 `--<role>-bg` 配对，Bootstrap 上报了 36 条 FAIL。去看用法才发现 `.fg-warning { color: var(--bs-warning-fg) }`——`-fg` 是页面上的前景色，不是 `-bg` 上的字。这个配对是我编的，36 条全是假的，于是砍掉，只保留语义明确的 `--<role>-contrast` on `--<role>-bg`。剩下的 3 条是真的：白字在 blue-500 上 3.56:1、green-500 上 2.82:1、red-500 上 4.42:1，都低于 4.5——`--bs-primary-contrast` 确实用在选中项文字上（`--bs-datepicker-day-selected-color`）。
  110 测试通过（+9）。
- **13:52 `--all-blocks` 在真实的 Bootstrap 上是不可读的** — 一条命令跑 Bootstrap 的 496 KB 表，输出 260 行，其中 259 行是「这个 block 有颜色但没有可检查的配对」，真正的结果淹没在里面。更要命的是「note: 832 token(s) not checked」——那 832 个里绝大多数是 box-shadow、字体栈、缓动函数，根本不是颜色。
  三个修法，每个都对着真实数字验证：① 每个 block 一行 → 汇总成一行（Bootstrap 249 个空 block，现在一行说完）；② 未解析 token 只报「像颜色」的（名字含 color/bg/fg/border/contrast…，或值本身能解析成颜色；shadow/gradient/font/spacing 一律排除）——832 → 47，剩下的 47 条看一眼源码确实是真读不了：`color-mix(in srgb, var(--bs-table-color) var(--bs-table-striped-bg-factor), transparent)`，百分比是变量还混了 transparent，报「未检查」才是诚实的；③ 最关键的，`--all-blocks` 之前对每个 block **独立解析 var()**，而 utility block 的 `var(--brand)` 指向 `:root` 里的声明——所以全被判成读不了。改成「解析用全表合并的 token，派生配对只用本 block」，这才是 CSS 层叠的实际语义。47 条里剩下的都是真·无解，不是工具蠢。
  顺带修掉选择器污染：`@charset "UTF-8"; :root` 这种把 at-rule 语句当成选择器一部分的问题（截到最后一个分号之后），不然 `--block :root` 永远匹配不上。
  260 行 → 20 行，3 条真失败仍然在。115 测试通过（+5）。
- **18:41 安装脚本看不见 vendor 里那 61 个 skill** — `./install.sh --list` 只列出一个 `frontend-design`，可仓库里明明抄了 61 个别人的 skill（`vendor/` 下），README 也整节介绍它们。原因很蠢：发现逻辑是 `for d in "$SKILLS_SRC"/*/`，只 glob 一层自己的 skill 目录。
  修的时候发现 vendor 的目录深度还不统一（`vendor/x/SKILL.md`、`vendor/lib/name/SKILL.md`、`vendor/lib/group/name/SKILL.md` 三种），所以改成 `find -name SKILL.md` 全量走。61 个里有两份同名 `test-driven-development`（superpowers 和 agent-skills 各一份），同名以自己写的优先、其次按路径排序取第一个，`--list` 两边都列。
  另一个设计决定：默认**只装自己写的**，`--vendor` 才把 61 个一起装。默认给别人的机器塞 61 个软链太粗暴了；`--list` 反过来总是全列（列表说的是「仓库里有什么」，安装说的是「装什么」）。
  `--remove` 顺带静音：原来会打印 60 行「skip X: not installed」，卸载只该说真卸掉了什么。
  自测时事故：跑 `./install.sh` 验证默认行为时忘了 `--target`，真的把 frontend-design 软链进了 `~/.claude/skills`（并创建了 `~/.claude`）。已删掉链接和空目录恢复原状。教训：测安装脚本一律带 `--target /tmp/...`，这一次记住了。
  CI 加一步「vendor 路径」：`--list` 必须同时出现自己的和 vendor 的、`--vendor --only common-accessibility` 装完是 1 个软链且指向嵌套目录——一层 glob 的写法会在这步直接失败。

## 2026-11-03

- **21:40 viewport-vh 只认字面量，`calc(100vh - …)` 全漏** — 收口窗口补做（今天 0 次迭代，旧会话损坏导致白天四个窗口都没跑成）。先拿真实语料测：`/Users/xin/Documents/Codex/2026-05-03/new-chat/src/app/globals.css` 有 5 处 100vh，其中 3 处是裸的、1 处 `min-height: 100vh`、还有 1 处是 **`max-height: calc(100vh - 100px)`**。旧规则 `\b(?:min-)?height\s*:\s*100vh\b` 一条都抓不到 calc 里的那种，而带 sticky header 的页面恰恰都这么写——也就是说这条 FAIL 在真实项目上基本是瞎的。
  改法：不再对整条规则体做一次正则，而是先把 `height / min-height / max-height` 这些声明切出来，再看值里有没有 `100vh`（calc/max()/min() 里出现同样算）。顺带把 `max-height` 缺口补上。token 声明（`--hero-height: 100vh`）不报：单位放 token 里、改一次全站生效，是正确的写法。
  验证：真实文件复测 4 条 → 5 条（新增的正是 line 254 那条 calc）；新增 2 个用例（calc 报、token 不报），27 个 sloplint 用例全过（+2）。
- **21:44 页面少了 viewport，手机上是整页缩小版** — 扫了 31 个真实 HTML，只有一个整页没有 `<meta name="viewport">`：`/Users/xin/Documents/deepseek-harness/default-workspace/resume-md/.build/resume.html`（A4 打印构建，属于可豁免——但它恰好证明这条规则只是地板，豁免写在记录里一行就完事）。而 sloplint 此前对「完整页面没有 viewport」一个字都不会说，这是响应式地板上最大的一个洞：AI 生成的页面常常从 `<body>` 开始写，`<head>` 里除了 `<title>` 什么都没有。
  实现上有个必须守住的分界：**片段/模板不是页面**，它们不拥有 `<head>`，对它们要求 meta 等于把每个服务端 include 都判失败。所以只在 `< !doctype html` 或 `<html` 出现时才查；`name=viewport` 不带引号也认。
  验证：31 个真实页面里命中 1 个（上面那个），新增 3 个用例（整页缺 meta 报、无引号 meta 通过、片段不报），30 个 sloplint 用例全过（+3）；两个 fixture 页面补上了 meta 保持「好例就是对的写法」。
- **21:50 把「禁止缩放」写进 viewport 的页面，低视力用户直接读不了** — 本机 31 个真实页面没有命中（本地语料里都是 `width=device-width, initial-scale=1` 这种正常写法），所以这条按标准立：WCAG 1.4.4 要求页面不损失内容地放大到 200%，而 `user-scalable=no` / `maximum-scale=1` 正是 iOS 上按住这个开关的写法（Android Chrome 会忽略 user-scalable，但 iOS 不会）。生成式页面经常顺手带上这两个参数来「防止布局缩放坏掉」——那是拿可访问性换自己的方便。
  分级取 FAIL 而不是 TELL：这不是口味问题，是有人真的读不了。阈值取 5（iOS 的默认上限），写 `maximum-scale=5` 等于没写，不算违规。
  验证：新增 2 个用例（两种写法都报，`maximum-scale=5` 不报），32 个 sloplint 用例全过。没拿真实文件做证据，这一点写清楚，好过假装有。
- **21:58 `no-focus-replacement` 的措辞和实现不一致：说「anywhere」，实际只看单个文件** — 拿两个真实风格的拆分复现：`reset.css` 写 `* { outline: none }`，`focus.css` 写 `:focus-visible { outline: 2px solid }`。两个一起扫，reset 照样 FAIL——可页面上明明有焦点了。原因：`scan()` 里每个文件各自算 `focus_kind`，于是「本文件没写 :focus-visible」被当成「整个项目没写」。
  改法：把判断提到 main()，所有入参文件（含沿着 `<link>` 找到的）先读进来合成一份 CSS 再算 `focus_kind`，`scan()` 只负责用这个全局结论判每一条 `outline: none`。单独扫 reset 时仍然 FAIL（那时它确实没有替代焦点），这才是正确语义。
  顺带的结构收益：每个文件只读一次，之前 scan() 读一遍、后面统计 var() 又读一遍。
  验证：新增 1 个用例（两文件分拆 → 通过；单独 reset → 失败），122 个测试全过（sloplint 34 个）。
- **22:03 `--strict --quiet` 退出 1 却不打印任何发现** — 收口最后一条，最小但最丢人：`--quiet` 的本意是「TELL 不影响结果所以别刷屏」，可 `--strict` 下 TELL 就是失败。两个都对，合在一起就是「退出码 1、屏幕空白、摘要说 0 failure」，读起来像 linter 自己坏了。
  改法：`--quiet` 只压 `not strict` 的 TELL；strict 下的摘要多一句「(+N tell(s) promoted by --strict)」，让 0 failure 的摘要和退出码 1 不再自相矛盾。
  验证：新增 1 个用例（strict+quiet 必须打印 literal-color 且带 promoted 字样），123 个测试全过；`--quiet` 单独用仍然隐藏，行为没变。
- **08:07 根相对的 `<link>` 被静默跳过，摘要却写「clean」** — 拿 `next export` 出来的真页面（/Users/xin/Documents/Codex/2026-05-03/new-chat/out/index.html）试：它整站样式都在 `/_next/static/css/faf81e09ecf69405.css`，sloplint 输出 `clean: 0 tell(s) wairable, 0 failures (1 file(s) scanned)`——一句都没提那份 CSS 没被打开。这正是这轮反复撞到的病：工具不说清自己查了什么，就把「没查」卖成「没问题」。
  改法：`linked_stylesheets()` 改成返回 (可读的, 跳过的)；跳过 = 远程 / 根相对 → 无法从磁盘解析 / 文件不存在。main() 汇总后在摘要前打一行 `note: N linked stylesheet(s) not scanned (remote, root-relative, or missing): …`，最多列 4 条加省略。
  验证：新增 2 个用例（`/_next/…` 与 CDN 的 href 必须出现在 note 里，且原文的 href 不丢），126 个测试全过；本地可读的 <link> 仍然照常跟进扫描，老行为不变。
- **12:41 指向不存在文件的相对 `<link>` 只被当成「跳过的」** — 早上那条 note 把三种原因写在一行里：远程、根相对、文件不存在。前两种确实没法从磁盘解析，第三种不一样——`href="assets/styles.css"` 而文件被改名/拼错时，页面就是裸着上线的，而 sloplint 只打一行 note、退出 0。实测：造一个 `assets/styles.css` 不存在的页面，原来 `exit 0` + note。
  改法：`linked_stylesheets()` 返回 (可读, [(行号, href, 原因)])，原因分 remote / root-relative / missing；missing 变成 FAIL `missing-stylesheet`（带行号），其余两种仍进 note。
  验证：新增 1 个用例（缺文件的相对 href → exit 1、输出 missing-stylesheet 与路径），127 个测试全过；根相对和 CDN 的两个老用例仍是 exit 0 + note，没被误伤。
