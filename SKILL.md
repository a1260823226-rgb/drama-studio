---
name: drama-studio
version: 1.0.0
description: |
  短剧工坊：把一段分场剧本，做成可直接投喂 AI 视频生成的成片生产包。
  三个阶段一条线：依据剧本制作资产（角色/场景/道具母版 + UUID 注册）→ 分镜（15 秒切片、断点切分、连续性链）→ AI 成片（固定模板切片 Prompt 编译、生成、四门验收、修复）。
  适用：真人短剧、独立短片、单元剧；适配即梦/Seedance 等以 @UUID 引用人物与场景的生成平台。
  硬约束全部代码化：单切片 15 秒、台词 25-35 汉字（激烈对峙 ≤40）、3-5 个有效动作单元、台词逐字不改、上片结尾动作即下片起始画面、链深度 ≤3。
  不绑定任何平台/API/模型，执行入口由用户自选。
  当用户给出剧本要求拆切片、要求做角色场景资产、要求生成 AI 短剧、要求修复某个失败镜头时使用。
license: MIT
metadata:
  requires:
    bins: [python3]
    runtimes: [claude-code, codex, workbuddy, any-agent-skills-client]
  language: zh
---

# drama-studio · 短剧工坊

中文 · [English](SKILL.en.md) ｜ 英文镜像：`SKILL.en.md` · `README.en.md` · `references/en/`

把短剧制作当成一条**连续生产线**，而不是一堆提示词。
本 Skill 吃**分场剧本**，吐**可直接复制的 15 秒切片 Prompt**，中间用质量门把每一步焊死。

设计哲学（融合自 shuohao-skills / dramake / seedance-2.0-os 三家，内化为本 skill 自有规则）：

1. **模型只写 JSON 的设计字段，脚本做其余一切**（解析、校验、编译、渲染）。提示词是编译出来的，不是聊出来的。
2. **质量门全部是代码，不是清单**。违规逐条报病灶，exit 1，改完重跑，直到通过。门不过，拒绝编译。
3. **上游事实不让模型重新想一遍**：`parse-script` / `seed-assets` / `seed-storyboard` 做确定性搬运。
4. **身份保真度卸载给参考图**：人物/场景用 `@UUID` 锚定，文本只写增量——这是参考图对文本的权威。
5. **零依赖**：只用 Python 标准库；不调用任何模型，不花任何额度，可完全离线自测。

## 边界（不做的事）

- 不生成图像或视频（记录状态、写提示词、验收结果；出图入口由用户选）。
- 不绑定平台：即梦 / Seedance / 其他任何入口均可，UUID 由用户平台给出后登记。
- 不替用户做授权决策：真人脸、声音、IP 的权利不清时，先问一句或走原创重写。
- 越界会被质量门拦：台词被改写、UUID 缺失、切片超时，都过不了门。

## 三条铁律

1. **静音观看也要能看懂**：铺垫、原因、反应、揭晓必须是可见动作，不能只靠台词解释。
2. **没真实看过、听过、抽帧检查，不得声称素材已通过**：`generated ≠ accepted`，只有验收状态能往下传。
3. **一次只改一个变量**：重试只动一个 prompt 子句、一个种子、或一个参考——否则读不出修复来源。

## 三阶段总览

```
分场剧本 ──parse-script──▶ scenes.json ──seed-assets──▶ assets.json（角色/场景/道具 + UUID + 参考图状态）
                                              │
                                    seed-storyboard ▼
                                    storyboard.json（15s 切片：景别/运镜/镜头语言/动作单元/台词/连续性）
                                              │ validate-storyboard（18 道门）
                                              ▼ compile-slices
                                    切片 Prompt 集（固定模板 + @UUID 绑定 + 逐字台词）
                                              │ 生成 → 抽帧/听音验收（四门）→ 修复或接受
                                              ▼
                                          成片
```

| 阶段 | 输入 | 产出 | 详见 |
|---|---|---|---|
| 1 资产 | 分场剧本 | `assets.json`：角色四视图/场景空镜提示词 + 分层物件清单 + UUID + 参考图状态 | `references/stage-1-assets.md` |
| 2 分镜 | `scenes.json` + `assets.json` | `storyboard.json`：15s 切片 + 连续性链 | `references/stage-2-storyboard.md` |
| 3 成片 | `storyboard.json` + `assets.json` | 切片 Prompt 集 + 验收记录 + 修复记录 | `references/stage-3-generation.md` |

## 工作目录约定

一个项目一个目录，文件名固定， agent 与用户都靠它对话：

