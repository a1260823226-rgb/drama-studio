# Stage 3 · AI Generation

Goal: compile the accepted storyboard into **slice prompts ready to feed the generation platform**, generate, verify, repair — until there is a film.

## 1. Compilation (compile-slices)

```bash
python {baseDir}/scripts/drama_studio.py compile-slices <project>-storyboard.json \
  --assets <project>-assets.json --scenes <project>-scenes.json --out <project>-slices.md
```

Compilation is deterministic: the template header, field order, `@UUID` bindings, and verbatim dialogue blocks are all assembled by the script — **the model takes no part**.
Compilation is refused while gates fail (`--force` overrides, for debugging only).

Output structure (`examples/三打白骨精-slices.md` is a complete sample):

1. **Slicing notes**: cut logic, cut-point sequence, continuity sequence, per-slice dialogue character counts.
2. **UUID table**: every character/scene used.
3. **Slice prompts**: one code block per slice, headed by source scene / cut point / size / camera / continuity / dialogue count.
4. **Blank template**: the reusable blank template (source: `assets/templates/slice-prompt.md`).

The anatomy of one slice prompt:

```text
真实电影风格。无BGM。无字幕。风格要求真实，镜头切换自然。
人物：@a9cf0873-e937-4657-8eb0-a2d7dd2f77c2是孙悟空。@f44f5bb2-4cbf-468e-be1f-fe8ddca78d0d是唐僧。@fc55e7ef-0539-4d24-b8e6-63ab5f0f008c是猪八戒。@9ddcf00e-bfb0-480b-8b86-25e914befbbe是沙僧。
场景：@3d1393e6-f6bd-4bac-8c7e-1c8a5ae6efb6是白虎岭古道。
景别：中景。
运镜：推镜。
镜头语言：中景平视，机位略低于马背缓推，唐僧与猴王分置画面左右，马颈作前景压住下缘，收在云影没入雾中。
画面内容：坡上停留处，唐僧扶鞍，悟空立于马侧，唐僧松开缰绳，按住腹部，抬眼看悟空；孙悟空收棒抱拳应命，转身一纵，脚踏云头翻过山脊；猪八戒把担子撂在地上，靠着石头坐下，沙僧持杖四望。
{唐僧（气息虚弱）：悟空，为师腹中饥饿，你去南山摘些桃子来。}
{孙悟空（抱拳）：师父稍等，弟子去去就回，八戒沙僧守好行李。}
```

Compilation discipline:

- **The template header is verbatim-immutable; field order never moves**; size/camera carry no `【】` by default (to add them: `params.fieldBrackets = true`).
- `@UUID` is platform parser syntax: **never rewrite as `[UUID]` or `@凛生`** — a wrong form silently drops the binding.
- **Shot language** sits between camera and visual content: size tier / camera position / move / composition / edit relation — one line stating this slice's visual intent (how to write it: `stage-2-storyboard.md`).
- Dialogue `{}` blocks are verbatim from the script; dialogue-free slices carry no `{}` blocks.
- Visual content = setting + 3-5 action units, deterministically assembled from `actionUnits`.
- Each prompt describes this slice only: it never replays the previous slice's completed actions, and never leaks future story.

## 2. Before generation: preview-confirm-invalidate

Before submitting, output a readable preview: model/entry, mode, duration, resolution, audio, full prompt, reference files and their roles, estimated cost, seed, candidate and retry caps.

- Quality tier ≠ payment authorization: budget caps, upload scope, candidate counts, and stop conditions are authorized separately.
- Once confirmed, **any field change that alters picture or cost voids the confirmation** and must be re-confirmed.
- On successful submission, record the request id immediately; on timeout, query the task history first — **never blindly resubmit** (duplicate payment).

## 3. Acceptance: four gates + evidence

After downloading the real footage, extract frames (head / 25% / 50% / 75% / tail), slow-mo the contact peaks, and transcribe and listen to any audio.

| Gate | What it checks | P0 examples |
|---|---|---|
| **Story** | A cold viewer (no synopsis) can state goal / obstacle / action / result; gags have setup | a gag that only works if a character says "where's my food"; an actor who sees the cause but performs as if blind |
| **Identity & style** | face, body, wardrobe topology, material hold across slices | wrong protagonist identity; wardrobe topology change that makes identity ambiguous |
| **Physics & continuity** | contact has approach→force→response→stable result; axis, direction, prop state are believable | clipping, extra limbs at key contact, a car that should reverse but drives forward |
| **Sound** | one speaker, lip-sync match, consistent timbre, music does not restart | a cat's mouth moving on a crew line, multiple characters speaking in sync |

- **Any P0 failure → no `accepted`, and the slice cannot be a parent for downstream slices.**
- Evidence tiers: directly watched/heard = evidence; user relay = "user-reported"; not checked = "unverified". Never call an unchecked take passed.
- Text-class content (phone UI, letters, price tags) defaults to post-production overlay; generated key text mutating = reject that frame and redo a clean plate.

## 4. Repair: five verdicts + one variable

| Verdict | Condition | Next step |
|---|---|---|
| **Keep** | the primary target is delivered, no fatal defect | lock it, log it, move on |
| **Fix in post** | the defect is in post's domain (color / caption / mix / trim / last few frames) | never burn takes on what an edit fixes in minutes |
| **Edit, don't regenerate** | composition and timing are right, one layer wrong, entry supports edit | keep the take as source, change only the failed layer |
| **Re-roll seed** | prompt is right, sampling unlucky | same prompt, new seed, **max 2-3 times**, then by definition it is the prompt's problem |
| **Rewrite** | the same defect appears in ≥2 candidates | systemic failure: diagnose by mechanism, redesign the slice, do not stack adjectives |

- **One variable per retry**: one prompt clause, or seed, or mode, or one reference.
- **Attempt budget**: before generating, write down the max candidates/retries and the "good enough" bar; if the budget is half spent with no progress on the same defect → stop iterating, switch strategy (shorten, fewer characters, simpler action, different mode). No infinite re-rolls.
- **Minimal repair**: pure audio break → re-mix; seam failure → shorten / action bridge / insert shot; second-half drift → keep the front, re-anchor and shorten; identity/causality failure → regenerate the minimal unit.
- **"Don't generate" is a legitimate deliverable**: dense on-screen text belongs to post; exact real-product behavior belongs to a camera; unclear rights belong to the authorization flow; two failures in budget belong to another idea.

## 5. State update (after each acceptance)

1. Set the slice's `status` to `accepted` / `repair` / `rejected` (`rejected` never enters canon and cannot be a continuation source).
2. Write the **actually observed** ending state back into `exitState` — observed overrides planned; subsequent slices continue from the observed state.
3. Adjust the next slice's `entryState` / `continuity` as needed, re-run `validate-storyboard`, and recompile the affected slices.
4. Extract the accepted tail frame (e.g., at `duration - 0.2s`, leaving a safety margin) as the next chain slice's head-frame reference.

## 6. Assembly and delivery

- Load each slice's **accepted range** (not the whole generation) into the timeline; generated duration ≠ cut duration.
- Split tracks: dialogue / ambience / SFX / music; unify loudness; J/L-cut bridges across sound seams.
- Captions, covers, and text layers are post-production overlays; before delivery, run the technical gates (resolution, loudness, duration, naming).
- Naming: `project_slice_version_ratio_status`, e.g. `青叶_S01-02_v2_9x16_accepted.mp4`.
