# 每日routine

每个日更窗口照这个走。目标不是「今天又有 commit」，是「今天这个 skill 真的更好用了」。

## 0. 定位

```bash
cd /Users/xin/Documents/deepseek-harness/default-workspace/skillforge
git status --short && git log --oneline -5
tail -20 docs/ITERATIONS.md
```

今天的活从下面三类里挑一类，**优先第 1 类**：

1. **实测打磨** —— 拿一个真实项目/真实截图/真实报错跑一遍现有 skill，把「它给的东西没法用」的地方修掉。这类改动最有价值，因为它来自证据不是想象。
2. **新增一条 skill** —— 只有在前一条 skill 都跑顺了、并且能说清「它防的是什么错」时才加。一天最多加一条。
3. **工具链** —— `tools/validate_skills.py` 补检查、`install.sh` 补场景、CI 补一步。

不做：改 README 措辞当迭代、给 SKILL.md 加同义反复的段落、为了凑次数把一个改动拆成五个 commit。

## 1. 写的规矩

- `description` 是唯一提前加载的部分：必须同时有「干什么」和「Use when …」。改它等于改触发率，改完要自己念一遍「用户会这么说吗」。
- 正文只留判断和流程；表格、清单、长例子放 `references/`。正文超过 220 行校验器会警告，那是真的会挤占上下文。
- 每条规则后面跟一句它防的是什么错误（「否则 X 会 Y」）。没有这句的规则是口号，删掉。
- 有可执行的检查就写成脚本，别写成散文。脚本要能被 CI 跑。

## 2. 验证（不通过不提交）

```bash
python3 tools/validate_skills.py
python3 -m unittest discover -s tests -t .
python3 skills/design-tokens/scripts/gen_tokens.py --brand "#3b82f6" --out /tmp/t   # 若改了生成器
bash install.sh --dry-run --target /tmp/sk-check                                     # 若改了安装器
```

改动了 skill 的判断逻辑时，再拿一个真实输入跑一遍，把输出贴进 ITERATIONS.md。

## 3. 记账

在 `docs/ITERATIONS.md` 当天的小节里加一条：时间 · 改了什么 · 为什么这么改 · 怎么验证的。踩坑要写下来（错误信息原文），那是这个文件里唯一别人偷不走的东西。

## 4. 提交

```bash
skills/commit-craft/scripts/commit_context.sh
git add <具体路径>
git commit -F - <<'MSG'
...
MSG
git push origin main    # 失败重试最多 3 次，不改历史
```

## 5. 汇报

三行以内：改了什么 / 为什么 / 验证结果。当天已经 ≥5 次迭代就只做维护，不硬凑。

## 坑

- **路径漂移**：改目录名/文件名后，正文里的 `references/...` 会失效。校验器会拦，但改完记得跑。
- **description 写太长**：超过 1024 直接失败；接近上限时说明塞了实现细节，该挪到正文。
- **`version: 1` 不加引号**：YAML 会当整数，校验器报错。写 `"1"`。
- **软链安装后改了目录名**：`~/.claude/skills` 里留一条断链，`install.sh --remove` 能清。
- **别在 skill 里写死绝对路径**：换机器就废。路径一律相对 skill 目录。
