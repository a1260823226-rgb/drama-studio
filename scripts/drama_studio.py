#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""drama-studio —— 短剧工坊的确定性工具。

三阶段：剧本解析 → 资产注册 → 分镜切片 → AI 成片编译。
设计哲学（融合自 shuohao-skills / dramake / seedance-2.0-os）：
  - 模型只写 JSON 的设计字段，脚本做其余一切（解析、校验、编译、渲染）；
  - 质量门全部是代码，不是清单：违规逐条报病灶，exit 1，改完重跑直到通过；
  - 上游事实不让模型重新想一遍：parse-script / seed-assets / seed-storyboard 做确定性搬运；
  - 零依赖：只用 Python 标准库，不调用任何模型，不花任何额度。

用法：python drama_studio.py <命令> [参数]  —— 详见 USAGE。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import uuid as uuidlib
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
TEMPLATE_PATH = BASE / "assets" / "templates" / "slice-prompt.md"

USAGE = """drama_studio.py — drama-studio skill 的确定性工具（短剧工坊）
  parse-script <script.md> [--title 剧名] [--out scenes.json]    解析分场剧本为 scenes.json
  seed-assets <scenes.json> [--out assets.json]                  从剧本种子化资产骨架
  build-sheets <assets.json> [--apply]                           组装人物四视图生图提示词
  uuid-new [--count N] [名字 ...]                                生成资产 UUID
  validate-assets <assets.json> [--scenes scenes.json]           资产质量门（10 道）
  seed-storyboard <scenes.json> [--assets assets.json] [--aspect 9:16] [--out storyboard.json]
                                                                 分镜骨架 + 切分计划
  validate-storyboard <sb.json> --scenes <scenes.json> --assets <assets.json>
                                                                 分镜质量门（核心）
  compile-slices <sb.json> --assets <assets.json> [--scenes scenes.json] [--out slices.md]
                                                                 编译 15s 切片 Prompt（门不过则拒绝编译）
  render <sb.json> [--assets assets.json] [--scenes scenes.json] [--html|--md] [--out 文件]
  slug <名字>                                                     安全文件名
所有命令默认打印到 stdout，可 shell 重定向落盘。"""

# ---------------------------------------------------------------- 常量

DEFAULT_PARAMS = {
    "sliceSeconds": 15,
    "minDialogueChars": 25,
    "maxDialogueChars": 35,
    "maxDialogueCharsIntense": 40,
    "minActionUnits": 3,
    "maxActionUnits": 5,
    "maxChainDepth": 3,
    "charsPerSecond": 4.5,
    "actionSeconds": 2.5,
    "durationTolerance": 0.30,
    "fieldBrackets": False,
}

CUT_POINTS = ["scene-start", "line-end", "entrance", "exit", "action-turn", "emotional-pause"]
CUT_POINT_ZH = {
    "scene-start": "场始",
    "line-end": "单句台词结束",
    "entrance": "人物入场",
    "exit": "人物离场",
    "action-turn": "重大动作转折",
    "emotional-pause": "情绪停顿",
}
CONTINUITY = ["scene-start", "chain", "cut", "reanchor"]
CONTINUITY_ZH = {
    "scene-start": "场始开镜",
    "chain": "链式衔接（上片尾帧即本片首帧）",
    "cut": "刻意剪辑（不承诺帧连续）",
    "reanchor": "重新锚定（从角色/场景母版开镜，重置链深度）",
}
RECOMMENDED_SIZES = ["全景", "中景", "中近景", "近景", "特写"]
RECOMMENDED_CAMERAS = ["固定镜头", "推镜", "拉镜", "摇镜", "横移", "跟拍", "环绕", "手持", "局部特写切换"]
VO_NAMES = {"VO", "旁白", "画外音"}
# 镜头语言词表（景别阶梯 / 拍摄方式 / 构图角度 / 组接方式）——用于「镜头语言是否写虚了」的提示
SHOT_VOCAB = [
    "极远景", "大远景", "远景", "大全景", "全景", "小全景", "中景", "中近景", "半身景",
    "近景", "特写", "大特写",
    "推", "拉", "摇", "移", "跟", "升", "降", "俯拍", "仰拍", "甩", "悬", "空镜",
    "长镜头", "反打", "变焦", "主观",
    "三分线", "前景", "后景", "景深", "机位", "平视", "构图", "画中画", "留白", "顶格",
    "淡入", "淡出", "叠化", "划", "入画", "出画", "定格", "闪回", "蒙太奇",
    "交叉剪辑", "平行剪辑", "切换", "跳切", "切出", "插入",
]
SHOT_LANGUAGE_MAX_CHARS = 80
IMAGE_OK_STATUS = {"linked", "accepted"}
UUID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
DELTA_RE = re.compile(r"[△※]")
# 资产产出范式：人物 = 白底四视图（16:9）；场景 = 分层物件清单 + 空镜（16:9）
FOUR_VIEW_PREFIX = (
    "AI生图提示词的前缀。帮我根据要求生成白底人物四视图，图片尺寸为16:9，四视图从左到右依次为"
    "镜头拍人物脸部特写，人物正面全身站立图，人物侧面全身站立图，人物背面全身站立图"
    "生成效果：真实质感，人物肌肤与毛孔贴近现实不油光，人物衣物细节拉满："
)
SHEET_RATIO = "16:9"
SCENE_OBJECT_LEVELS = ("核心", "环境", "隐含")
NO_TEXT_MARKERS = ("不出现任何可读文字", "无可读文字", "无任何可读文字", "无文字",
                   "no readable text", "no text")

SCENE_RE = re.compile(r"^\s*(\d+(?:-\d+)*)\s+(.+?)\s+(?:([日夜间昏晚晨])\s+)?([内外]{1,2})\s*$")
CAST_RE = re.compile(r"^\s*人物[:：]\s*(.+?)\s*$")
ACTION_RE = re.compile(r"^\s*[△※]\s*(.+?)\s*$")
CLOSEUP_RE = re.compile(r"^\s*特写[:：]\s*(.+?)\s*$")
DIALOGUE_RE = re.compile(r"^\s*([^：:（）()]{1,12})（([^（）()]+)）\s*[:：]\s*(.*?)\s*$")
DIALOGUE_PLAIN_RE = re.compile(r"^\s*([^：:（）()]{1,12})\s*[:：]\s*(.*?)\s*$")


