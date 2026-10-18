# Stage 2 · Storyboard (15-Second Slices)

Goal: cut the script into a set of **independently usable slices whose concatenation restores the story**, each slice an acceptable generation contract.
Slicing is creative work, but the six hard laws are all enforced by the 18 gates of `validate-storyboard` — **a failing gate means no compilation**.

## Slice data structure

```jsonc
{
  "id": "S01-02",                 // scene-seq: unique
  "sceneId": "3-2",               // owning scene (one scene per slice group; a location change opens a new scene)
  "title": "占有欲的试探",         // slice subtitle
  "seconds": 15,
  "cutPoint": "line-end",         // cut-point type at this slice's opening
  "size": "中近景",               // shot size, matched to the story (template four: medium/medium-close/close/full)
  "camera": "推镜",               // camera move: one primary action
  "shotLanguage": "中近景侧机位缓推，浅景深锁定伤膝与冰袋，两人分置画面左右形成对峙构图，推至近景时切走。",
                                // shot language: size tier / camera position / move / composition / edit relation — one line (≤80 chars)
  "setting": "理疗室内日光灯顶光，两人隔床对峙",   // environmental setup (optional)
  "actionUnits": [                // 3-5 effective action units; meaningless micro-actions like blinks are dropped
    "拓真俯身撑住床沿，目光落在凛生的伤膝上",
    "凛生攥紧床单，指节发白",
    "拓真伸手想碰冰袋，又在半空收回",
    "凛生偏头避开视线，下巴埋进领口"
  ],
  "dialogue": [                   // dialogue verbatim from the script, not one byte changed
    { "speaker": "拓真", "emotion": "眼神充满占有欲", "line": "听说裁判长前几天为难你了？" }
  ],
  "characters": ["凛生", "拓真"], // on-screen characters (by name; resolved to UUIDs at compile time)
  "props": ["冰袋"],
  "entryState": "拓真立于床前两步之外，房门已带上，凛生抬眼戒备",
  "exitState": "拓真俯身撑着床沿，目光落在伤膝上，凛生攥紧床单偏头避开",
  "continuity": "chain",          // scene-start / chain / cut / reanchor
  "reanchorFrom": [],             // required when reanchor: ["C01","C02","S01"]
  "intense": false,               // intense confrontation: dialogue cap raised to 40
  "status": "planned"             // planned → generated → reviewed → accepted | repair | rejected
}
```

## The six slicing laws

### 1. Duration: each slice exactly 15 seconds

`seconds` must equal `params.sliceSeconds`. 15 seconds is the generation container, not a content ceiling.

### 2. Dialogue: 25-35 Chinese characters, max 40 when intense

- Counted in **Chinese characters** (punctuation excluded): 听说裁判长为难你了 = 9.
- The slice total lands in 25-35; mark `intense: true` for confrontation up to 40.
- Over-long lines must split into the next slice; **after splitting, the concatenation must restore the original verbatim** (the `dialogue-coverage` gate concatenates per scene and compares — nothing added, dropped, or reworded).
- Dialogue-free slices (pure action / empty frames) have no floor and carry no `{}` blocks.
- Every line names one speaker, one visible mouth shape; non-speakers' closed mouths are checked at acceptance.

### 3. Action units: 3-5

- Each slice holds 3-5 **effective action units** (posture, blocking, expression, prop interaction, conflict detail).
- Drop meaningless micro-actions like blinks or breathing ripples; complex conflicts and continuous fights must be split.
- Event-load discipline: one 15-second slice carries **one primary prop system + one high-risk physical chain + one primary emotional payoff**.
- No freezing after a line: schedule reactions and exits around the dialogue (breath, eyeline shift, weight change).

### 4. Cut points: only these five nodes

| cutPoint | Meaning |
|---|---|
| `line-end` | end of a single line |
| `entrance` | character enters |
| `exit` | character exits |
| `action-turn` | major action turn |
| `emotional-pause` | emotional pause |

The first slice is marked `scene-start`. **The previous slice's ending action must be the next slice's opening** — not a stylistic preference, but a hard check by the `continuity` gate.

### 5. Continuity: chain / cut / reanchor

```
scene-start ─chain─▶ chain ─chain─▶ [chain depth reaches 3] ─reanchor─▶ chain ─cut─▶ next scene
```

- `chain`: this slice's head frame = the previous slice's accepted tail frame; `entryState` must catch the previous `exitState` verbatim.
- `reanchor`: when chain depth hits the cap, on a wardrobe change, or on detected drift, re-open from the character/scene masters; the entry state is declared explicitly and `reanchorFrom` lists the assets. Resets chain depth.
- `cut`: an intentional edit (no frame-continuity promise), for scene boundaries or rhythm switches.
- Scene changes (`sceneId` change) **forbid chain** — a scene boundary opens from the masters.
- Chain depth ≤ `params.maxChainDepth` (default 3).
- A good seam preserves at least two of: motion / direction / shape / eyeline / sound / light.

