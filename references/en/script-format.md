# Input Script Format (Scene-Based Script)

This skill's entry point is a **line-oriented scene script**. `parse-script` is strict: unrecognized lines abort immediately with a line number — no guessing, no silent skipping.

## Line types

| Line | Syntax | Notes |
|---|---|---|
| Scene header | `scene-id location time int/ext` | Time and int/ext are optional: `3-2 青叶大学冰场理疗室 日 内`; the location may contain spaces (non-greedy up to the last time token) |
| Cast | `人物：name、name、name` | Separated by 、, comma, or space; must be the scene's first content line |
| Action | `△action description` | May span multiple lines; `※` is equivalent |
| Close-up | `特写：close-up content` | Becomes an action beat with `closeup: true` |
| Dialogue | `character (emotion): line` | Emotion is optional: `character: line`; character names ≤12 chars, no colons or brackets |
| Comment | starts with `#` | Skipped |

```text
3-2 青叶大学冰场理疗室 日 内
人物：凛生、拓真、开太

△凛生坐在理疗床上，右腿做了专业固定，膝盖上敷着冰袋，无法随意活动。
拓真（眼神充满占有欲）：听说裁判长前几天为难你了？
凛生（冷漠）：不关你的事。
特写：冰袋表面的水珠顺着凛生的指尖滑落。
```

## Parser output: scenes.json

```jsonc
{
  "title": "青叶大学", "lang": "zh", "source": "青叶大学-script.md",
  "scenes": [{
    "id": "3-2", "location": "青叶大学冰场理疗室", "time": "日", "intExt": "内",
    "characters": ["凛生", "拓真", "开太"],
    "beats": [
      { "no": 1, "type": "action", "text": "凛生坐在理疗床上……", "closeup": false },
      { "no": 3, "type": "dialogue", "speaker": "拓真", "emotion": "眼神充满占有欲", "line": "听说裁判长前几天为难你了？" }
    ]
  }]
}
```

- `beats[].no` is sequential within the scene; actions and dialogue keep the original order.
- Dialogue is preserved **verbatim** (punctuation included) — the `dialogue-coverage` gate compares against it.
- Parsing sanitizes: the `△` symbol exists only in the source; it never reaches a downstream artifact.

## Fixing format errors

- `Unrecognized`: rewrite the line into one of the five line types above; a forgotten `△` on an action line is the most common cause.
- `Duplicate scene-id` / `content before scene header`: check the scene ids and the position of the `人物：` line.
- The user has a novel or synopsis instead of a scene script: rewrite it into this format before entering the pipeline — **do not bypass the parser**; every downstream gate's traceability rests on scenes.json.
