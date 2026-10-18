<div align="center">

<picture>
  <img alt="drama-studio 短剧工坊——从分场剧本到 15 秒 AI 视频切片的制作全流程" src="assets/pipeline-zh.png" width="100%">
</picture>

# drama-studio · 短剧工坊

**把一段分场剧本，做成可直接投喂 AI 视频生成的 15 秒切片 Prompt 生产包。**

[![Version](https://img.shields.io/badge/version-1.0.0-6D5DF6?style=flat-square&labelColor=1E1B2E)](#)
[![Quality gates](https://img.shields.io/badge/gates-26-8B7CF6?style=flat-square&labelColor=1E1B2E)](#硬约束全部由质量门强制执行)
[![Self-test](https://img.shields.io/badge/selftest-104%20assertions-22C55E?style=flat-square&labelColor=1E1B2E)](#安装为-agent-skill)
[![License](https://img.shields.io/badge/license-MIT-6B7280?style=flat-square&labelColor=1E1B2E)](LICENSE)

[开始这里](#开始这里) · [三个阶段](#为什么是这三个阶段) · [硬约束](#硬约束全部由质量门强制执行) · [一分钟上手](#一分钟上手) · [安装](#安装为-agent-skill)

[English](README.md) · 中文

</div>

Updated: **2026-10-18** · **v1.0.0** · 仓库默认展示为英文（[`README.md`](README.md)）；本文档为中文版，Agent 入口另有 [`SKILL.md`](SKILL.md)（中文）/ [`SKILL.en.md`](SKILL.en.md)（英文），参考文档英文镜像在 [`references/en/`](references/en/)。

三个阶段一条线，每步都有代码质量门把守：

```
分场剧本 ──▶ 资产（角色四视图 / 场景空镜 + @UUID）──▶ 分镜（15s 切片 + 镜头语言 + 连续性链）──▶ AI 成片（固定模板 Prompt + 四门验收）
```

不是提示词合集，是一条有状态、有验收标准、可修复的生产线。不绑定任何平台/API/模型——即梦、Seedance 或其他入口皆可，执行权在用户。

<a id="开始这里"></a>

## 开始这里

| 你是谁 | 先打开 |
|---|---|
| 第一次接触 | 本页 → [一分钟上手](#一分钟上手) → `examples/三打白骨精-*` 整套样例 |
| Agent 集成者 | [`SKILL.md`](SKILL.md)（中文）/ [`SKILL.en.md`](SKILL.en.md)（英文）——三阶段工作流与命令速查 |
| 要改切分规则 | [`references/stage-2-storyboard.md`](references/stage-2-storyboard.md)——六条切分律 + 镜头语言 |
| 要改资产产出 | [`references/stage-1-assets.md`](references/stage-1-assets.md)——人物四视图、场景分层物件 |
| 要改提示词编译 | [`references/stage-3-generation.md`](references/stage-3-generation.md)——模板解剖、四门验收、修复五判决 |
| 要查某道门为什么响 | [`references/quality-gates.md`](references/quality-gates.md)——26 道门总表与病灶文案 |

## 为什么是这三个阶段

| 阶段 | 回答的问题 | 产出 |
|---|---|---|
| 1 资产 | 画面里的人是谁、地方是哪、手里拿的是什么？ | `assets.json`：外貌/服饰提示词 + 分层物件清单 + UUID + 参考图状态 |
| 2 分镜 | 这 15 秒拍什么、谁在画面哪、镜头怎么说话、台词是哪几句？ | `storyboard.json`：切片 + 镜头语言 + 连续性链 |
| 3 成片 | 喂给平台的 Prompt 长什么样、生成出来怎么验、坏了怎么修？ | `slices.md`：可直接复制的切片 Prompt |

<a id="硬约束全部由质量门强制执行"></a>

## 硬约束（全部由质量门强制执行）

- 单切片恰好 **15 秒**；
- 单切片台词 **25-35 汉字**（激烈对峙 ≤40），**逐字**来自剧本，不增不减不改；
- 每切片 **3-5 个有效动作单元**，复杂冲突必须切开；
- 断点只切在：单句台词结束 / 人物入场 / 人物离场 / 重大动作转折 / 情绪停顿；
- **上一片结尾动作 = 下一片起始画面**（`continuity` 门硬查）；
- 每切片一句**镜头语言**（景别层次/机位角度/运镜方式/构图/组接，≤80 字）；
- 链式衔接深度 ≤3，超了从角色/场景母版重新锚定；
- 人物/场景一律 `@UUID` 绑定参考图，文本只写增量；
- 模板头逐字不可改，字段顺序不可动。

<a id="一分钟上手"></a>

## 一分钟上手

```bash
# 1. 解析剧本（严格格式，见 references/script-format.md）
python scripts/drama_studio.py parse-script 项目-script.md --title 项目 --out 项目-scenes.json

# 2. 生成资产骨架，补全后校验（参考图出完/上传后才算数）
python scripts/drama_studio.py seed-assets 项目-scenes.json --out 项目-assets.json
python scripts/drama_studio.py uuid-new 凛生 拓真 开太
python scripts/drama_studio.py validate-assets 项目-assets.json --scenes 项目-scenes.json
# 人物：造型师提示词填 appearance/costume → build-sheets 组装四视图提示词 → 出图上传
python scripts/drama_studio.py build-sheets 项目-assets.json --apply
# 场景：美术指导提示词填 objects 分层清单 → 手写空镜 sheetPrompt（含无可读文字）

# 3. 分镜：按 references/stage-2-storyboard.md 填 slices，校验到全过
python scripts/drama_studio.py seed-storyboard 项目-scenes.json --aspect 9:16 --out 项目-storyboard.json
python scripts/drama_studio.py validate-storyboard 项目-storyboard.json --scenes 项目-scenes.json --assets 项目-assets.json

# 4. 编译切片 Prompt（门不过则拒绝编译）
python scripts/drama_studio.py compile-slices 项目-storyboard.json --assets 项目-assets.json --scenes 项目-scenes.json --out 项目-slices.md
```

`examples/三打白骨精-*` 是一整套跑通的样例（剧本 → 资产 → 14 个切片 → slices.md → 报告），从那儿抄最快。

## 样例切片长这样

```text
真实电影风格。无BGM。无字幕。风格要求真实，镜头切换自然。
人物：@2e14540f-41ca-4feb-ac60-442348dc9fd3是凛生。@e57bf6bd-2fcd-4ca9-9f07-519faf7f8f65是拓真。
场景：@bd657dad-a344-4fe2-99b5-4579e94f6678是理疗室。
景别：中近景。
运镜：推镜。
镜头语言：中近景侧机位缓推，浅景深锁定伤膝与冰袋，两人分置画面左右形成对峙构图，推至近景时切走。
画面内容：理疗室内日光灯顶光，两人隔床对峙，拓真俯身撑住床沿，目光落在凛生的伤膝上；凛生攥紧床单，指节发白；拓真伸手想碰冰袋，又在半空收回；凛生偏头避开视线，下巴埋进领口。
{拓真（眼神充满占有欲）：听说裁判长前几天为难你了，你可是滑联的宝贝，她到底是因为什么对你动怒的？}
```

<a id="安装为-agent-skill"></a>

## 安装为 Agent Skill

```bash
# Claude Code
cp -r drama-studio ~/.claude/skills/
# Codex / 其他支持 SKILL.md 的客户端：拷入其 skills 目录，或直接让 Agent 读 SKILL.md
```

自包含、可单独拷走：只用 Python ≥3.8 标准库，不调模型、不花额度、可离线自测。

```bash
python scripts/selftest.py   # 104 项断言（含中英镜像一致性检查），约 1 秒
```

## 目录

```
drama-studio/
├── README.md                仓库默认展示（英文）
├── README.zh.md             本文档（中文版）
├── SKILL.md                 Agent 读的主入口（中文）
├── SKILL.en.md              英文镜像
├── scripts/
│   ├── drama_studio.py      确定性工具（解析/种子化/校验/编译/渲染）
│   └── selftest.py          自测（104 项断言，不调模型）
├── references/              中文参考
│   ├── script-format.md         输入剧本格式规范
│   ├── stage-1-assets.md        资产阶段：人物四视图、场景分层物件、UUID 登记
│   ├── stage-2-storyboard.md    分镜阶段：六条切分律与数据结构
│   ├── stage-3-generation.md    成片阶段：编译、验收四门、修复五判决
│   ├── quality-gates.md         26 道质量门总表与设计原则
│   └── en/                      英文镜像（一一对应）
├── assets/
│   ├── pipeline-zh.png          全流程架构图（中文）
│   ├── pipeline-en.png          Pipeline architecture diagram (English)
│   └── templates/               提示词模板与采集单（中文原生：提示词本身以中文交付）
│       ├── character-extract.md      人物提取提示词（造型师）+ 四视图前缀
│       ├── scene-extract.md          场景提取提示词（美术指导）+ 空镜写法
│       ├── asset-intake.md           资产登记单（字段字典 + 流程）
│       └── production-brief.md       生产简报
└── examples/                   三打白骨精整套样例（同时是自测夹具）
```

> 语言约定：切片 Prompt、提取提示词、示例数据保持中文原生（它们的工作语言就是中文）；文档层双语——仓库默认展示英文（`README.md` / `SKILL.en.md` / `references/en/`），中文在 `README.zh.md` / `SKILL.md` / `references/`，自测会检查镜像缺失。

## 它向谁学了什么

- **shuohao-skills**：JSON 单一事实源 + 脚本做校验渲染；`seed` 命令做上游确定性搬运；质量门代码化、逐条病灶；台词逐字门与覆盖门。
- **dramake**：三态状态机（generated ≠ accepted，实测覆盖计划）；generation_block 事件负载预算；四道验收门与 P0 判定；一次只改一个变量 + 尝试预算；参考职责与不传递。
- **seedance-2.0-os**：提示词是编译不是写作；身份保真度卸载给参考图；反 slop（不写空泛评价词）；重拍经济学（五判决 + shot log）；链深度上限与重新锚定；英文默认的文档布局（hero 图 + 徽章/锚点导航 + 语言切换行）。
- **你的实战范式**：15 秒切片 Prompt（固定模板头、UUID 引用、25-35 汉字、3-5 动作单元、断点规则、上片结尾即下片开头）全部原样保留并写成门禁；资产产出采用你验证过的两条流水线——人物=造型师「外貌+服饰」双段提示词组装白底四视图（16:9），场景=美术指导分层物件清单（核心/环境/隐含）写成空镜提示词（含无可读文字约束）。

## 许可

[MIT](LICENSE)
