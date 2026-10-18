# Quality Gates — Full Reference

Gates are code (`scripts/drama_studio.py`), not a checklist to read. Violations are reported item by item, exit 1; missing upstream inputs are **declared as skipped, never silent**. What gates cannot check (looks, angle, framing, performance) is checked with your eyes on the image.

## Asset gates (validate-assets, 10)

| id | What it checks | Threshold / rule |
|---|---|---|
| `structure` | the registry has all three kinds, characters/scenes have names | non-empty |
| `uuid-format` | every character/scene has a valid UUID | 36-char hexadecimal UUID |
| `reference-image` | every character/scene has an image prompt, and the reference image is uploaded or accepted | character `sheetPrompt` non-empty (four-view), scene `sheetPrompt` non-empty (plate); `images[].status` ∈ {linked, accepted}; ratio 16:9 |
| `name-free` | image prompts never contain the character's name | `appearance/costume/sheetPrompt` free of name |
| `sheet-fresh` | reference images are not stale | `generatedFrom` == current `sheetPrompt` fingerprint; skipped with a notice when an existing image has no recorded fingerprint |
| `scene-objects` | every scene has a layered object list | core + environment required (implied optional); level ∈ core/environment/implied; each object has `role` + `visual` |
| `scene-no-text` | the scene plate prompt declares no readable text | contains a marker such as "不出现任何可读文字" (text is a post-production overlay) |
| `voice-lock` | speaking characters have locked timbre | `timbre/pitch/pace` non-empty (needs `--scenes`) |
| `scene-coverage` | every script scene has a scene asset | matched by `sceneRef` (needs `--scenes`) |
| `prop-states` | narrative props have a state machine | `states` non-empty (prop cards may be absent) |

## Storyboard gates (validate-storyboard, 18)

| id | What it checks | Threshold / rule |
|---|---|---|
| `structure` | slices non-empty, nine required fields present | id/sceneId/title/size/camera/characters/entryState/exitState/continuity |
| `slice-id` | slice ids unique | no duplicates |
| `slice-seconds` | per-slice duration | == `params.sliceSeconds` (default 15) |
| `action-units` | effective action-unit count | `minActionUnits`-`maxActionUnits` (default 3-5) |
| `dialogue-chars` | per-slice dialogue characters | 25-35; ≤40 when `intense: true`; no floor for dialogue-free slices |
| `cut-point` | cut-point type is legal | scene-start/line-end/entrance/exit/action-turn/emotional-pause |
| `no-delta` | slice text carries no script markers | no `△`/`※` |
| `uuid-coverage` | slice references resolve to UUIDs | characters/scenes exist in assets.json with UUIDs |
| `cast-match` | slice characters stay within the scene cast | ⊆ the scene's `characters` |
| `speaker-on-screen` | dialogue speakers are on screen | ∈ this slice's characters, or explicit VO/旁白/画外音 |
| `size-camera` | size and camera are non-empty | non-empty passes (⚠ notice outside the recommended vocab, no block) |
| `shot-language` | every slice has one line of shot language | non-empty and ≤80 chars; ⚠ notice when no executable term (size/camera/move/composition/edit) appears |
| `continuity` | chain links hold; non-chain slices declare entry | a `chain` slice's entryState normalized == previous exitState; `cut`/`reanchor` entryState non-empty |
| `scene-boundary` | no chain across scenes | continuity ≠ chain when `sceneId` changes |
| `reanchor-from` | reanchor lists its anchoring assets | `reanchorFrom` non-empty |
| `chain-depth` | chain depth | consecutive chain ≤ `maxChainDepth` (default 3) |
| `dialogue-coverage` | dialogue verbatim, nothing added or dropped | per-scene normalized concatenation equals the script exactly (long lines may split; the concatenation must restore the original) |
| `shot-variety` | size/camera not one recipe | ≥2 distinct (size, camera) combinations |

## Design principles (read before changing thresholds)

1. **A false-blocking gate is worse than no gate**: fields dominated by fixed text are not checked; keyword scans that would misfire only earn ⚠ notices (the recommended size/camera vocabulary).
2. **Thresholds are configurable**: all in `storyboard.json`'s `params`, never hard-coded.
3. **Skipped gates say so**: without `--scenes`, `voice-lock`/`scene-coverage` carry the detail "this gate skipped (treated as passed)".
4. **Diagnostics must be actionable**: every detail names the specific slice and number, not a count.

## Responsibilities beyond gates

Gates only check what is determinable. Looks drifting, awkward angles, boring framing, hollow performance, whether a gag is funny — **these require human eyes on the image and human ears on the audio**. The four acceptance gates (story / identity / physics / sound) belong to Stage 3 — see `stage-3-generation.md`.