```
<项目>/
├── <项目>-script.md        分场剧本（输入）
├── <项目>-scenes.json      parse-script 产物
├── <项目>-assets.json      seed-assets 产物 + 人工补全
├── <项目>-storyboard.json  seed-storyboard 产物 + 人工切分
├── <项目>-slices.md        compile-slices 产物（投产）
├── <项目>-report.md/html   render 产物
└── images/                 参考图与生成素材
```

## Stage 0 · 判断用户会什么（先读这个）

不要要求小白先学会专业术语。按输入深度分流：

- **只有剧本**：走完整三阶段（本 skill 的主路径）。
- **已有资产/分镜**：从对应阶段切入，先 `validate` 体检，**局部问题不得强制重走全流程**。
- **只要诊断**：只跑 validate 系列，输出病灶清单与最小修复建议，不生成、不付费。
- **只要修一个镜头**：只重建该切片的 storyboard 条目，重跑门禁后单独重编译。

## Stage 1 · 依据剧本制作资产

```bash
python {baseDir}/scripts/drama_studio.py parse-script <项目>-script.md --title <项目> --out <项目>-scenes.json
python {baseDir}/scripts/drama_studio.py seed-assets <项目>-scenes.json --out <项目>-assets.json
python {baseDir}/scripts/drama_studio.py uuid-new 凛生 拓真 开太        # 平台上还没有的资产，先生成 UUID
python {baseDir}/scripts/drama_studio.py validate-assets <项目>-assets.json --scenes <项目>-scenes.json
```

Agent 要做的事（细节与提示词模板见 `references/stage-1-assets.md`）：

1. **人物**：用 `character-extract.md` 的造型师提示词为每个角色产出两段——`appearance`（五官及外貌）+ `costume`（服饰）；`build-sheets --apply` 组装成白底四视图生图提示词（16:9，脸部特写+正/侧/背面全身）并盖指纹；出图上传后 `images[].status = linked`。
2. **场景**：用 `scene-extract.md` 的美术指导提示词产出分层物件清单（核心/环境/隐含——隐含物件是跨切片不漂移的根）；据此手写空镜 `sheetPrompt`（按空间顺序铺陈 + 光线机位 + 无可读文字）。
3. 平台给出 UUID 后填回 `assets.json`；跑 `validate-assets`（10 道门），逐条修到全过。

**没出图之前不得进入 Stage 3**：UUID 没有绑定参考图，模型会当场发明一张脸。改了描述必须重出图——`generatedFrom` 指纹对不上即过期。

## Stage 2 · 分镜（15 秒切片）

```bash
python {baseDir}/scripts/drama_studio.py seed-storyboard <项目>-scenes.json --aspect 9:16 --out <项目>-storyboard.json
# 编辑 storyboard.json 的 slices（规则见 references/stage-2-storyboard.md）
python {baseDir}/scripts/drama_studio.py validate-storyboard <项目>-storyboard.json --scenes <项目>-scenes.json --assets <项目>-assets.json
python {baseDir}/scripts/drama_studio.py render <项目>-storyboard.json --assets <项目>-assets.json --scenes <项目>-scenes.json --out <项目>-report.md
```

切分六律（全部由 `validate-storyboard` 的 18 道门强制执行）：

1. **时长**：每切片恰好 15 秒。
2. **台词**：单切片合计 25-35 汉字；激烈对峙标 `intense: true` 可到 40；无台词切片不设下限；超长台词必须拆到下一片（拼接后须逐字还原）。
3. **动作单元**：每切片 3-5 个有效动作单元；剔除眨眼这类无意义细碎动作；复杂冲突必须切开，禁止大段剧情塞进单条。
4. **断点**：只切在 单句台词结束 / 人物入场 / 人物离场 / 重大动作转折 / 情绪停顿；`cutPoint` 字段如实声明。
5. **连续性**：`chain` 切片的 `entryState` 必须逐字接住上一片 `exitState`（上一个切片的结尾动作，就是下一个切片的起始画面）；跨场必须 `cut` 或 `reanchor`；链深度 ≤3，超了从母版重开。
6. **景别、运镜与镜头语言**：逐镜按剧情匹配，不复用一套；每个切片写一句镜头语言（景别层次/机位角度/运镜方式/构图/组接，≤80 字），回答"为什么这样拍"。

## Stage 3 · AI 成片

```bash
python {baseDir}/scripts/drama_studio.py compile-slices <项目>-storyboard.json --assets <项目>-assets.json --scenes <项目>-scenes.json --out <项目>-slices.md
```

