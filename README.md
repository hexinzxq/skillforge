# skillforge

给自己攒的一套 agent skill，遵循 [Agent Skills 规范](https://agentskills.io/specification)：一个目录一个 skill，`SKILL.md` 带 YAML frontmatter，支撑文件按需加载。

不是「教程合集」。每条 skill 的目标是：把 agent 从「看起来答得像样」推到「给出的东西能直接落地」——
每个结论都带数值、每条命令都能跑、每个测试都能说出它防的是哪个 bug。

## 装

```bash
git clone https://github.com/hexinzxq/skillforge.git
cd skillforge

./install.sh                          # 软链到 ~/.claude/skills
./install.sh --project ~/code/app     # 装进某个项目的 .claude/skills
./install.sh --only ui-critique       # 只装一个
./install.sh --copy                   # 复制而不是软链
./install.sh --list                   # 看这仓库里有什么
./install.sh --remove                 # 卸掉（只删自己建的软链）
```

软链是默认的：改了仓库里的文件，agent 下次读到的就是新版。

## 有什么

### 前端界面

| skill | 什么时候用 | 产出 |
|---|---|---|
| [`ui-critique`](skills/ui-critique/SKILL.md) | 丢一张截图 / 一个组件，问「这样好看吗」「为什么感觉怪」 | 按严重度排序的问题表，每行带实测值和替换值；附「别动的地方」 |
| [`design-tokens`](skills/design-tokens/SKILL.md) | 开新项目、补暗色、给一个品牌色 | `tokens.css` + `tokens.json`，明暗两套语义 token，附对比度表；低于 4.5:1 直接报错 |

### 日常开发

| skill | 什么时候用 | 产出 |
|---|---|---|
| [`commit-craft`](skills/commit-craft/SKILL.md) | 改完了要提交 | 符合仓库既有风格的 commit，正文写「为什么」，必要时拆成多个 commit |
| [`debug-probe`](skills/debug-probe/SKILL.md) | 报错、测试挂了、行为「有点怪」 | 假设树 + 每个假设一个最小探针，证据出来再改代码 |
| [`test-gap`](skills/test-gap/SKILL.md) | 要测试、覆盖率很高但还在漏 bug、刚修完 bug | 缺口表 +「如果代码错成 X 这条测试会失败」的用例，不凑覆盖率数字 |

## 三条共同规矩

1. **先测量再判断。** 不给「感觉有点挤」「优化一下性能」这种话，给 8px→12px、4.1:1→6.2:1、42 个用例里 3 个失败。
2. **能跑的东西才叫产出。** 有脚本就真的跑脚本（`contrast.py`、`gen_tokens.py`、`commit_context.sh`），不把命令写在 markdown 里让用户自己试。
3. **说清为什么，不堆清单。** 每条规则后面跟一句它防的是什么错误——这样下一个人知道什么时候可以破例。

## 规范怎么保证

`tools/validate_skills.py` 用 stdlib 实现了规范里的硬约束，CI 每次都跑：

```bash
python3 tools/validate_skills.py      # 5 skill(s) valid, 0 warning(s)
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

MIT
