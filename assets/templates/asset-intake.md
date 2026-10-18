# 资产登记单（Asset Intake）

> 每个项目一份 `assets.json`。本单是字段字典 + 登记流程；提取提示词见
> `character-extract.md`（人物）与 `scene-extract.md`（场景）。

## 角色卡

| 字段 | 来源 | 说明 |
|---|---|---|
| `name` / `uuid` | 剧本 / 平台 | 切片里写名字，编译时解析为 `@UUID` |
| `importance` | protagonist / major / supporting / minor | |
| `appearance` | 造型师提示词·内容一 | 五官及外貌，一段流式描写 |
| `costume` | 造型师提示词·内容二 | 服饰：形制→面料→配色→使用痕迹 |
| `sheetPrompt` | `build-sheets` 组装 | 四视图前缀 + appearance + costume |
| `outfits[]` | 换装时追加 | `{id,label,costume,sheetPrompt,status,generatedFrom}` |
| `recognition` | 自定 | 识别锚点：跨切片认人的那一处 |
| `generatedFrom` | `build-sheets --apply` | 出图时 sheetPrompt 的指纹；对不上 = 图过期 |
| `images[]` | 出图后登记 | `{view:"four-view", ratio:"16:9", status, note}` |
| `voice` | 自定 | `{timbre,pitch,pace,accent}`——有台词角色必填 |

图片状态流转：`pending → linked（已上传平台）→ accepted（抽帧验收过）`。

## 场景卡

| 字段 | 来源 | 说明 |
|---|---|---|
| `name` / `uuid` / `sceneRef` | 剧本场次 | |
| `summary` | 自定 | 设计意图，不是户型说明 |
| `objects[]` | 美术指导提示词 | `{name,level,category,role,visual}`；level ∈ 核心/环境/隐含 |
| `atmosphere` | 美术指导提示词 | 场景整体氛围总结（16:9） |
| `sheetPrompt` | Agent 手写 | 空镜描述：按空间顺序铺陈 + 光线机位 + 无可读文字 |
| `generatedFrom` | 手写后盖指纹 | 同上；`build-sheets --apply` 可补盖 |
| `images[]` | 出图后登记 | `{view:"sheet", ratio:"16:9", status, note}` |

## 道具卡（跨场景流转的叙事道具）

| 字段 | 说明 |
|---|---|
| `name` / `scale` | 手持级 / 桌面级 / 家具级 |
| `summary` | 戏剧功能（它在故事里干什么） |
| `anchors` | 一致性锚点 |
| `states[]` | 状态机：数量/位置/朝向/开合/完好/干湿/文字图层 |
| `carriedBy` / `relatedScenes` | 谁带着、在哪几场出现 |

> 场景内静态物件进 `scenes[].objects`；**跨场景流转、有状态变化**的叙事道具才建道具卡（如凛生的冰袋：fresh → melting）。

## 登记流程

1. `seed-assets` 出骨架（角色/场次自动建卡）。
2. 人物：`character-extract.md` 提示词 → `appearance` / `costume` → `build-sheets --apply` 组装出 `sheetPrompt` 并盖指纹 → 出图 → `images[].status = linked`。
3. 场景：`scene-extract.md` 提示词 → `objects` + `atmosphere` → 手写 `sheetPrompt` → 盖指纹 → 出图 → `status = linked`。
4. 平台给 UUID 后填回；`validate-assets` 跑到 10 道门全过。

## 反模式

- 在 appearance/costume 里写角色名（`name-free` 门拦）。
- 改了描述不重出图（`sheet-fresh` 门拦）。
- 场景提示词不声明无可读文字（`scene-no-text` 门拦）。
- 隐含物件不登记——模型会每次即兴发明一个。
