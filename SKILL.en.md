---
name: drama-studio
version: 1.0.0
description: |
  Short-Drama Studio: turn a scene-based script into a production pack of AI-video-ready slice prompts.
  Three stages on one line: build assets from the script (character/scene/prop masters + UUID registry) → storyboard (15-second slices, cut-point splitting, continuity chain) → generation (fixed-template slice prompt compilation, generation, four-gate acceptance, repair).
  Works for live-action short drama, standalone shorts, and anthology episodes; fits generation platforms that reference characters and scenes by @UUID (Dreamina, Seedance, and similar).
  Hard constraints are code-enforced: 15 seconds per slice, 25-35 Chinese characters of dialogue per slice (max 40 for intense confrontation), 3-5 effective action units, dialogue verbatim, previous slice's ending action is the next slice's opening frame, chain depth ≤3.
  Not bound to any platform, API, or model — the execution entry point is the user's choice.
  Use when the user supplies a script and asks for slice splitting, character/scene assets, AI short-drama generation, or repair of a failed take.
license: MIT
metadata:
  requires:
    bins: [python3]
    runtimes: [claude-code, codex, workbuddy, any-agent-skills-client]
  language: en
---

# drama-studio · Short-Drama Studio

Treat short-drama production as one **continuous production line**, not a pile of prompts.
This skill eats a **scene-based script** and spits out **copy-paste-ready 15-second slice prompts**, with quality gates welding every step shut.