### 6. Size, camera, and shot language: match shot by shot

- One primary camera move per slice, with a start and an end; a move must be motivated (reveal, follow, change what) — if stillness expresses the intent better, hold still.
- Shot size carries relation: full = situation and scale, medium = confrontation, medium-close = emotion, close = key prop / micro-expression.
- Each slice answers "why shoot it this way"; the `shot-variety` gate blocks "one recipe for everything".

## Shot language: one line stating the visual intent

Shot language is the **visual expression system that transmits the filmmaker's intent through the camera** — using size changes, shooting techniques, and image combination to serve narrative. It has no fixed rules, but the toolbox is stable in four layers:

### ① Shot size (distance and angle)

| Size | Framing | Narrative function |
|---|---|---|
| Extreme long / long / wide-long | figure ant-small, environment swallows the person | situation, solitude, fusion with the world |
| Extreme wide | subject + surrounding environment | environmental introduction, the widest shot |
| Full | full body / scene overview | the relation between action and environment |
| Medium-full | head-to-toe, relatively complete | pressure or smallness |
| Medium | calf-up (seven-tenths) | the workhorse of performance scenes, balanced |
| Medium-close / half-body | waist to head | relation and emotion |
| Close | chest-up | approaching observation, emotional impact |
| Close-up / extreme close-up | shoulder-up / local detail | instantaneous reaction, key prop (brow, eye, trigger) |

Usage: the `size` field picks from the template four (medium/medium-close/close/full); finer tiers (wide-long, medium-full, extreme close-up) go into `shotLanguage`.

### ② Shooting techniques (presenting spatial relations dynamically)

Push / pull / pan / truck / follow / crane up / crane down / tilt down / tilt up / whip /悬 / empty / combined; reverse shot, zoom, POV.
Principle: **one primary move per shot**, with a start and an end, and the move must be motivated.

### ③ Composition and angle (power relations inside the frame)

- Angle: front / side / back / level / low / high — height carries power and sympathy; low angle reads tall and solemn, high angle shows the whole.
- Layers: foreground / midground / background — depth; foreground presses the frame, background establishes environment.
- Rule of thirds, frame-in-frame, negative space, edge-hugging, depth of field (shallow = locks the subject, pushes environment back).
- Composition is relation: two figures split left/right = confrontation, one large one small = power gap, a subject framed by a doorway = trapped.

### ④ Editing relations (grammar between shots)

Fade in / fade out / dissolve / superimpose / wipe / enter frame / exit frame / freeze / flashback; cut (continuous / insert); montage (narrative: parallel, cross-cutting).
Principle: a good seam preserves at least two of — motion / direction / shape / eyeline / sound / light; a jump cut is a rhythm tool, not a cover for sloppiness.

### How to write it

`shotLanguage` is one line (≤80 chars) covering whichever layers apply: **size tier + camera position + move + composition + edit relation with adjacent shots**. Examples:

```text
特写仰拍，拓真封住画面上缘形成压迫构图，凛生眼睫特写接冰袋水珠特写，交叉剪辑节奏加紧。
大全景定场，平视固定机位，人物置于右下三分线，白床单作前景压住画幅，长镜头缓起，与切片2的中近景形成景别跳切。
```

- Land on executable terms (the `shot-language` gate checks presence and length; vague writing only earns a warning, but the warning must be heeded).
- Cross-slice shot language must form a system: the size ladder advances and retreats (full → medium → close is approach, the reverse is distance), move density has rhythm, seam types carry intent — **a single shot's form never exists in isolation**.

## Workflow

1. `seed-storyboard` produces the skeleton + scene plan (dialogue lines/chars, action beats, estimated seconds, suggested slice count — the suggestion is a starting point; adjust by cut points and dialogue load).
2. Hand-write `slices` per the six laws: decide cut points first, then action units and dialogue (copy verbatim from scenes.json), then entry/exit states.
3. Run `validate-storyboard` until green; fix defects item by item — **never edit dialogue just to satisfy a gate**; dialogue changes go back to the script layer.
4. `render` outputs the report for a self-check of the continuity chain.

## Common defects

| Defect | Fix |
|---|---|
| 41 characters in one slice | Split into the next slice, or confirm true confrontation and mark `intense` |
| 6 action units | Merge like items or cut to the next slice |
| `continuity` gate reports a broken link | Copy the previous slice's `exitState` verbatim as this slice's `entryState` |
| `dialogue-coverage` reports a mismatch | Dialogue was reworded / dropped / moved between scenes — check verbatim against scenes.json |
| Chain depth exceeded | Make the next slice `reanchor` (list masters) or `cut` |
| Cross-scene chain | Scene boundary must be `cut` or `reanchor` |