# ---------------------------------------------------------------- 基础工具

def norm(s: str) -> str:
    """比较用归一化：只留字母数字（丢空白与标点）。"""
    return "".join(ch for ch in (s or "") if ch.isalnum())


def han(s: str) -> int:
    """汉字数（台词字数门按汉字计，标点不计）。"""
    return sum(1 for ch in (s or "") if "\u4e00" <= ch <= "\u9fff")


def read_json(path: str):
    p = Path(path)
    if not p.exists():
        raise SystemExit(f"文件不存在：{path}")
    return json.loads(p.read_text(encoding="utf-8"))


def write_json(obj, path: str):
    Path(path).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def dump(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2)


def slug(name: str) -> str:
    s = re.sub(r"[^\w\u4e00-\u9fff]+", "-", (name or "").strip())
    return s.strip("-") or "untitled"


def gate(gates, gid, label, ok, detail=""):
    gates.append({"id": gid, "label": label, "ok": bool(ok), "detail": detail})
    return gates


def print_gates(gates, warnings, title="质量门"):
    for g in gates:
        mark = "✓" if g["ok"] else "✗"
        line = f"{mark} {g['id']} — {g['label']}"
        if not g["ok"] and g["detail"]:
            line += f" — {g['detail']}"
        print(line)
    for w in warnings:
        print(f"⚠ {w}")
    bad = [g for g in gates if not g["ok"]]
    print(f"\n{title}：{len(gates) - len(bad)} 通过，{len(bad)} 未过")
    return 1 if bad else 0


def params_of(sb: dict) -> dict:
    p = dict(DEFAULT_PARAMS)
    p.update(sb.get("params") or {})
    return p


# ---------------------------------------------------------------- 剧本解析

def parse_script(text: str, title: str = "") -> dict:
    scenes, problems = [], []
    cur = None
    seen_ids = set()
    for lineno, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = SCENE_RE.match(line)
        if m and not line.startswith(("△", "※")):
            sid, loc, tm, ie = m.group(1), m.group(2).strip(), m.group(3) or "", m.group(4)
            if sid in seen_ids:
                problems.append(f"第 {lineno} 行：场号 {sid} 重复")
            seen_ids.add(sid)
            cur = {"id": sid, "location": loc, "time": tm, "intExt": ie,
                   "characters": [], "beats": []}
            scenes.append(cur)
            continue
        if cur is None:
            problems.append(f"第 {lineno} 行：场头之前出现内容：「{line[:24]}」")
            continue
        m = CAST_RE.match(line)
        if m:
            names = re.split(r"[、，,\s]+", m.group(1))
            cur["characters"] = [n for n in (x.strip() for x in names) if n]
            continue
        m = CLOSEUP_RE.match(line)
        if m:
            cur["beats"].append({"no": len(cur["beats"]) + 1, "type": "action",
                                 "text": m.group(1), "closeup": True})
            continue
        m = ACTION_RE.match(line)
        if m:
            cur["beats"].append({"no": len(cur["beats"]) + 1, "type": "action",
                                 "text": m.group(1), "closeup": False})
            continue
        m = DIALOGUE_RE.match(line)
        if m:
            cur["beats"].append({"no": len(cur["beats"]) + 1, "type": "dialogue",
                                 "speaker": m.group(1).strip(), "emotion": m.group(2).strip(),
                                 "line": m.group(3)})
            continue
        m = DIALOGUE_PLAIN_RE.match(line)
        if m:
            cur["beats"].append({"no": len(cur["beats"]) + 1, "type": "dialogue",
                                 "speaker": m.group(1).strip(), "emotion": "",
                                 "line": m.group(2)})
            continue
        problems.append(f"第 {lineno} 行：无法识别（应为 场头/人物:/△动作/角色（情绪）：台词/特写:）：「{line[:24]}」")
    if not scenes:
        problems.append("没有解析到任何场次")
    if problems:
        raise SystemExit("剧本解析失败：\n  " + "\n  ".join(problems))
    return {"title": title, "lang": "zh", "scenes": scenes}


def scene_dialogue(scene: dict):
    return [b for b in scene["beats"] if b["type"] == "dialogue"]


def scene_dialogue_text(scene: dict) -> str:
    return norm("".join(b["line"] for b in scene_dialogue(scene)))


def scene_estimate_seconds(scene: dict, p: dict) -> float:
    dlg = sum(han(b["line"]) for b in scene_dialogue(scene))
    acts = sum(1 for b in scene["beats"] if b["type"] == "action")
    return dlg / p["charsPerSecond"] + acts * p["actionSeconds"]


# ---------------------------------------------------------------- 资产

def prompt_sha(s: str) -> str:
    """提示词指纹：出了图之后改描述，对不上即过期。"""
    return hashlib.sha256((s or "").encode("utf-8")).hexdigest()[:12]


def seed_assets(scenes: dict) -> dict:
    chars, char_idx = [], {}
    for sc in scenes["scenes"]:
        for name in sc["characters"]:
            if name not in char_idx:
                char_idx[name] = len(chars)
                chars.append({
                    "id": f"C{len(chars):02d}", "name": name, "uuid": "",
                    "importance": "supporting", "appearsIn": [], "speaking": False,
                    "appearance": "",     # 内容一：五官及外貌（造型师提示词产出）
                    "costume": "",        # 内容二：服饰（造型师提示词产出）
                    "sheetPrompt": "",    # 最终生图提示词 = 四视图前缀 + 外貌 + 服饰
                    "outfits": [],        # 换装变体：[{id,label,costume,sheetPrompt,status,generatedFrom}]
                    "recognition": "",
                    "generatedFrom": "",  # 出图时 sheetPrompt 的指纹；对不上即过期
                    "images": [{"view": "four-view", "ratio": SHEET_RATIO, "status": "pending",
                                "note": "白底四视图：脸部特写+正/侧/背面全身"}],
                    "voice": {"timbre": "", "pitch": "", "pace": "", "accent": ""},
                })
            c = chars[char_idx[name]]
            if sc["id"] not in c["appearsIn"]:
                c["appearsIn"].append(sc["id"])
            if any(b["type"] == "dialogue" and b["speaker"] == name for b in sc["beats"]):
                c["speaking"] = True
    if chars:
        chars[0]["importance"] = "protagonist"
    scene_assets = [{
        "id": f"S{i:02d}", "name": sc["location"], "sceneRef": sc["id"], "uuid": "",
        "summary": "",
        "objects": [],           # 分层物件清单：核心 / 环境 / 隐含
        "atmosphere": "",        # 场景整体氛围总结
        "sheetPrompt": "",       # 空镜生图提示词
        "generatedFrom": "",
        "images": [{"view": "sheet", "ratio": SHEET_RATIO, "status": "pending",
                    "note": "空镜设定图：无人、无可读文字"}],
    } for i, sc in enumerate(scenes["scenes"], 1)]
    return {"title": scenes.get("title") or "", "lang": "zh",
            "characters": chars, "scenes": scene_assets, "props": []}