Design philosophy (fused from shuohao-skills / dramake / seedance-2.0-os, internalized as this skill's own rules):

1. **The model writes only the design fields of the JSON; the script does everything else** (parse, validate, compile, render). Prompts are compiled, not chatted.
2. **Quality gates are code, not checklists**. Violations are reported item by item, exit 1, fix and re-run until green. A failing gate refuses compilation.
3. **Upstream facts are never re-invented by the model**: `parse-script` / `seed-assets` / `seed-storyboard` move them deterministically.
4. **Identity fidelity is offloaded to reference images**: characters and scenes are anchored by `@UUID`; text carries only the increment — that is the reference image's authority over text.
5. **Zero dependencies**: Python standard library only; no model calls, no quota, fully offline self-test.

## Boundaries (what this skill does not do)

- Does not generate images or video (it records status, writes prompts, logs acceptance; the generation entry point is the user's choice).
- Not platform-bound: Dreamina / Seedance / any other entry works; UUIDs are registered once the user's platform issues them.
- Does not make rights decisions for the user: when real-face, voice, or IP rights are unclear, ask one short question or rewrite toward original material.
- Boundary violations are caught by gates: reworded dialogue, missing UUIDs, over-long slices — none of them pass.

## Three iron rules

1. **It must be understandable muted**: setup, cause, reaction, and payoff must be visible actions, never explained only by dialogue.
2. **Never claim a take passed without actually watching, hearing, or frame-checking it**: `generated ≠ accepted`; only accepted state propagates downstream.
3. **Change one variable at a time**: a retry moves exactly one prompt clause, one seed, or one reference — otherwise the source of the fix is unreadable.

## Three stages at a glance

```
scene script ──parse-script──▶ scenes.json ──seed-assets──▶ assets.json (characters/scenes/props + UUIDs + reference status)
                                              │
                                    seed-storyboard ▼
                                    storyboard.json (15s slices: size/camera/shot language/action units/dialogue/continuity)
                                              │ validate-storyboard (18 gates)
                                              ▼ compile-slices
                                    slice prompt set (fixed template + @UUID bindings + verbatim dialogue)
                                              │ generate → frame/audio acceptance (four gates) → repair or accept
                                              ▼
                                          the film
```

| Stage | Input | Output | Details |
|---|---|---|---|
| 1 Assets | scene script | `assets.json`: four-view/plate prompts + layered object list + UUIDs + reference status | `references/en/stage-1-assets.md` |
| 2 Storyboard | `scenes.json` + `assets.json` | `storyboard.json`: 15s slices + continuity chain | `references/en/stage-2-storyboard.md` |
| 3 Generation | `storyboard.json` + `assets.json` | slice prompt set + acceptance log + repair log | `references/en/stage-3-generation.md` |

## Working-directory convention

One project, one directory, fixed file names — agent and user both talk through it:

```
<project>/
├── <project>-script.md        scene script (input)
├── <project>-scenes.json      parse-script output
├── <project>-assets.json      seed-assets output + manual fill-in
├── <project>-storyboard.json  seed-storyboard output + manual slicing
├── <project>-slices.md        compile-slices output (production-ready)
├── <project>-report.md/html   render output
└── images/                    reference images and generated footage
```

## Stage 0 · Read what the user can do first

Never require a beginner to learn the jargon first. Route by input depth:

- **Script only**: run the full three stages (this skill's main path).
- **Assets/storyboard already exist**: enter at the matching stage, run `validate` as a checkup first — **a local problem must never force a full re-run**.
- **Diagnosis only**: run the validate family only; output the defect list and minimal repair advice. No generation, no payment.
- **One broken shot**: rebuild just that slice's storyboard entry, re-run the gates, recompile that slice alone.

## Stage 1 · Build assets from the script

```bash
python {baseDir}/scripts/drama_studio.py parse-script <project>-script.md --title <project> --out <project>-scenes.json
python {baseDir}/scripts/drama_studio.py seed-assets <project>-scenes.json --out <project>-assets.json
python {baseDir}/scripts/drama_studio.py uuid-new Rinsheng Takashi Kaita   # assets not yet on the platform: mint UUIDs first
python {baseDir}/scripts/drama_studio.py validate-assets <project>-assets.json --scenes <project>-scenes.json
```

What the agent does (templates and details in `references/en/stage-1-assets.md`):

1. **Characters**: run the stylist prompt from `character-extract.md` for each character to produce two parts — `appearance` (face and looks) + `costume` (wardrobe); `build-sheets --apply` assembles the white-background four-view image prompt (16:9: face close-up + front/side/back full-body) and stamps the fingerprint; after generating and uploading, set `images[].status = linked`.
2. **Scenes**: run the art-director prompt from `scene-extract.md` to produce the layered object list (core / environment / implied — implied objects are the root of cross-slice stability); from it, hand-write the plate `sheetPrompt` (spatial order + lighting and camera + the no-readable-text clause).
3. Once the platform issues UUIDs, fill them back into `assets.json`; run `validate-assets` (10 gates) and fix item by item until green.

**Do not enter Stage 3 before images exist**: a UUID with no bound reference image, and the model invents a face on the spot. If the description changes, the image must be regenerated — a mismatched `generatedFrom` fingerprint means stale.

## Stage 2 · Storyboard (15-second slices)

```bash
python {baseDir}/scripts/drama_studio.py seed-storyboard <project>-scenes.json --aspect 9:16 --out <project>-storyboard.json
# edit the slices of storyboard.json (rules in references/en/stage-2-storyboard.md)
python {baseDir}/scripts/drama_studio.py validate-storyboard <project>-storyboard.json --scenes <project>-scenes.json --assets <project>-assets.json
python {baseDir}/scripts/drama_studio.py render <project>-storyboard.json --assets <project>-assets.json --scenes <project>-scenes.json --out <project>-report.md
```

The six slicing laws (all hard-enforced by the 18 gates of `validate-storyboard`):

1. **Duration**: each slice is exactly 15 seconds.
2. **Dialogue**: 25-35 Chinese characters per slice; mark `intense: true` for confrontation up to 40; no floor for dialogue-free slices; over-long lines must split into the next slice (and the concatenation must restore the original verbatim).
3. **Action units**: 3-5 effective action units per slice; drop meaningless micro-actions like blinks; complex conflicts must be split — never cram a whole plot beat into one slice.
4. **Cut points**: cut only at end of a line / entrance / exit / major action turn / emotional pause; declare `cutPoint` honestly.
5. **Continuity**: a `chain` slice's `entryState` must catch the previous slice's `exitState` verbatim (the previous slice's ending action is the next slice's opening frame); scene changes require `cut` or `reanchor`; chain depth ≤3, beyond that re-open from the masters.
6. **Size, camera, and shot language**: match each shot to the story, never reuse one recipe; each slice carries one line of shot language (size tier / camera position / move / composition / edit relation, ≤80 chars) answering "why shoot it this way".

## Stage 3 · AI generation

```bash
python {baseDir}/scripts/drama_studio.py compile-slices <project>-storyboard.json --assets <project>-assets.json --scenes <project>-scenes.json --out <project>-slices.md
```

Compiled output = fixed template header + `@UUID` character/scene lines + size/camera + shot language + visual content (setting + 3-5 action units) + verbatim `{character (emotion): line}` blocks; a blank template is appended at the end. **The template header is verbatim-immutable; field order never moves.**

Generation and acceptance (details in `references/en/stage-3-generation.md`):

1. **Preview-confirm**: before submitting, output a readable preview (model/entry, duration, resolution, full prompt, reference files and their roles, estimated cost, candidate and retry caps); any field change that alters picture or cost voids the confirmation.
2. **Evidence-based acceptance**: download the real footage, extract frames (head / 25% / 50% / 75% / tail), slow-mo the contact points, transcribe and listen to any audio. Four gates: **story / identity & style / physics & continuity / sound**; any P0 failure blocks `accepted`.
3. **Five repair verdicts**: keep / fix in post / edit instead of regenerate / re-roll with a new seed (≤2-3 times) / rewrite (same defect in ≥2 candidates). One variable per retry; if the attempt budget is half spent with no progress, switch strategy.
4. **State update**: after acceptance, set `status` to `accepted` and write the actually observed ending state back into `exitState` — **observed state overrides planned state**; subsequent slices continue from the observed state, not the plan.

## Quality gates at a glance

| Stage | Gates | Representative gates |
|---|---|---|
| Assets `validate-assets` | 10 | `reference-image` (four-view/plate prompt + image + 16:9) / `sheet-fresh` (fingerprint not stale) / `scene-objects` (layered object list) / `scene-no-text` (no readable text) / `name-free` / `voice-lock` |
| Storyboard `validate-storyboard` | 18 | `slice-seconds` / `dialogue-chars` / `action-units` / `cut-point` / `continuity` / `chain-depth` / `dialogue-coverage` (verbatim dialogue) / `shot-language` / `shot-variety` |

Full ids, thresholds, and diagnostic wording in `references/en/quality-gates.md`. What gates cannot check (looks, angles, framing, performance) is checked **with your eyes on the image** — never pretend a gate covers it.

## Continuity model (quick reference)

- Every slice has `entryState` / `exitState`; `chain` = the previous slice's tail frame is this slice's head frame.
- Slice status: `planned → generated → reviewed → accepted | repair | rejected`; `rejected` never enters canon and cannot be a continuation source.
- Chain depth defaults to ≤3 (`maxChainDepth`); after a scene change, wardrobe change, detected drift, or two consecutive long slices, `reanchor` from the character/scene masters.
- A good seam preserves at least two of: motion / direction / shape / eyeline / sound / light.

## Fast lanes

- **Slice prompts only**: script in hand → parse-script → (if asset UUIDs already exist, straight to) seed-storyboard → fill slices → validate → compile. Skips the wait for images, but the `reference-image` gate still flags the risk.
- **Diagnosis only**: run the validate family; output defects; touch no slices.
- **Fix one shot**: change only that slice entry; re-run validate + compile.

## Command reference

```
parse-script <script.md> [--title T] [--out scenes.json]    script → scenes.json
seed-assets <scenes.json> [--out assets.json]               asset skeleton
build-sheets <assets.json> [--apply]                        assemble character four-view prompts and stamp fingerprints
uuid-new [--count N] [names...]                             mint UUIDs
validate-assets <assets.json> [--scenes scenes.json]        10 asset gates
seed-storyboard <scenes.json> [--aspect 9:16] [--out sb.json] storyboard skeleton + slicing plan
validate-storyboard <sb.json> --scenes S --assets A         18 storyboard gates (core)
compile-slices <sb.json> --assets A [--scenes S] [--out slices.md]  compile (refused while gates fail)
render <sb.json> [--assets A] [--scenes S] [--html|--md] [--out F]  report
slug <name>                                                 safe filename
```

All commands print to stdout by default (shell-redirect to persist); `--out` writes a file directly. Script paths are always written as `{baseDir}/scripts/drama_studio.py`; this skill is self-contained and copyable on its own.

## Self-test and examples

```bash
python {baseDir}/scripts/selftest.py     # 106 assertions, no model calls, no quota, ~1 second
```

`examples/三打白骨精-*` is a complete worked sample (script → scenes → assets → storyboard → slices → report) and doubles as the self-test fixture. After changing any script, run the self-test first.
