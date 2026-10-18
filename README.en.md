<div align="center">

# drama-studio · Short-Drama Studio

**Turn a scene-based script into a production pack of 15-second slice prompts, ready to feed an AI video model.**

[![Version](https://img.shields.io/badge/version-1.0.0-6D5DF6?style=flat-square&labelColor=1E1B2E)](#)
[![Quality gates](https://img.shields.io/badge/gates-26-8B7CF6?style=flat-square&labelColor=1E1B2E)](#hard-constraints-enforced-by-code)
[![Self-test](https://img.shields.io/badge/selftest-104%20assertions-22C55E?style=flat-square&labelColor=1E1B2E)](#install-as-an-agent-skill)
[![License](https://img.shields.io/badge/license-MIT-6B7280?style=flat-square&labelColor=1E1B2E)](LICENSE)

[Start here](#start-here) · [Three stages](#why-these-three-stages) · [Hard constraints](#hard-constraints-enforced-by-code) · [Quick start](#one-minute-quick-start) · [Install](#install-as-an-agent-skill)

English · [中文](README.md)

</div>

Updated: **2026-10-18** · **v1.0.0** · Chinese is the primary documentation; this file mirrors [`README.md`](README.md), [`SKILL.en.md`](SKILL.en.md), and [`references/en/`](references/en/).

One pipeline, three stages, every step guarded by code-level quality gates:

```
scene script ──▶ assets (character four-views / scene plates + @UUID) ──▶ storyboard (15s slices + shot language + continuity chain) ──▶ generation (fixed-template prompts + four-gate acceptance)
```

Not a prompt collection — a stateful, verifiable, repairable production line. Not bound to any platform, API, or model: Dreamina, Seedance, or any other entry point works; execution stays in the user's hands.

<a id="start-here"></a>

## Start here

| You are | Open first |
|---|---|
| New here | This page → [Quick start](#one-minute-quick-start) → the complete `examples/青叶大学-*` sample |
| Agent integrator | [`SKILL.md`](SKILL.md) (Chinese) / [`SKILL.en.md`](SKILL.en.md) (English) — the three-stage workflow and command reference |
| Changing slicing rules | [`references/stage-2-storyboard.md`](references/stage-2-storyboard.md) — the six slicing laws + shot language |
| Changing asset output | [`references/stage-1-assets.md`](references/stage-1-assets.md) — character four-views, layered scene objects |
| Changing prompt compilation | [`references/stage-3-generation.md`](references/stage-3-generation.md) — template anatomy, four acceptance gates, five repair verdicts |
| Debugging a failing gate | [`references/quality-gates.md`](references/quality-gates.md) — all 26 gates and their diagnostic messages |

## Why these three stages

| Stage | Question it answers | Output |
|---|---|---|
| 1 Assets | Who is on screen, where are we, what is in their hands? | `assets.json`: appearance/costume prompts + layered object lists + UUIDs + reference-image status |
| 2 Storyboard | What happens in these 15 seconds, who stands where, how does the camera speak, which lines are said? | `storyboard.json`: slices + shot language + continuity chain |
| 3 Generation | What does the platform-facing prompt look like, how is the take verified, how is a failure repaired? | `slices.md`: copy-paste-ready slice prompts |

<a id="hard-constraints-enforced-by-code"></a>

## Hard constraints (all enforced by quality gates)

- Each slice is exactly **15 seconds**;
- Each slice carries **25-35 Chinese characters** of dialogue (max 40 for intense confrontation), **verbatim** from the script — not added, not dropped, not reworded;
- Each slice holds **3-5 effective action units**; complex conflicts must be split;
- Cuts land only on: end of a line / entrance / exit / major action turn / emotional pause;
- **The previous slice's ending action is the next slice's opening frame** (hard-checked by the `continuity` gate);
- Each slice carries one line of **shot language** (size tier / camera position / move / composition / edit relation, ≤80 chars);
- Chain depth ≤3; beyond that, re-anchor from the character/scene masters;
- Characters and scenes are always bound via `@UUID` references; text carries only the increment;
- The template header is verbatim-immutable; field order never moves.

<a id="one-minute-quick-start"></a>

## One-minute quick start

```bash
# 1. Parse the script (strict format, see references/script-format.md)
python scripts/drama_studio.py parse-script project-script.md --title Project --out project-scenes.json

# 2. Seed the asset registry, fill it in, then validate (a reference image must exist first)
python scripts/drama_studio.py seed-assets project-scenes.json --out project-assets.json
python scripts/drama_studio.py uuid-new Rinsheng Takashi Kaita
python scripts/drama_studio.py validate-assets project-assets.json --scenes project-scenes.json
# Characters: stylist prompt fills appearance/costume → build-sheets assembles the four-view prompt → generate & upload
python scripts/drama_studio.py build-sheets project-assets.json --apply
# Scenes: art-director prompt fills the layered object list → hand-write the plate sheetPrompt (with the no-text clause)

# 3. Storyboard: fill slices per references/stage-2-storyboard.md, validate until every gate passes
python scripts/drama_studio.py seed-storyboard project-scenes.json --aspect 9:16 --out project-storyboard.json
python scripts/drama_studio.py validate-storyboard project-storyboard.json --scenes project-scenes.json --assets project-assets.json

# 4. Compile slice prompts (compilation is refused while any gate fails)
python scripts/drama_studio.py compile-slices project-storyboard.json --assets project-assets.json --scenes project-scenes.json --out project-slices.md
```

`examples/青叶大学-*` is a complete worked sample (script → assets → 5 slices → slices.md → report). Copying from it is the fastest way in.

## A compiled slice looks like this

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

(The slice prompt template is Chinese-native by design — it is the working language of the target platforms. See [`assets/templates/slice-prompt.md`](assets/templates/slice-prompt.md).)

<a id="install-as-an-agent-skill"></a>

## Install as an Agent Skill

```bash
# Claude Code
cp -r drama-studio ~/.claude/skills/
# Codex / any SKILL.md-compatible client: copy into its skills directory, or let the agent read SKILL.md directly
```

Self-contained and copyable: Python ≥3.8 standard library only, no model calls, no quota, fully offline self-test.

```bash
python scripts/selftest.py   # 104 assertions (including bilingual-mirror consistency), ~1 second
```

## Directory

```
drama-studio/
├── SKILL.md                 Main entry the agent reads (Chinese)
├── SKILL.en.md              English mirror
├── README.md                This document's source (Chinese)
├── README.en.md             This document
├── scripts/
│   ├── drama_studio.py      Deterministic tooling (parse / seed / validate / compile / render)
│   └── selftest.py          Self-test (104 assertions, no model calls)
├── references/              Chinese references
│   ├── script-format.md         Input script format spec
│   ├── stage-1-assets.md        Assets stage: four-views, layered objects, UUID registry
│   ├── stage-2-storyboard.md    Storyboard stage: six slicing laws and data model
│   ├── stage-3-generation.md    Generation stage: compilation, four gates, five verdicts
│   ├── quality-gates.md         All 26 quality gates and design principles
│   └── en/                      English mirrors (one-to-one)
├── assets/templates/       Prompt templates and intake sheets (Chinese-native: the prompts themselves ship in Chinese)
│   ├── character-extract.md      Character extraction prompt (stylist) + four-view prefix
│   ├── scene-extract.md          Scene extraction prompt (art director) + plate style
│   ├── asset-intake.md           Asset registry (field dictionary + workflow)
│   └── production-brief.md       Production brief
└── examples/                    Complete Aobaga University sample (doubles as the self-test fixture)
```

> Language convention: slice prompts, extraction prompts, and sample data stay Chinese-native (that is their working language); SKILL / README / references ship bilingual, with `references/en/` mirroring the Chinese files one-to-one — the self-test checks for missing mirrors.

## What it learned from whom

- **shuohao-skills**: JSON as single source of truth + scripts for validation and rendering; `seed` commands for deterministic upstream transfer; code-level quality gates with per-item diagnostics; verbatim-dialogue and coverage gates.
- **dramake**: three-state lifecycle (`generated ≠ accepted`, observed state overrides planned); generation-block event-load budgeting; four acceptance gates with P0 rulings; one-variable retries + attempt budgets; reference roles and must-not-transfer.
- **seedance-2.0-os**: prompts are compiled, not written; identity fidelity offloaded to reference images; anti-slop (no empty evaluators); retake economics (five verdicts + shot log); chain-depth caps and re-anchoring; bilingual documentation layout (English mirrors + badges/anchor navigation).
- **Your battle-tested patterns**: the 15-second slice prompt (fixed template header, UUID references, 25-35 characters, 3-5 action units, cut rules, previous-slice ending = next-slice opening) is preserved verbatim and encoded as gates; asset output uses your two proven pipelines — characters = stylist "appearance + costume" two-part prompt assembled into a white-background four-view sheet (16:9), scenes = art-director layered object list (core/environment/implied) written into a plate prompt (with the no-readable-text clause).

## License

[MIT](LICENSE)