def find_char(assets: dict, name: str):
    for c in assets.get("characters", []):
        if c.get("name") == name:
            return c
    return None


def find_scene_asset(assets: dict, scene_id: str):
    for s in assets.get("scenes", []):
        if s.get("sceneRef") == scene_id or s.get("id") == scene_id:
            return s
    return None


def validate_assets(assets: dict, scenes: dict | None):
    gates, warnings = [], []
    chars = assets.get("characters") or []
    scns = assets.get("scenes") or []
    props = assets.get("props") or []
    gate(gates, "structure", "资产册结构完整（角色/场景/道具三类）",
         bool(chars) and all(c.get("name") for c in chars) and all(s.get("name") for s in scns),
         "角色或场景缺少 name" if (chars and not all(c.get("name") for c in chars)) else "")
    bad_uuid = [c["name"] for c in chars if not UUID_RE.match(c.get("uuid") or "")]
    bad_uuid += [s["name"] for s in scns if not UUID_RE.match(s.get("uuid") or "")]
    gate(gates, "uuid-format", "每个角色/场景都有合法 UUID",
         not bad_uuid, "缺 UUID 或格式不对：" + "、".join(bad_uuid) if bad_uuid else "")
    no_sheet_c = [c["name"] for c in chars if not (c.get("sheetPrompt") or "").strip()]
    no_sheet_s = [s["name"] for s in scns if not (s.get("sheetPrompt") or "").strip()]
    no_img_c = [c["name"] for c in chars
                if not any((im.get("status") in IMAGE_OK_STATUS) for im in c.get("images", []))]
    no_img_s = [s["name"] for s in scns
                if not any((im.get("status") in IMAGE_OK_STATUS) for im in s.get("images", []))]
    bad_ratio = [c["name"] for c in chars
                 if any(im.get("status") in IMAGE_OK_STATUS and im.get("ratio") != SHEET_RATIO
                        for im in c.get("images", []))]
    bad_ratio += [s["name"] for s in scns
                  if any(im.get("status") in IMAGE_OK_STATUS and im.get("ratio") != SHEET_RATIO
                         for im in s.get("images", []))]
    gate(gates, "reference-image",
         "每个角色/场景都有生图提示词，且参考图已上传或已验收（16:9）",
         not (no_sheet_c or no_sheet_s or no_img_c or no_img_s or bad_ratio),
         ("缺提示词：" + "、".join(no_sheet_c + no_sheet_s)) if (no_sheet_c or no_sheet_s)
         else (("缺图：" + "、".join(no_img_c + no_img_s) + "（未出图前不得编译切片，模型会当场发明一张脸）")
               if (no_img_c or no_img_s)
               else (("比例不是 16:9：" + "、".join(bad_ratio)) if bad_ratio else "")))
    name_leak = []
    for c in chars:
        for field in ("appearance", "costume", "sheetPrompt"):
            txt = c.get(field) or ""
            if txt and c["name"] in txt:
                name_leak.append(f"{c['name']}.{field}")
    gate(gates, "name-free", "出图提示词不出现角色名",
         not name_leak, "提示词含角色名：" + "、".join(name_leak) if name_leak else "")
    stale, no_fp = [], []
    for c in chars:
        items = [(c.get("sheetPrompt"), c.get("generatedFrom"), c["name"])]
        for o in c.get("outfits") or []:
            items.append((o.get("sheetPrompt"), o.get("generatedFrom"),
                          f"{c['name']}/{o.get('label') or o.get('id') or '?'}"))
        for prompt, fp, label in items:
            if not prompt:
                continue
            if not fp:
                no_fp.append(label)
            elif prompt_sha(prompt) != fp:
                stale.append(label)
    for s in scns:
        if s.get("sheetPrompt") and not s.get("generatedFrom"):
            no_fp.append(s["name"])
        elif s.get("sheetPrompt") and prompt_sha(s["sheetPrompt"]) != s.get("generatedFrom"):
            stale.append(s["name"])
    for label in no_fp:
        warnings.append(f"{label} 已出图但未记录 generatedFrom，描述改动无法自动检出")
    gate(gates, "sheet-fresh", "参考图未过期（generatedFrom 与当前提示词一致）",
         not stale, "描述已改但图未重出：" + "、".join(stale) if stale else "")
    bad_obj = []
    for s in scns:
        objs = s.get("objects") or []
        probs = []
        if not any(o.get("level") == "核心" for o in objs):
            probs.append("缺核心物件")
        if not any(o.get("level") == "环境" for o in objs):
            probs.append("缺环境物件")
        bad_level = [o.get("name") or "?" for o in objs if o.get("level") not in SCENE_OBJECT_LEVELS]
        if bad_level:
            probs.append("层级非法：" + "、".join(bad_level))
        incomplete = [o.get("name") or "?" for o in objs if not (o.get("role") and o.get("visual"))]
        if incomplete:
            probs.append("缺画面作用/视觉特征：" + "、".join(incomplete))
        if probs:
            bad_obj.append(f"{s['name']}（{'；'.join(probs)}）")
    gate(gates, "scene-objects",
         "每个场景有分层物件清单（核心+环境必须有，隐含可选），每件有画面作用与视觉特征",
         not bad_obj, "；".join(bad_obj))
    no_text = [s["name"] for s in scns
               if not any(m in (s.get("sheetPrompt") or "") for m in NO_TEXT_MARKERS)]
    gate(gates, "scene-no-text", "场景空镜提示词声明「不出现可读文字」（文字后期叠加）",
         not no_text, "缺无可读文字约束：" + "、".join(no_text) if no_text else "")
    if scenes:
        speaking = {b["speaker"] for sc in scenes["scenes"] for b in scene_dialogue(sc)}
        no_voice = [c["name"] for c in chars if c["name"] in speaking
                    and not all((c.get("voice") or {}).get(k) for k in ("timbre", "pitch", "pace"))]
        gate(gates, "voice-lock", "每个有台词的角色都锁了音色（音色/音高/语速）",
             not no_voice, "缺音色设定：" + "、".join(no_voice) if no_voice else "")
        scene_ids = {sc["id"] for sc in scenes["scenes"]}
        missing = [sid for sid in sorted(scene_ids) if find_scene_asset(assets, sid) is None]
        gate(gates, "scene-coverage", "剧本每个场次都有对应场景资产",
             not missing, "缺场景资产：" + "、".join(missing) if missing else "")
    else:
        gate(gates, "voice-lock", "每个有台词的角色都锁了音色（音色/音高/语速）", True,
             "未提供 scenes.json，本门跳过（视为通过）")
        gate(gates, "scene-coverage", "剧本每个场次都有对应场景资产", True,
             "未提供 scenes.json，本门跳过（视为通过）")
    bad_prop = [p["name"] for p in props if not (p.get("states") or [])]
    gate(gates, "prop-states", "每个叙事道具至少一个状态",
         not bad_prop, "道具缺状态：" + "、".join(bad_prop) if bad_prop else "")
    return gates, warnings