编译产物 = 固定模板头 + `@UUID` 人物/场景行 + 景别/运镜 + 镜头语言 + 画面内容（环境铺垫 + 3-5 动作单元）+ `{角色（情绪）：台词}` 逐字块；结尾附通用空白模板。**模板头逐字不可改，字段顺序不可动。**

生成与验收（细节见 `references/stage-3-generation.md`）：

1. **预览-确认**：提交前输出可读预览（模型/入口/时长/分辨率/完整 prompt/参考文件及职责/预计费用/候选与重试上限）；任何改变画面或费用的字段变更都要重新确认。
2. **证据验收**：下载真实素材，抽帧（开头/25%/50%/75%/结尾）、慢放查接触、有音频就转写人工听。四道门：**剧情 / 身份画风 / 物理连续 / 声音**；任何 P0 不过就不得标 `accepted`。
3. **修复五判决**：保留 / 后期修 / 编辑而非重生 / 换种子重抽（≤2-3 次）/ 重写（同缺陷 ≥2 个候选）。一次只改一个变量，尝试预算过半无进展就换策略。
4. **状态更新**：验收后把 `status` 改为 `accepted`，把实际观察到的结尾状态写回 `exitState`——**实测状态覆盖计划状态**，后续切片从实测状态继续，不从计划状态继续。

## 质量门总表

| 阶段 | 门数 | 代表门禁 |
|---|---|---|
| 资产 `validate-assets` | 10 | `reference-image`（四视图/空镜提示词+图+16:9）/ `sheet-fresh`（指纹未过期）/ `scene-objects`（分层物件清单）/ `scene-no-text`（无可读文字）/ `name-free` / `voice-lock` |
| 分镜 `validate-storyboard` | 18 | `slice-seconds` / `dialogue-chars` / `action-units` / `cut-point` / `continuity` / `chain-depth` / `dialogue-coverage`（台词逐字）/ `shot-language`（镜头语言）/ `shot-variety` |

完整 id、阈值与病灶文案见 `references/quality-gates.md`。门查不了的（长相、角度、取景、表演）**靠眼睛看图**，不假装门能查。

## 连续性模型（速查）

- 每个切片有 `entryState` / `exitState`；`chain` = 上片尾帧即本片首帧。
- 切片状态：`planned → generated → reviewed → accepted | repair | rejected`；`rejected` 不进 canon，不能当续拍源。
- 链深度默认 ≤3（`maxChainDepth`）；换场、换装、发现漂移、连续两个长片后，从角色/场景母版 `reanchor`。
- 好的接缝至少保住两项：动作 / 方向 / 形状 / 视线 / 声音 / 光线。

## 快速通道

- **只要切片 Prompt**：剧本已在手 → parse-script →（资产 UUID 已有的话直接）seed-storyboard → 填 slices → validate → compile。跳过出图等待，但 `anchor-image` 门会提醒风险。
- **只要诊断**：只跑 validate 系列，输出病灶，不动 slices。
- **修一个镜头**：只改那一个切片条目，重跑 validate + compile。

## 命令速查

```
parse-script <script.md> [--title T] [--out scenes.json]    剧本 → scenes.json
seed-assets <scenes.json> [--out assets.json]               资产骨架
build-sheets <assets.json> [--apply]                        组装人物四视图提示词并盖指纹
uuid-new [--count N] [名字...]                              生成 UUID
validate-assets <assets.json> [--scenes scenes.json]        资产 10 门
seed-storyboard <scenes.json> [--aspect 9:16] [--out sb.json] 分镜骨架+切分计划
validate-storyboard <sb.json> --scenes S --assets A         分镜 18 门（核心）
compile-slices <sb.json> --assets A [--scenes S] [--out slices.md]  编译（门不过拒绝）
render <sb.json> [--assets A] [--scenes S] [--html|--md] [--out F]  报告
slug <名字>                                                  安全文件名
```

所有命令默认打印到 stdout，可重定向落盘；`--out` 直接写文件。脚本路径一律写 `{baseDir}/scripts/drama_studio.py`，本 skill 自包含、可单独拷走。

本文档的中文版为主文档；`references/en/` 与 `references/` 一一对应，`selftest.py` 会检查镜像缺失。

## 自测与示例

```bash
python {baseDir}/scripts/selftest.py     # 104 项断言，不调模型不花额度，约 1 秒
```

`examples/青叶大学-*` 是一整套跑通的样例（剧本 → scenes → assets → storyboard → slices → report），同时是自测夹具。改动脚本后先跑自测。
