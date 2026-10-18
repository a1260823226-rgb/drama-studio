# Stage 1 · Build Assets from the Script

Goal: every **character**, **scene**, and **narrative prop** in the script gets a design record, a reference image (set), and a platform UUID.
Every downstream slice prompt binds them via `@UUID` — **identity fidelity is offloaded to reference images; text carries only the increment**.

The output pattern (two battle-tested pipelines):

- **Characters**: a stylist prompt produces "appearance + costume" two parts → assembled into a **white-background four-view** image prompt (16:9) → generate and upload → register the UUID.
- **Scenes**: an art-director prompt produces a **layered object list** (core / environment / implied) → written into a **plate** image prompt → generate and upload → register the UUID.

## 1. Characters: from script to four-view

### Extraction (character-extract.md)

Feed the script to the "veteran film stylist" prompt; each on-screen character yields two parts:

1. **Face and appearance**: age/gender/identity → height and build → face and features → skin → hair, down to drawable, checkable detail.
2. **Costume**: cut and form → fabric → palette → trims and accessories → signs of wear; form comes first (mid-prompt detail gets lost in translation).

Iron rules: **never write the character's name** (the four-view shape identifies the person, not the name); every character gets at least one **recognition anchor** (Sun Wukong's headband, Tang Sanzang's nine-ringed staff).

### Assembly (build-sheets)

```bash
python {baseDir}/scripts/drama_studio.py build-sheets <project>-assets.json            # preview
python {baseDir}/scripts/drama_studio.py build-sheets <project>-assets.json --apply    # write back and stamp fingerprints
```

`sheetPrompt = four-view prefix + appearance + costume`, assembled deterministically; the model takes no part:

```text
AI生图提示词的前缀。帮我根据要求生成白底人物四视图，图片尺寸为16:9，四视图从左到右依次为镜头拍人物脸部特写，人物正面全身站立图，人物侧面全身站立图，人物背面全身站立图生成效果：真实质感，人物肌肤与毛孔贴近现实不油光，人物衣物细节拉满：
```

The four-view = four angles in one image (face close-up + front/side/back full-body), white background, 16:9. One image serves three jobs at once: **identity anchor, wardrobe topology master, and proportion reference** — more stable than a chain of images (chains accumulate drift; regenerating one drags the rest).

### Wardrobe changes

A wardrobe change is a new look state, not an overwrite: append to `outfits[]` (`id/label/costume/sheetPrompt/status/generatedFrom`). Default look and competition look get one four-view each; the UUID stays the same (same character), and slices reference whichever applies.

### Generation and registration

After generating, set `images[].status` to `linked`; after frame-checking, `accepted`. Reference-image hard limits: single side 300-5760 px, aspect ratio 0.4-2.5, ≤20MB, four-view ratio 16:9. What gates cannot check (looks, angle, proportion) is checked **with your eyes on the image**.

## 2. Scenes: from script to plate

### Extraction (scene-extract.md)

Feed the script to the "film art director" prompt to produce a **layered object list**:

| Level | Definition | Example (rocky slope) |
|---|---|---|
| Core | Explicitly mentioned, forms the scene's subject | grey-white boulders, flat stone at the slope mouth, clay jar and green porcelain bottle |
| Environment | Builds background and atmosphere | half-dispersed fog, dry grass and gravel, shallow gully between boulders |
| Implied | Unstated but logically inevitable | leftover offerings, burlap seal on the jar's mouth |

**Implied objects are the root of continuity**: the script only says "carrying the jar to deliver a meal", but the jar, its seal, and the leftovers logically exist — leave them unregistered, and the model improvises a different one every generation, and cross-slice drift is guaranteed. If scenes must connect, objects must be stated by necessity and priority.

### Assembling the plate prompt

`sheetPrompt` is written by the agent as a **plate description** from the object list + atmosphere summary, laid out in spatial order:

```text
东方神话写实电影风格，荒山乱石坡空镜，无人场景。画面中景是一组灰白巨石，表面被雨水冲出浅沟……
巨石前一块半人高的平顶石，石上放着一只粗陶青砂罐与一只釉色发暗的绿磁瓶，罐口蒙着麻布……
石群之间是一道半人深的浅沟……坡面枯草成簇，碎石遍布……远处浓雾被日光顶开一半……
偏冷的中性日光从右上方斜下，白石反光晃眼，泥地显脏……镜头中景广角，平视略低，巨石压住画面右侧三分之一……
写实影视剧照质感，电影级画质。画面中不出现任何可读文字、数字、标语、品牌名、标签或说明字样。
```

Six rules of thumb: ① plate means no people, no hands; ② spatial order — midground boulders → flat stone → gully → slope → distance; ③ concrete material/color/form (coarse pottery, dull glaze, burlap seal); ④ state lighting and camera position; ⑤ **close with the no-readable-text clause** (checked by the `scene-no-text` gate; text is a post-production overlay); ⑥ for time-of-day/lighting variants, re-generate with a new `atmosphere` and `sheetPrompt`, UUID unchanged.

### Narrative props

Static in-scene objects go into `scenes[].objects`; only props that **move across scenes and change state** get a prop card (`states[]` state machine: count/position/orientation/open-closed/intact/dry-wet/text layer).

## 3. UUID registry and lifecycle

- UUIDs are issued by the **user's generation platform** (after reference images are uploaded), or minted locally with `uuid-new`.
- `assets.json` is the single source of truth for UUIDs; slices carry names only, and `compile-slices` resolves them to `@UUID`.
- Image status: `pending → linked → accepted`. **Without a `linked`/`accepted` reference image, the `reference-image` gate fails and Stage 3 refuses compilation** — the model would invent a face on the spot.
- **Any description change requires regeneration**: `generatedFrom` is the fingerprint of the prompt at generation time; a mismatch means stale (caught by the `sheet-fresh` gate). Change appearance/costume → re-run `build-sheets --apply` → regenerate → re-accept.

## 4. Sound

Every speaking character locks `voice.timbre / pitch / pace / accent` (checked by the `voice-lock` gate). The voice bible serves dubbing and lip-sync acceptance: the same character's timbre must hold across slices — spot-check with ASR transcription plus a manual A/B blind listen.

## Commands

```bash
python {baseDir}/scripts/drama_studio.py seed-assets <project>-scenes.json --out <project>-assets.json
python {baseDir}/scripts/drama_studio.py build-sheets <project>-assets.json --apply
python {baseDir}/scripts/drama_studio.py uuid-new 孙悟空 唐僧 猪八戒 沙僧 白骨精
python {baseDir}/scripts/drama_studio.py validate-assets <project>-assets.json --scenes <project>-scenes.json
```