# ---------------------------------------------------------------- 分镜

def seed_storyboard(scenes: dict, assets: dict | None, aspect: str) -> dict:
    p = DEFAULT_PARAMS
    plans = []
    for sc in scenes["scenes"]:
        dlg = scene_dialogue(sc)
        est = scene_estimate_seconds(sc, p)
        plans.append({
            "sceneId": sc["id"], "location": sc["location"],
            "time": sc["time"], "intExt": sc["intExt"],
            "cast": sc["characters"],
            "dialogueLines": len(dlg),
            "dialogueChars": sum(han(b["line"]) for b in dlg),
            "actionBeats": sum(1 for b in sc["beats"] if b["type"] == "action"),
            "estimateSeconds": round(est, 1),
            "suggestSlices": max(1, -(-int(est) // p["sliceSeconds"])),
        })
    return {"title": scenes.get("title") or "", "lang": "zh", "aspectRatio": aspect,
            "params": dict(DEFAULT_PARAMS), "scenePlans": plans, "slices": []}


def slice_dialogue_chars(sl: dict) -> int:
    return sum(han(d.get("line") or "") for d in sl.get("dialogue") or [])


def validate_storyboard(sb: dict, scenes: dict, assets: dict):
    gates, warnings = [], []
    slices = sb.get("slices") or []
    p = params_of(sb)
    scene_by_id = {sc["id"]: sc for sc in scenes["scenes"]}

    gate(gates, "structure", "切片清单非空且字段齐全",
         bool(slices) and all(sl.get("id") and sl.get("sceneId") and sl.get("title")
                              and sl.get("size") and sl.get("camera") and sl.get("characters")
                              and sl.get("entryState") and sl.get("exitState")
                              and sl.get("continuity") for sl in slices),
         "有切片缺 id/sceneId/title/size/camera/characters/entryState/exitState/continuity")
    ids = [sl.get("id") for sl in slices]
    gate(gates, "slice-id", "切片 id 唯一", len(ids) == len(set(ids)),
         "重复 id：" + "、".join(sorted({i for i in ids if ids.count(i) > 1})) if len(ids) != len(set(ids)) else "")
    bad_sec = [sl["id"] for sl in slices if sl.get("seconds", p["sliceSeconds"]) != p["sliceSeconds"]]
    gate(gates, "slice-seconds", f"每个切片 {p['sliceSeconds']} 秒", not bad_sec,
         "时长不对：" + "、".join(bad_sec) if bad_sec else "")
    bad_units = [f"{sl['id']}({len(sl.get('actionUnits') or [])})" for sl in slices
                 if not (p["minActionUnits"] <= len(sl.get("actionUnits") or []) <= p["maxActionUnits"])]
    gate(gates, "action-units", f"每切片 {p['minActionUnits']}-{p['maxActionUnits']} 个有效动作单元",
         not bad_units, "动作单元数越界：" + "、".join(bad_units) if bad_units else "")
    bad_dlg, dlg_detail = [], []
    for sl in slices:
        n = slice_dialogue_chars(sl)
        if n == 0:
            continue
        cap = p["maxDialogueCharsIntense"] if sl.get("intense") else p["maxDialogueChars"]
        if not (p["minDialogueChars"] <= n <= cap):
            bad_dlg.append(sl["id"])
            dlg_detail.append(f"{sl['id']} {n} 字（区间 {p['minDialogueChars']}-{cap}）")
    gate(gates, "dialogue-chars", f"单切片台词 {p['minDialogueChars']}-{p['maxDialogueChars']} 汉字（激烈对峙 ≤{p['maxDialogueCharsIntense']}）",
         not bad_dlg, "；".join(dlg_detail))
    bad_cut = [sl["id"] for sl in slices if sl.get("cutPoint") not in CUT_POINTS]
    gate(gates, "cut-point", "断点类型合法（单句台词结束/入场/离场/动作转折/情绪停顿）",
         not bad_cut, "断点非法：" + "、".join(bad_cut) if bad_cut else "")
    delta = [sl["id"] for sl in slices
             if any(DELTA_RE.search(str(v)) for v in
                    [sl.get("setting") or "", " ".join(sl.get("actionUnits") or []),
                     " ".join(d.get("line") or "" for d in sl.get("dialogue") or [])])]
    gate(gates, "no-delta", "切片文本不带原始剧本 △/※ 标记", not delta,
         "仍含 △：" + "、".join(delta) if delta else "")
    bad_cast, bad_speaker, no_uuid = [], [], []
    for sl in slices:
        sc = scene_by_id.get(sl.get("sceneId"))
        if sc is None:
            continue
        for name in sl.get("characters") or []:
            if name not in sc["characters"]:
                bad_cast.append(f"{sl['id']}:{name}")
            c = find_char(assets, name)
            if c is None or not UUID_RE.match(c.get("uuid") or ""):
                no_uuid.append(f"{sl['id']}:{name}")
        sa = find_scene_asset(assets, sl.get("sceneId"))
        if sa is None or not UUID_RE.match(sa.get("uuid") or ""):
            no_uuid.append(f"{sl['id']}:场景{sl.get('sceneId')}")
        for d in sl.get("dialogue") or []:
            sp = d.get("speaker") or ""
            if sp not in VO_NAMES and sp not in (sl.get("characters") or []):
                bad_speaker.append(f"{sl['id']}:{sp}")
    gate(gates, "uuid-coverage", "切片引用的人物/场景都能在资产册解析到 UUID",
         not no_uuid, "无法解析 UUID：" + "、".join(no_uuid) if no_uuid else "")
    gate(gates, "cast-match", "切片人物不超出场次 cast", not bad_cast,
         "越界人物：" + "、".join(bad_cast) if bad_cast else "")
    gate(gates, "speaker-on-screen", "台词说话人在本切片画内（或显式 VO）",
         not bad_speaker, "说话人不在画内：" + "、".join(bad_speaker) if bad_speaker else "")
    empty_size = [sl["id"] for sl in slices if not (sl.get("size") or "").strip()]
    empty_cam = [sl["id"] for sl in slices if not (sl.get("camera") or "").strip()]
    gate(gates, "size-camera", "每个切片都写明景别与运镜", not empty_size and not empty_cam,
         "缺景别：" + "、".join(empty_size + empty_cam) if (empty_size or empty_cam) else "")
    no_lang = [sl["id"] for sl in slices if not (sl.get("shotLanguage") or "").strip()]
    long_lang = [f"{sl['id']}({len(sl.get('shotLanguage') or '')}字)" for sl in slices
                 if len(sl.get("shotLanguage") or "") > SHOT_LANGUAGE_MAX_CHARS]
    gate(gates, "shot-language", f"每个切片都有一句镜头语言（景别/机位/运镜/构图/组接），≤{SHOT_LANGUAGE_MAX_CHARS} 字",
         not no_lang and not long_lang,
         ("缺镜头语言：" + "、".join(no_lang)) if no_lang
         else ("超长：" + "、".join(long_lang) if long_lang else ""))
    for sl in slices:
        lang = sl.get("shotLanguage") or ""
        if lang and not any(term in lang for term in SHOT_VOCAB):
            warnings.append(f"{sl['id']} 的镜头语言里没有一个可执行术语（景别/机位/运镜/构图/组接），检查是否写虚了")
    for sl in slices:
        if sl.get("size") and sl["size"] not in RECOMMENDED_SIZES:
            warnings.append(f"{sl['id']} 景别「{sl['size']}」不在推荐词表（{'/'.join(RECOMMENDED_SIZES)}）")
        if sl.get("camera") and sl["camera"] not in RECOMMENDED_CAMERAS:
            warnings.append(f"{sl['id']} 运镜「{sl['camera']}」不在推荐词表（{'/'.join(RECOMMENDED_CAMERAS)}）")
    # 连续性
    cont_bad, boundary_bad, depth_bad, reanchor_bad = [], [], [], []
    depth = 0
    prev = None
    for sl in slices:
        c = sl.get("continuity")
        if c not in CONTINUITY:
            cont_bad.append(f"{sl['id']}:{c}")
        if c == "chain":
            depth += 1
            if prev is not None and norm(sl.get("entryState")) != norm(prev.get("exitState")):
                cont_bad.append(f"{sl['id']} 入场状态≠上一片出场状态")
            if prev is not None and prev.get("sceneId") != sl.get("sceneId"):
                boundary_bad.append(sl["id"])
        else:
            depth = 1
            if c == "reanchor" and not (sl.get("reanchorFrom") or []):
                reanchor_bad.append(sl["id"])
            if not (sl.get("entryState") or "").strip():
                cont_bad.append(f"{sl['id']} 非链式切片必须显式声明入场状态")
        if depth > p["maxChainDepth"]:
            depth_bad.append(sl["id"])
        prev = sl
    gate(gates, "continuity", "连续性合法：chain 片上片尾帧相接；cut/reanchor 显式声明入场状态",
         not cont_bad, "；".join(cont_bad) if cont_bad else "")
    gate(gates, "scene-boundary", "跨场不得链式衔接（场景边界从母版开镜）",
         not boundary_bad, "跨场仍 chain：" + "、".join(boundary_bad) if boundary_bad else "")
    gate(gates, "reanchor-from", "reanchor 切片必须列出重新锚定所用的资产",
         not reanchor_bad, "缺 reanchorFrom：" + "、".join(reanchor_bad) if reanchor_bad else "")
    gate(gates, "chain-depth", f"链式衔接深度 ≤ {p['maxChainDepth']}（超了必须 cut 或 reanchor）",
         not depth_bad, "链深度超限：" + "、".join(depth_bad) if depth_bad else "")
    # 台词逐字 + 覆盖（按场次拼接比对，允许长台词跨切片拆分）
    cov_bad = []
    for sc in scenes["scenes"]:
        want = scene_dialogue_text(sc)
        got = norm("".join(d.get("line") or "" for sl in slices
                           if sl.get("sceneId") == sc["id"] for d in sl.get("dialogue") or []))
        if want != got:
            cov_bad.append(f"场 {sc['id']}（剧本 {len(want)} 字 / 切片 {len(got)} 字）")
    gate(gates, "dialogue-coverage", "剧本台词逐字进入切片，不增不减不改（长台词可拆分，拼接须还原）",
         not cov_bad, "对不上：" + "；".join(cov_bad) if cov_bad else "")
    sig = {(sl.get("size"), sl.get("camera")) for sl in slices}
    gate(gates, "shot-variety", "景别/运镜不复用一套（按剧情逐镜匹配）",
         len(sig) > 1 or len(slices) <= 1, "全部切片景别运镜完全相同" if len(sig) == 1 and len(slices) > 1 else "")
    return gates, warnings


# ---------------------------------------------------------------- 编译

def compile_slices(sb: dict, assets: dict, scenes: dict | None) -> str:
    slices = sb.get("slices") or []
    p = params_of(sb)
    bracket = bool(p.get("fieldBrackets"))

    def field(name: str, value: str) -> str:
        return f"{name}：{'【' + value + '】' if bracket else value}。"

    # UUID 对照表
    used_chars, used_scenes = [], []
    for sl in slices:
        for name in sl.get("characters") or []:
            if name not in used_chars:
                used_chars.append(name)
        sa = find_scene_asset(assets, sl.get("sceneId"))
        if sa and sa["name"] not in used_scenes:
            used_scenes.append(sa["name"])

    title = sb.get("title") or "未命名"
    total = len(slices) * p["sliceSeconds"]
    cut_seq = " / ".join(CUT_POINT_ZH.get(sl.get("cutPoint"), sl.get("cutPoint") or "?") for sl in slices)
    cont_seq = " / ".join(CONTINUITY_ZH.get(sl.get("continuity"), "?").split("（")[0] for sl in slices)
    dlg_stat = []
    for sl in slices:
        n = slice_dialogue_chars(sl)
        dlg_stat.append(f"切片 {sl['id'].split('-')[-1]} {'无台词' if n == 0 else f'{n} 字'}")

    out = []
    out.append(f"# 《{title}》AI 成片切片 Prompt（{p['sliceSeconds']}s × {len(slices)}）\n")
    out.append("## 一、拆解说明\n")
    if scenes:
        locs = "、".join(f"{sc['id']} {sc['location']}" for sc in scenes["scenes"]
                         if any(sl.get("sceneId") == sc["id"] for sl in slices))
        out.append(f"- 原剧本场次：{locs}。")
    out.append(f"- 切分为 {len(slices)} 个 {p['sliceSeconds']} 秒切片，总时长 {total} 秒。")
    out.append(f"- 断点序列：{cut_seq}。")
    out.append(f"- 连续性：{cont_seq}。")
    out.append(f"- 台词字数（汉字）：{'；'.join(dlg_stat)}。")
    out.append(f"- 每个切片的结尾动作即下一个切片的起始画面；超 {p['maxChainDepth']} 片链式衔接后从母版重新锚定。\n")
    out.append("## 二、UUID 对照表\n")
    out.append("| 类型 | 名称 | UUID |")
    out.append("|---|---|---|")
    for name in used_chars:
        c = find_char(assets, name)
        out.append(f"| 人物 | {name} | {c.get('uuid') if c else ''} |")
    for s in assets.get("scenes", []):
        if s["name"] in used_scenes:
            out.append(f"| 场景 | {s['name']} | {s.get('uuid')} |")
    out.append("\n## 三、切片 Prompt\n")
    for i, sl in enumerate(slices, 1):
        persons = "".join(f"@{find_char(assets, n).get('uuid')}是{n}。" for n in sl.get("characters") or [])
        sa = find_scene_asset(assets, sl.get("sceneId"))
        scene_line = f"@{sa.get('uuid')}是{sa['name']}。" if sa else ""
        units = "；".join(sl.get("actionUnits") or [])
        setting = (sl.get("setting") or "").strip()
        visual = (setting + "，" if setting else "") + units + "。"
        dlg_lines = []
        for d in sl.get("dialogue") or []:
            emo = f"（{d['emotion']}）" if d.get("emotion") else ""
            dlg_lines.append(f"{{{d.get('speaker')}{emo}：{d.get('line')}}}")
        n = slice_dialogue_chars(sl)
        out.append(f"### 切片 {i}【{p['sliceSeconds']}s｜{sl.get('title')}】\n")
        out.append(f"源场次：{sl.get('sceneId')} ｜ 断点：{CUT_POINT_ZH.get(sl.get('cutPoint'), '?')} ｜ "
                   f"景别：{sl.get('size')} ｜ 运镜：{sl.get('camera')} ｜ "
                   f"连续性：{CONTINUITY_ZH.get(sl.get('continuity'), '?')} ｜ "
                   f"台词：{'无' if n == 0 else f'{n} 字'}"
                   + ("（激烈对峙）" if sl.get("intense") else "") + "\n")
        out.append("```text")
        out.append("真实电影风格。无BGM。无字幕。风格要求真实，镜头切换自然。")
        out.append(f"人物：{persons}")
        out.append(f"场景：{scene_line}")
        out.append(field("景别", sl.get("size") or ""))
        out.append(field("运镜", sl.get("camera") or ""))
        lang = (sl.get("shotLanguage") or "").strip()
        if lang and not lang.endswith(("。", "！", "？", ".")):
            lang += "。"
        out.append(f"镜头语言：{lang}")
        out.append(f"画面内容：{visual}")
        out.extend(dlg_lines)
        out.append("```\n")
    out.append("## 四、通用空白模板（新剧本复用）\n")
    out.append("```text")
    out.append(TEMPLATE_PATH.read_text(encoding="utf-8").rstrip("\n"))
    out.append("```")
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------- 渲染

def render_md(sb: dict, assets: dict, scenes: dict | None) -> str:
    slices = sb.get("slices") or []
    p = params_of(sb)
    out = [f"# 《{sb.get('title') or '未命名'}》分镜报告\n",
           f"- 画幅：{sb.get('aspectRatio', '9:16')} ｜ 切片：{len(slices)} × {p['sliceSeconds']}s "
           f"= {len(slices) * p['sliceSeconds']}s",
           f"- 场面：{len(sb.get('scenePlans') or []) or '?'} ｜ 质量门：见下方清单\n"]
    if scenes:
        out.append("## 场次计划\n")
        out.append("| 场次 | 地点 | 人物 | 台词句/字 | 动作节拍 | 预估秒 | 建议切片 |")
        out.append("|---|---|---|---|---|---|---|")
        for sc in scenes["scenes"]:
            dlg = scene_dialogue(sc)
            out.append(f"| {sc['id']} | {sc['location']} | {'、'.join(sc['characters'])} "
                       f"| {len(dlg)} / {sum(han(b['line']) for b in dlg)} "
                       f"| {sum(1 for b in sc['beats'] if b['type'] == 'action')} "
                       f"| {round(scene_estimate_seconds(sc, p), 1)} "
                       f"| {max(1, -(-int(scene_estimate_seconds(sc, p)) // p['sliceSeconds']))} |")
        out.append("")
    out.append("## 切片清单\n")
    out.append("| # | 切片 | 场次 | 标题 | 景别 | 运镜 | 断点 | 连续性 | 台词字 |")
    out.append("|---|---|---|---|---|---|---|---|---|")
    for i, sl in enumerate(slices, 1):
        n = slice_dialogue_chars(sl)
        out.append(f"| {i} | {sl['id']} | {sl.get('sceneId')} | {sl.get('title')} | {sl.get('size')} "
                   f"| {sl.get('camera')} | {CUT_POINT_ZH.get(sl.get('cutPoint'), '?')} "
                   f"| {sl.get('continuity')} | {n or '—'} |")
    out.append("\n## 连续性链\n")
    depth = 0
    for i, sl in enumerate(slices, 1):
        depth = depth + 1 if sl.get("continuity") == "chain" else 1
        line = (f"- 切片 {i}（{sl['id']}）{CONTINUITY_ZH.get(sl.get('continuity'), '?')}"
                f"｜链深度 {depth}/{p['maxChainDepth']}")
        if sl.get("shotLanguage"):
            line += f"｜镜头语言：{sl['shotLanguage']}"
        out.append(line)
    return "\n".join(out) + "\n"


def render_html(sb: dict, assets: dict, scenes: dict | None, gates, warnings) -> str:
    md = render_md(sb, assets, scenes)
    rows = []
    for g in gates:
        cls = "ok" if g["ok"] else "bad"
        rows.append(f'<tr class="{cls}"><td>{"✓" if g["ok"] else "✗"}</td><td>{g["id"]}</td>'
                    f'<td>{g["label"]}</td><td>{g["detail"]}</td></tr>')
    warn_html = "".join(f"<li>{w}</li>" for w in warnings)
    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>《{sb.get('title') or '未命名'}》分镜报告 · drama-studio</title>
<style>
body{{font-family:system-ui,"PingFang SC","Microsoft YaHei",sans-serif;margin:2rem auto;max-width:960px;color:#1f2430;line-height:1.6}}
table{{border-collapse:collapse;width:100%;font-size:14px;margin:1rem 0}}
th,td{{border:1px solid #d8dce3;padding:6px 10px;text-align:left;vertical-align:top}}
th{{background:#f2f4f8}} tr.ok td:first-child{{color:#137333}} tr.bad td{{background:#fdecea}}
pre{{background:#f6f7f9;padding:12px;overflow:auto;font-size:13px}}
h1{{font-size:22px}} h2{{font-size:17px;margin-top:2rem}}
.warn{{background:#fff7e0;border:1px solid #f0d488;padding:8px 14px;border-radius:6px}}
</style></head><body>
<h1>《{sb.get('title') or '未命名'}》分镜报告</h1>
<pre>{md}</pre>
<h2>质量门</h2>
<table><tr><th>✓✗</th><th>id</th><th>门禁</th><th>病灶</th></tr>{''.join(rows)}</table>
{f'<div class="warn"><b>提示</b><ul>{warn_html}</ul></div>' if warnings else ''}
</body></html>"""


# ---------------------------------------------------------------- CLI

def cmd_parse_script(args):
    text = Path(args.script).read_text(encoding="utf-8")
    title = args.title or Path(args.script).stem
    scenes = parse_script(text, title)
    scenes["source"] = Path(args.script).name
    n_dlg = sum(len(scene_dialogue(sc)) for sc in scenes["scenes"])
    n_act = sum(1 for sc in scenes["scenes"] for b in sc["beats"] if b["type"] == "action")
    print(f"解析完成：{len(scenes['scenes'])} 场，{n_dlg} 句台词，{n_act} 个动作节拍")
    if args.out:
        write_json(scenes, args.out)
        print(f"已写入 {args.out}")
    else:
        print(dump(scenes))
    return 0


def cmd_seed_assets(args):
    scenes = read_json(args.scenes)
    assets = seed_assets(scenes)
    print("资产骨架已生成：为每个角色/场次建卡，uuid 与参考图状态待填。")
    print("  - appearance/costume 用 character-extract.md 的造型师提示词产出")
    print("  - build-sheets 把四视图前缀 + 外貌 + 服饰组装成 sheetPrompt")
    print("  - 场景按 scene-extract.md 的美术指导提示词填 objects 分层清单，再手写 sheetPrompt")
    print("  - 用 uuid-new 生成 UUID；参考图出完/上传后把 images[].status 改为 linked 或 accepted")
    if args.out:
        write_json(assets, args.out)
        print(f"已写入 {args.out}")
    else:
        print(dump(assets))
    return 0


def cmd_build_sheets(args):
    """把四视图前缀 + appearance + costume 确定性组装为 sheetPrompt，并盖指纹。

    --apply：角色组装并写 generatedFrom；场景sheetPrompt 为手写，仅补盖缺失的指纹。
    """
    assets = read_json(args.assets)
    changed = []
    for c in assets.get("characters") or []:
        if not ((c.get("appearance") or "").strip() or (c.get("costume") or "").strip()):
            continue
        prompt = FOUR_VIEW_PREFIX + "\n" + (c.get("appearance") or "").strip() \
            + "\n" + (c.get("costume") or "").strip()
        if args.apply:
            c["sheetPrompt"] = prompt
            c["generatedFrom"] = prompt_sha(prompt)
        changed.append((c["name"], prompt))
    stamped = []
    if args.apply:
        for s in assets.get("scenes") or []:
            if (s.get("sheetPrompt") or "").strip() and not s.get("generatedFrom"):
                s["generatedFrom"] = prompt_sha(s["sheetPrompt"])
                stamped.append(s["name"])
    if not changed and not stamped:
        print("没有可组装的角色（appearance/costume 为空）。")
        return 1
    for name, prompt in changed:
        print(f"=== {name} ===")
        print(prompt)
        print()
    if args.apply:
        write_json(assets, args.assets)
        print(f"已写回 {args.assets}（组装 {len(changed)} 个角色"
              + (f"，补盖场景指纹 {len(stamped)} 个" if stamped else "") + "）")
    else:
        print("（预览模式；加 --apply 写回资产册并盖指纹）")
    return 0


def cmd_uuid_new(args):
    names = args.names or []
    n = args.count or max(1, len(names))
    for i in range(n):
        name = names[i] if i < len(names) else ""
        print(f"{uuidlib.uuid4()}" + (f"  {name}" if name else ""))
    return 0


def cmd_validate_assets(args):
    assets = read_json(args.assets)
    scenes = read_json(args.scenes) if args.scenes else None
    gates, warnings = validate_assets(assets, scenes)
    return print_gates(gates, warnings, "资产质量门")


def cmd_seed_storyboard(args):
    scenes = read_json(args.scenes)
    assets = read_json(args.assets) if args.assets else None
    sb = seed_storyboard(scenes, assets, args.aspect)
    print("场次切分计划（suggestSlices 为按时长估算的建议值，实际按断点规则与台词字数调整）：")
    print(f"{'场次':<8}{'地点':<18}{'台词句':<8}{'台词字':<8}{'动作':<6}{'预估秒':<8}{'建议切片'}")
    for pl in sb["scenePlans"]:
        print(f"{pl['sceneId']:<8}{pl['location']:<18}{pl['dialogueLines']:<8}{pl['dialogueChars']:<8}"
              f"{pl['actionBeats']:<6}{pl['estimateSeconds']:<8}{pl['suggestSlices']}")
    if args.out:
        write_json(sb, args.out)
        print(f"\n骨架已写入 {args.out}；按 stage-2-storyboard.md 的规则填 slices。")
    else:
        print("\n" + dump(sb))
    return 0


def cmd_validate_storyboard(args):
    sb = read_json(args.storyboard)
    scenes = read_json(args.scenes)
    assets = read_json(args.assets)
    gates, warnings = validate_storyboard(sb, scenes, assets)
    return print_gates(gates, warnings, "分镜质量门")


def cmd_compile_slices(args):
    sb = read_json(args.storyboard)
    assets = read_json(args.assets)
    scenes = read_json(args.scenes) if args.scenes else None
    if scenes:
        gates, warnings = validate_storyboard(sb, scenes, assets)
        bad = [g for g in gates if not g["ok"]]
        if bad and not args.force:
            print("质量门未过，拒绝编译。先修复以下问题再跑：")
            for g in bad:
                print(f"  ✗ {g['id']} — {g['label']}" + (f" — {g['detail']}" if g["detail"] else ""))
            print("\n（确认要在门未过时强行编译：--force）")
            return 1
    md = compile_slices(sb, assets, scenes)
    if args.out:
        Path(args.out).write_text(md, encoding="utf-8")
        print(f"已写入 {args.out}（{len(sb.get('slices') or [])} 个切片）")
    else:
        print(md)
    return 0


def cmd_render(args):
    sb = read_json(args.storyboard)
    assets = read_json(args.assets) if args.assets else {"scenes": [], "characters": []}
    scenes = read_json(args.scenes) if args.scenes else None
    if args.html:
        gates, warnings = ([], [])
        if scenes:
            gates, warnings = validate_storyboard(sb, scenes, assets)
        html = render_html(sb, assets, scenes, gates, warnings)
        if args.out:
            Path(args.out).write_text(html, encoding="utf-8")
            print(f"已写入 {args.out}")
        else:
            print(html)
        return 0
    md = render_md(sb, assets, scenes)
    if args.out:
        Path(args.out).write_text(md, encoding="utf-8")
        print(f"已写入 {args.out}")
    else:
        print(md)
    return 0


def cmd_slug(args):
    print(slug(args.name))
    return 0


def main(argv=None):
    # Windows 控制台默认 GBK，✓/✗/中文会崩：强制 UTF-8，不支持则降级替换
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    ap = argparse.ArgumentParser(prog="drama_studio.py", add_help=True)
    sub = ap.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("parse-script", help="解析分场剧本")
    sp.add_argument("script")
    sp.add_argument("--title", default="")
    sp.add_argument("--out", default="")
    sp.set_defaults(fn=cmd_parse_script)

    sp = sub.add_parser("seed-assets", help="从剧本种子化资产骨架")
    sp.add_argument("scenes")
    sp.add_argument("--out", default="")
    sp.set_defaults(fn=cmd_seed_assets)

    sp = sub.add_parser("build-sheets", help="组装人物四视图生图提示词（前缀+外貌+服饰）")
    sp.add_argument("assets")
    sp.add_argument("--apply", action="store_true")
    sp.set_defaults(fn=cmd_build_sheets)

    sp = sub.add_parser("uuid-new", help="生成 UUID")
    sp.add_argument("names", nargs="*")
    sp.add_argument("--count", type=int, default=0)
    sp.set_defaults(fn=cmd_uuid_new)

    sp = sub.add_parser("validate-assets", help="资产质量门")
    sp.add_argument("assets")
    sp.add_argument("--scenes", default="")
    sp.set_defaults(fn=cmd_validate_assets)

    sp = sub.add_parser("seed-storyboard", help="分镜骨架 + 切分计划")
    sp.add_argument("scenes")
    sp.add_argument("--assets", default="")
    sp.add_argument("--aspect", default="9:16")
    sp.add_argument("--out", default="")
    sp.set_defaults(fn=cmd_seed_storyboard)

    sp = sub.add_parser("validate-storyboard", help="分镜质量门（核心）")
    sp.add_argument("storyboard")
    sp.add_argument("--scenes", required=True)
    sp.add_argument("--assets", required=True)
    sp.set_defaults(fn=cmd_validate_storyboard)

    sp = sub.add_parser("compile-slices", help="编译 15s 切片 Prompt")
    sp.add_argument("storyboard")
    sp.add_argument("--assets", required=True)
    sp.add_argument("--scenes", default="")
    sp.add_argument("--out", default="")
    sp.add_argument("--force", action="store_true")
    sp.set_defaults(fn=cmd_compile_slices)

    sp = sub.add_parser("render", help="分镜报告")
    sp.add_argument("storyboard")
    sp.add_argument("--assets", default="")
    sp.add_argument("--scenes", default="")
    sp.add_argument("--html", action="store_true")
    sp.add_argument("--md", action="store_true")
    sp.add_argument("--out", default="")
    sp.set_defaults(fn=cmd_render)

    sp = sub.add_parser("slug", help="安全文件名")
    sp.add_argument("name")
    sp.set_defaults(fn=cmd_slug)

    args = ap.parse_args(argv)
    try:
        return args.fn(args) or 0
    except SystemExit as e:
        print(str(e), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
