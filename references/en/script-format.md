# Input Script Format (Scene-Based Script)

This skill's entry point is a **line-oriented scene script**. `parse-script` is strict: unrecognized lines abort immediately with a line number — no guessing, no silent skipping.

## Line types

| Line | Syntax | Notes |
|---|---|---|
| Scene header | `scene-id location time int/ext` | Time and int/ext are optional: `1-2 白虎岭乱石坡 日 外`; the location may contain spaces (non-greedy up to the last time token) |
| Cast | `人物：name、name、name` | Separated by 、, comma, or space; must be the scene's first content line |
| Action | `△action description` | May span multiple lines; `※` is equivalent |
| Close-up | `特写：close-up content` | Becomes an action beat with `closeup: true` |
| Dialogue | `character (emotion): line` | Emotion is optional: `character: line`; character names ≤12 chars, no colons or brackets |
| Comment | starts with `#` | Skipped |

```text
1-2 白虎岭乱石坡 日 外
人物：唐僧、猪八戒、沙僧、村姑

△雾散了一半，乱石坡下传来环佩声。一个青衣女子提着青砂罐、拎着绿磁瓶，从坡下一步步上来。
猪八戒（眼睛发直）：女菩萨，青罐里提的是什么？
村姑（福身一礼）：长老，这是给田中丈夫送的斋饭。
特写：罐盖翻开，长蛆与蛤蟆从斋饭里涌出来。
```

## Parser output: scenes.json

```jsonc
{
  "title": "三打白骨精", "lang": "zh", "source": "三打白骨精-script.md",
  "scenes": [{
    "id": "1-2", "location": "白虎岭乱石坡", "time": "日", "intExt": "外",
    "characters": ["孙悟空", "唐僧", "猪八戒", "沙僧", "村姑"],
    "beats": [
      { "no": 1, "type": "action", "text": "雾散了一半，乱石坡下传来环佩声……", "closeup": false },
      { "no": 2, "type": "dialogue", "speaker": "猪八戒", "emotion": "眼睛发直", "line": "女菩萨，青罐里提的是什么？" }
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
