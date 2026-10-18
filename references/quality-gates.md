# 质量门总表

门全部是代码（`scripts/drama_studio.py`），不是给人读的清单。违规逐条报病灶，exit 1；缺上游时**明说跳过，不静默**。门查不了的（长相、角度、取景、表演）靠眼睛看图。

## 资产门（validate-assets，10 道）

| id | 查什么 | 阈值 / 判定 |
|---|---|---|
| `structure` | 资产册三类齐全、角色/场景有 name | 非空 |
| `uuid-format` | 每个角色/场景有合法 UUID | 36 位十六进制 UUID |
| `reference-image` | 每个角色/场景都有生图提示词，且参考图已上传或已验收 | 角色 `sheetPrompt` 非空（四视图）、场景 `sheetPrompt` 非空（空镜）；`images[].status` 为 linked/accepted；比例 16:9 |
| `name-free` | 出图提示词不出现角色名 | `appearance/costume/sheetPrompt` 不含 name |
| `sheet-fresh` | 参考图未过期 | `generatedFrom` == 当前 `sheetPrompt` 指纹；已出图未记录指纹时跳过并提示 |
| `scene-objects` | 每个场景有分层物件清单 | 核心+环境必须有（隐含可选）；层级为核心/环境/隐含；每件有 `role` + `visual` |
| `scene-no-text` | 场景空镜提示词声明无可读文字 | 含「不出现任何可读文字」等标记（文字后期叠加） |
| `voice-lock` | 有台词角色锁了音色 | `timbre/pitch/pace` 非空（需 `--scenes`） |
| `scene-coverage` | 剧本每个场次有场景资产 | 按 `sceneRef` 对账（需 `--scenes`） |
| `prop-states` | 叙事道具有状态机 | `states` 非空 |

## 分镜门（validate-storyboard，18 道）

| id | 查什么 | 阈值 / 判定 |
|---|---|---|
| `structure` | 切片非空、九要素齐全 | id/sceneId/title/size/camera/characters/entryState/exitState/continuity |
| `slice-id` | 切片 id 唯一 | 无重复 |
| `slice-seconds` | 单切片时长 | == `params.sliceSeconds`（默认 15） |
| `action-units` | 有效动作单元数 | `minActionUnits`-`maxActionUnits`（默认 3-5） |
| `dialogue-chars` | 单切片台词汉字数 | 25-35；`intense: true` 时 ≤40；无台词切片不设限 |
| `cut-point` | 断点类型合法 | `scene-start/line-end/entrance/exit/action-turn/emotional-pause` |
| `no-delta` | 切片文本不带原始剧本标记 | 无 `△`/`※` |
| `uuid-coverage` | 切片引用可解析 UUID | 人物/场景都在 assets.json 且有 UUID |
| `cast-match` | 切片人物不越出场次 cast | ⊆ 场次 `characters` |
| `speaker-on-screen` | 台词说话人在画内 | ∈ 本切片 characters，或显式 VO/旁白/画外音 |
| `size-camera` | 景别运镜非空 | 非空即过（推荐词表外用 ⚠ 提示，不拦） |
| `shot-language` | 每个切片有一句镜头语言 | 非空且 ≤80 字；无可执行术语（景别/机位/运镜/构图/组接）时 ⚠ 提示 |
| `continuity` | chain 接得上；非链式显式声明入场 | `chain` 的 entryState 归一化 == 上片 exitState；`cut/reanchor` 的 entryState 非空 |
| `scene-boundary` | 跨场不链式 | `sceneId` 变化时 continuity ≠ chain |
| `reanchor-from` | reanchor 列了锚定资产 | `reanchorFrom` 非空 |
| `chain-depth` | 链深度 | 连续 chain ≤ `maxChainDepth`（默认 3） |
| `dialogue-coverage` | 台词逐字、不增不减 | 按场次拼接归一化后与剧本完全相等（长台词可拆分，拼接须还原） |
| `shot-variety` | 景别运镜不复用一套 | 存在 ≥2 种不同 (size, camera) 组合 |

## 设计原则（改阈值前先读）

1. **误拦比没有门更糟**：固定文本占比高的字段不查；关键词扫描误伤的只提示不拦（景别/运镜推荐词表走 ⚠）。
2. **阈值可配**：全部在 `storyboard.json` 的 `params` 里，不写死。
3. **跳过的门明说**：缺 `--scenes` 时 `voice-lock`/`scene-coverage` 的 detail 写明"本门跳过（视为通过）"。
4. **病灶要能改**：每条 detail 都点名具体切片与数字，不是计数。

## 门之外的责任

质量门只能查"可确定"的部分。长相漂移、角度别扭、取镜无聊、表演空洞、笑点好不好笑——**这些必须人看图、人听音**。四道验收门（剧情/身份/物理/声音）是 Stage 3 的责任，见 `stage-3-generation.md`。
