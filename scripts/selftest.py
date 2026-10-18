#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""drama-studio 自测：覆盖所有确定性逻辑。

不调用任何真实模型、不花任何额度、不联网。
每道质量门都有「击穿用例」和「不误拦用例」。
跑法：python scripts/selftest.py
"""
import copy
import json
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
EX = BASE / "examples"
sys.path.insert(0, str(Path(__file__).resolve().parent))

import drama_studio as ds  # noqa: E402

SCRIPT = (EX / "三打白骨精-script.md").read_text(encoding="utf-8")
SCENES = json.loads((EX / "三打白骨精-scenes.json").read_text(encoding="utf-8"))
ASSETS = json.loads((EX / "三打白骨精-assets.json").read_text(encoding="utf-8"))
SB = json.loads((EX / "三打白骨精-storyboard.json").read_text(encoding="utf-8"))

passed = 0


def ok(cond, label):
    global passed
    assert cond, label
    passed += 1


def eq(a, b, label):
    global passed
    assert a == b, f"{label} — 期望 {b!r}，实际 {a!r}"
    passed += 1


def gate_of(gates, gid):
    for g in gates:
        if g["id"] == gid:
            return g
    raise AssertionError(f"没有这道门：{gid}")


def sb_fresh():
    return copy.deepcopy(SB)


def assets_fresh():
    return copy.deepcopy(ASSETS)


# ---------------- 剧本解析 ----------------
sc = ds.parse_script(SCRIPT, "三打白骨精")
eq(len(sc["scenes"]), 4, "示例剧本解析出 4 场")
eq(sc["scenes"][0]["id"], "1-1", "场号 1-1")
eq(sc["scenes"][0]["location"], "白虎岭古道", "场地点")
eq(sc["scenes"][0]["time"], "日", "时间 日")
eq(sc["scenes"][0]["intExt"], "外", "内外 外")
eq(sc["scenes"][0]["characters"], ["孙悟空", "唐僧", "猪八戒", "沙僧", "白骨精"], "出场人物")
beats = sc["scenes"][0]["beats"]
eq(sum(1 for b in beats if b["type"] == "dialogue"), 3, "首场 3 句台词")
eq(sum(1 for b in beats if b["type"] == "action"), 6, "首场 6 个动作节拍")
eq(sum(1 for b in sc["scenes"][1]["beats"] if b.get("closeup")), 1, "第二场 1 条特写标注")
eq(len(sc["scenes"][1]["characters"]), 5, "第二场出场 5 人")
d0 = next(b for b in beats if b["type"] == "dialogue")
eq((d0["speaker"], d0["emotion"]), ("唐僧", "气息虚弱"), "台词拆出说话人与情绪")
ok("△" not in json.dumps(sc, ensure_ascii=False), "解析结果不带 △ 符号")

bad = ds.parse_script("1-1 房间 日 内\n这行无法识别\n", "x") if False else None
try:
    ds.parse_script("1-1 房间 日 内\n这行无法识别\n", "x")
    ok(False, "无法识别的行应当报错退出")
except SystemExit:
    ok(True, "无法识别的行会报错退出")

try:
    ds.parse_script("1-1 房间 日 内\n1-1 房间 日 内\n", "x")
    ok(False, "场号重复应当报错")
except SystemExit:
    ok(True, "场号重复会报错退出")

# ---------------- 基础函数 ----------------
eq(ds.han("悟空住手！莫要伤人！"), 8, "汉字计数不含标点")
eq(ds.norm("师父莫念，那真是妖精！"), ds.norm("师父莫念那真是妖精"), "归一化丢标点")
eq(ds.slug("三打白骨精 白虎岭/断崖前"), "三打白骨精-白虎岭-断崖前", "slug 生成安全文件名")

# ---------------- 资产种子化与质量门 ----------------
assets = ds.seed_assets(SCENES)
eq([c["name"] for c in assets["characters"]],
   ["孙悟空", "唐僧", "猪八戒", "沙僧", "白骨精", "村姑", "老妪", "老丈"], "资产骨架角色顺序照剧本")
eq(assets["characters"][0]["importance"], "protagonist", "首个角色默认 protagonist")
eq(len(assets["scenes"]), 4, "每个场次一个场景资产")
eq(assets["characters"][0]["images"][0]["view"], "four-view", "角色参考图默认四视图")
eq(assets["characters"][0]["images"][0]["ratio"], "16:9", "角色四视图比例 16:9")
ok("appearance" in assets["characters"][0] and "costume" in assets["characters"][0],
   "角色卡有外貌/服饰两段设计字段")
ok("objects" in assets["scenes"][0] and "sheetPrompt" in assets["scenes"][0],
   "场景卡有分层物件清单与空镜提示词字段")

gates, _ = ds.validate_assets(ASSETS, SCENES)
ok(all(g["ok"] for g in gates), f"示例资产全部门通过，未过：{[g['id'] for g in gates if not g['ok']]}")
eq(len(gates), 10, "资产质量门共 10 道")

m = assets_fresh()
m["characters"][0]["uuid"] = ""
gates, _ = ds.validate_assets(m, SCENES)
ok(not gate_of(gates, "uuid-format")["ok"], "缺 UUID 会被 uuid-format 门拦下")

m = assets_fresh()
m["characters"][0]["sheetPrompt"] = ""
gates, _ = ds.validate_assets(m, SCENES)
ok(not gate_of(gates, "reference-image")["ok"], "缺四视图生图提示词会被 reference-image 门拦下")

m = assets_fresh()
m["characters"][0]["images"] = []
gates, _ = ds.validate_assets(m, SCENES)
ok(not gate_of(gates, "reference-image")["ok"], "没有参考图会被 reference-image 门拦下")

m = assets_fresh()
m["characters"][0]["images"][0]["ratio"] = "2:3"
gates, _ = ds.validate_assets(m, SCENES)
ok(not gate_of(gates, "reference-image")["ok"], "四视图比例不是 16:9 会被 reference-image 门拦下")

m = assets_fresh()
m["characters"][0]["appearance"] = "孙悟空站在石阶上，golden headband, fur-covered face"
gates, _ = ds.validate_assets(m, SCENES)
ok(not gate_of(gates, "name-free")["ok"], "出图提示词含角色名会被 name-free 门拦下")

m = assets_fresh()
m["characters"][0]["voice"]["timbre"] = ""
gates, _ = ds.validate_assets(m, SCENES)
ok(not gate_of(gates, "voice-lock")["ok"], "有台词角色缺音色会被 voice-lock 门拦下")

m = assets_fresh()
m["scenes"][0]["objects"] = [o for o in m["scenes"][0]["objects"] if o["level"] != "核心"]
gates, _ = ds.validate_assets(m, SCENES)
ok(not gate_of(gates, "scene-objects")["ok"], "场景缺核心物件会被 scene-objects 门拦下")

m = assets_fresh()
m["scenes"][0]["objects"][0]["level"] = "次要"
gates, _ = ds.validate_assets(m, SCENES)
ok(not gate_of(gates, "scene-objects")["ok"], "物件层级非法会被 scene-objects 门拦下")

m = assets_fresh()
m["scenes"][0]["objects"][0]["role"] = ""
gates, _ = ds.validate_assets(m, SCENES)
ok(not gate_of(gates, "scene-objects")["ok"], "物件缺画面作用会被 scene-objects 门拦下")

m = assets_fresh()
m["scenes"][0]["sheetPrompt"] = m["scenes"][0]["sheetPrompt"].replace(
    "画面中不出现任何可读文字、数字、标语、品牌名、标签或说明字样。", "")
gates, _ = ds.validate_assets(m, SCENES)
ok(not gate_of(gates, "scene-no-text")["ok"], "场景提示词缺无可读文字约束会被 scene-no-text 门拦下")

m = assets_fresh()
m["characters"][0]["sheetPrompt"] += "比赛日追加一件银色竞赛服。"
gates, _ = ds.validate_assets(m, SCENES)
ok(not gate_of(gates, "sheet-fresh")["ok"], "出图后改提示词，图未重出会被 sheet-fresh 门拦下")

m = assets_fresh()
m["characters"][0]["generatedFrom"] = ""
gates, warns = ds.validate_assets(m, SCENES)
ok(gate_of(gates, "sheet-fresh")["ok"], "未记录指纹时 sheet-fresh 门不误报")
ok(any("孙悟空" in w and "generatedFrom" in w for w in warns), "已出图未记录指纹时明说跳过")

m = assets_fresh()
m["scenes"][0]["sheetPrompt"] += "墙角加一台制冰机。"
gates, _ = ds.validate_assets(m, SCENES)
ok(not gate_of(gates, "sheet-fresh")["ok"], "场景出图后改提示词会被 sheet-fresh 门拦下")

m = assets_fresh()
m["scenes"][0]["sceneRef"] = "9-9"
gates, _ = ds.validate_assets(m, SCENES)
ok(not gate_of(gates, "scene-coverage")["ok"], "剧本场次缺场景资产会被 scene-coverage 门拦下")

gates, _ = ds.validate_assets(ASSETS, None)
ok(gate_of(gates, "voice-lock")["ok"], "缺 scenes.json 时 voice-lock 明说跳过不误报")

# 四视图组装：确定性 = 前缀 + 外貌 + 服饰
assembled = ds.FOUR_VIEW_PREFIX + "\n" + ASSETS["characters"][0]["appearance"] \
    + "\n" + ASSETS["characters"][0]["costume"]
eq(ASSETS["characters"][0]["sheetPrompt"], assembled, "示例孙悟空的 sheetPrompt = 四视图前缀+外貌+服饰")
ok(ds.prompt_sha(ASSETS["characters"][0]["sheetPrompt"]) == ASSETS["characters"][0]["generatedFrom"],
   "示例 generatedFrom 与 sheetPrompt 指纹一致")

# ---------------- 分镜质量门 ----------------
gates, warnings = ds.validate_storyboard(SB, SCENES, ASSETS)
ok(all(g["ok"] for g in gates), f"示例分镜全部门通过，未过：{[g['id'] for g in gates if not g['ok']]}")
eq(not warnings, True, "示例分镜无提示（景别运镜都在推荐词表）")

m = sb_fresh()
m["slices"][1]["dialogue"][0]["line"] += "你倒是说话啊别装作没听见好不好"
gates, _ = ds.validate_storyboard(m, SCENES, ASSETS)
ok(not gate_of(gates, "dialogue-chars")["ok"], "单切片台词超 35 字会被 dialogue-chars 门拦下")

m = sb_fresh()
m["slices"][1]["dialogue"][0]["line"] += "你哑巴了"  # 35 + 4 = 39 字
m["slices"][1]["intense"] = True
gates, _ = ds.validate_storyboard(m, SCENES, ASSETS)
ok(gate_of(gates, "dialogue-chars")["ok"], "激烈对峙标记后 40 字内不误拦")

m = sb_fresh()
m["slices"][1]["dialogue"] = [{"speaker": "唐僧", "emotion": "虚弱", "line": "嗯。"}]
gates, _ = ds.validate_storyboard(m, SCENES, ASSETS)
ok(not gate_of(gates, "dialogue-chars")["ok"], "单切片台词不足 25 字会被拦下")

m = sb_fresh()
m["slices"][0]["dialogue"] = []
m["slices"][1]["dialogue"] = []
gates, _ = ds.validate_storyboard(m, SCENES, ASSETS)
ok(gate_of(gates, "dialogue-chars")["ok"], "无台词切片不受 25-35 字数门限制")

m = sb_fresh()
m["slices"][0]["actionUnits"] = m["slices"][0]["actionUnits"][:2]
gates, _ = ds.validate_storyboard(m, SCENES, ASSETS)
ok(not gate_of(gates, "action-units")["ok"], "动作单元不足 3 个会被 action-units 门拦下")

m = sb_fresh()
m["slices"][0]["actionUnits"].append("第六个动作单元")
gates, _ = ds.validate_storyboard(m, SCENES, ASSETS)
ok(not gate_of(gates, "action-units")["ok"], "动作单元超过 5 个会被 action-units 门拦下")

m = sb_fresh()
m["slices"][4]["entryState"] = "完全不同的入场状态"
gates, _ = ds.validate_storyboard(m, SCENES, ASSETS)
ok(not gate_of(gates, "continuity")["ok"], "链式切片入场状态接不上上一片出场会被 continuity 门拦下")

m = sb_fresh()
m["slices"][3]["continuity"] = "chain"
gates, _ = ds.validate_storyboard(m, SCENES, ASSETS)
ok(not gate_of(gates, "chain-depth")["ok"], "链深度超 3 会被 chain-depth 门拦下")

m = sb_fresh()
m["slices"][3]["reanchorFrom"] = []
gates, _ = ds.validate_storyboard(m, SCENES, ASSETS)
ok(not gate_of(gates, "reanchor-from")["ok"], "reanchor 切片不列锚定资产会被拦下")

m = sb_fresh()
m["slices"][0]["dialogue"] = [{"speaker": "唐僧", "emotion": "气息虚弱",
                              "line": "悟空，为师腹中饥饿，你去南山摘些桃子来。"}]
m["slices"][2]["dialogue"] = m["slices"][2]["dialogue"][1:]
gates, _ = ds.validate_storyboard(m, SCENES, ASSETS)
ok(not gate_of(gates, "dialogue-coverage")["ok"], "台词被挪场/漏掉会被 dialogue-coverage 门拦下")

m = sb_fresh()
m["slices"][1]["dialogue"][0]["line"] = "悟空，为师腹中饥饿，你去摘几个桃子来。"
gates, _ = ds.validate_storyboard(m, SCENES, ASSETS)
ok(not gate_of(gates, "dialogue-coverage")["ok"], "台词被改写（非逐字）会被 dialogue-coverage 门拦下")

m = sb_fresh()
for sl in m["slices"]:
    sl["size"], sl["camera"] = "中景", "固定镜头"
gates, _ = ds.validate_storyboard(m, SCENES, ASSETS)
ok(not gate_of(gates, "shot-variety")["ok"], "全部切片景别运镜相同会被 shot-variety 门拦下")

m = sb_fresh()
m["slices"][0]["shotLanguage"] = ""
gates, _ = ds.validate_storyboard(m, SCENES, ASSETS)
ok(not gate_of(gates, "shot-language")["ok"], "切片缺镜头语言会被 shot-language 门拦下")

m = sb_fresh()
m["slices"][0]["shotLanguage"] = "这是一个非常漫长的镜头语言描述" * 6
gates, _ = ds.validate_storyboard(m, SCENES, ASSETS)
ok(not gate_of(gates, "shot-language")["ok"], "镜头语言超长会被 shot-language 门拦下")

m = sb_fresh()
m["slices"][0]["shotLanguage"] = "这一镜要拍出命运感和张力"
gates, warns = ds.validate_storyboard(m, SCENES, ASSETS)
ok(gate_of(gates, "shot-language")["ok"], "镜头语言写虚了不拦（门只查有无与长度）")
ok(any("S01-01" in w and "写虚" in w for w in warns), "镜头语言无可执行术语时给提示")

m = sb_fresh()
for sl in m["slices"]:
    sl["shotLanguage"] = "中景固定机位，人物置于三分线，浅景深。"
gates, warns = ds.validate_storyboard(m, SCENES, ASSETS)
ok(gate_of(gates, "shot-language")["ok"], "各切片镜头语言不同且都在词表内，不误拦")
ok(not any("写虚" in w for w in warns), "镜头语言含术语时不出写虚提示")

m = sb_fresh()
m["slices"][0]["actionUnits"][0] = "△师徒四人沿青石阶上岭"
gates, _ = ds.validate_storyboard(m, SCENES, ASSETS)
ok(not gate_of(gates, "no-delta")["ok"], "切片文本残留 △ 会被 no-delta 门拦下")

m = sb_fresh()
m["slices"][4]["dialogue"][0]["speaker"] = "路人"
gates, _ = ds.validate_storyboard(m, SCENES, ASSETS)
ok(not gate_of(gates, "speaker-on-screen")["ok"], "说话人不在画内会被 speaker-on-screen 门拦下")

m = sb_fresh()
m["slices"][4]["characters"] = ["唐僧", "猪八戒", "沙僧", "村姑", "黄袍怪"]
gates, _ = ds.validate_storyboard(m, SCENES, ASSETS)
ok(not gate_of(gates, "cast-match")["ok"], "切片人物越出场次 cast 会被 cast-match 门拦下")

m = sb_fresh()
m["slices"][1]["seconds"] = 10
gates, _ = ds.validate_storyboard(m, SCENES, ASSETS)
ok(not gate_of(gates, "slice-seconds")["ok"], "切片时长不是 15 秒会被 slice-seconds 门拦下")

m = sb_fresh()
m["slices"][1]["cutPoint"] = "随便"
gates, _ = ds.validate_storyboard(m, SCENES, ASSETS)
ok(not gate_of(gates, "cut-point")["ok"], "断点类型非法会被 cut-point 门拦下")

m = sb_fresh()
m["slices"][1]["characters"] = ["唐僧", "黄袍怪"]
gates, _ = ds.validate_storyboard(m, SCENES, ASSETS)
ok(not gate_of(gates, "uuid-coverage")["ok"], "引用资产册里没有的人物会被 uuid-coverage 门拦下")

m = sb_fresh()
m["slices"][1]["continuity"] = "chain"
m["slices"][2]["continuity"] = "chain"
m["slices"][2]["sceneId"] = "1-2"
gates, _ = ds.validate_storyboard(m, SCENES, ASSETS)
ok(not gate_of(gates, "scene-boundary")["ok"], "跨场链式衔接会被 scene-boundary 门拦下")

# ---------------- 切片编译 ----------------
md = ds.compile_slices(SB, ASSETS, SCENES)
ok(md.startswith("# 《三打白骨精》AI 成片切片 Prompt（15s × 14）"), "编译输出标题")
ok("真实电影风格。无BGM。无字幕。风格要求真实，镜头切换自然。" in md, "固定模板头逐字保留")
eq(md.count("真实电影风格。无BGM。无字幕。风格要求真实，镜头切换自然。"), 15,
   "模板头出现 14 个切片 + 1 次空白模板")
ok("@a9cf0873-e937-4657-8eb0-a2d7dd2f77c2是孙悟空。" in md, "人物行 UUID 绑定")
ok("@3d1393e6-f6bd-4bac-8c7e-1c8a5ae6efb6是白虎岭古道。" in md, "场景行 UUID 绑定")
ok("{唐僧（气息虚弱）：悟空，为师腹中饥饿，你去南山摘些桃子来。}" in md,
   "台词逐字进切片")
ok("△" not in md.split("## 四、")[0], "切片正文不带 △")
ok("### 切片 5【15s｜编出来的家世】" in md, "切片标题带时长与小标题")
ok("## 四、通用空白模板（新剧本复用）" in md, "结尾附通用空白模板")
ok("景别：【中景/中近景/特写/全景】。" in md, "空白模板保留原文")
ok("镜头语言：【景别层次/机位角度/运镜方式/构图/与前后镜头的组接——一句话说清本切片的视觉意图】" in md,
   "空白模板含新增的镜头语言行")
ok("镜头语言：大全景定场，平视固定机位，石阶作纵深引导线，人物占画面下三分之一，山雾压住上缘留白，长镜头缓起。" in md,
   "切片1的镜头语言进编译产物")
ok("切片 01 无台词；切片 02 35 字" in md, "拆解说明按全片序号统计台词字数（多场戏不重号）")
# 镜头语言行必须位于运镜与画面内容之间
lines = [x for x in md.splitlines() if x.startswith(("景别：", "运镜：", "镜头语言：", "画面内容："))]
eq(lines[:4], ["景别：全景。", "运镜：固定镜头。",
               "镜头语言：大全景定场，平视固定机位，石阶作纵深引导线，人物占画面下三分之一，山雾压住上缘留白，长镜头缓起。",
               "画面内容：白虎岭古道口，石阶向上没入雾里，雾中只露枯松的轮廓，师徒四人沿青石阶上岭，孙悟空扛着金箍棒走在最前；唐僧牵马居中，猪八戒挑着行李一步一喘，沙僧持降妖宝杖殿后；唐僧勒住缰绳，按住腹部，脸色发白；山脊后，白骨精半边身子贴住岩壁，指骨抠进石缝；她的眼窝里透出一点绿光，盯住坡下那匹白马。"],
   "字段顺序：景别→运镜→镜头语言→画面内容")
tpl = (BASE / "assets" / "templates" / "slice-prompt.md").read_text(encoding="utf-8").rstrip("\n")
ok(md.rstrip("\n").endswith("```") and tpl in md, "空白模板与模板文件一致")

m = sb_fresh()
m["params"]["fieldBrackets"] = True
md2 = ds.compile_slices(m, ASSETS, SCENES)
ok("景别：【全景】。" in md2, "fieldBrackets=true 时景别带【】")

# 编译前自检：门不过则拒绝
bad_sb = sb_fresh()
bad_sb["slices"][1]["dialogue"][0]["line"] += "你倒是说话啊别装作没听见好不好"
tmp = BASE / "_selftest_bad_sb.json"
tmp.write_text(json.dumps(bad_sb, ensure_ascii=False), encoding="utf-8")
r = subprocess.run([sys.executable, str(BASE / "scripts" / "drama_studio.py"),
                    "compile-slices", str(tmp), "--assets", str(EX / "三打白骨精-assets.json"),
                    "--scenes", str(EX / "三打白骨精-scenes.json")],
                   capture_output=True, text=True, encoding="utf-8")
eq(r.returncode, 1, "质量门未过时 compile-slices 拒绝编译（exit 1）")
ok("拒绝编译" in r.stdout, "拒绝编译有明确提示")
r2 = subprocess.run([sys.executable, str(BASE / "scripts" / "drama_studio.py"),
                     "compile-slices", str(tmp), "--assets", str(EX / "三打白骨精-assets.json"),
                     "--scenes", str(EX / "三打白骨精-scenes.json"), "--force"],
                    capture_output=True, text=True, encoding="utf-8")
eq(r2.returncode, 0, "--force 可强行编译")
tmp.unlink()

# 解析 CLI 端到端
r = subprocess.run([sys.executable, str(BASE / "scripts" / "drama_studio.py"),
                    "parse-script", str(EX / "三打白骨精-script.md")],
                   capture_output=True, text=True, encoding="utf-8")
eq(r.returncode, 0, "parse-script CLI 正常退出")
ok('"speaker": "孙悟空"' in r.stdout, "parse-script stdout 可被重定向落盘")

r = subprocess.run([sys.executable, str(BASE / "scripts" / "drama_studio.py"),
                    "uuid-new", "--count", "2"],
                   capture_output=True, text=True, encoding="utf-8")
eq(len([x for x in r.stdout.split("\n") if x.strip()]), 2, "uuid-new --count 2 出两条")

# build-sheets：预览不落盘，--apply 组装并盖指纹
tmp_a = BASE / "_selftest_assets.json"
probe = assets_fresh()
for c in probe["characters"]:
    c["sheetPrompt"] = ""
    c["generatedFrom"] = ""
for s in probe["scenes"]:
    s["generatedFrom"] = ""
tmp_a.write_text(json.dumps(probe, ensure_ascii=False), encoding="utf-8")
r = subprocess.run([sys.executable, str(BASE / "scripts" / "drama_studio.py"),
                    "build-sheets", str(tmp_a)],
                   capture_output=True, text=True, encoding="utf-8")
eq(r.returncode, 0, "build-sheets 预览模式正常退出")
ok("白底人物四视图" in r.stdout, "预览含四视图前缀")
ok("预览模式" in r.stdout, "预览模式有提示")
before = json.loads(tmp_a.read_text(encoding="utf-8"))
ok(before["characters"][0]["sheetPrompt"] == "", "预览模式不改资产册")
r = subprocess.run([sys.executable, str(BASE / "scripts" / "drama_studio.py"),
                    "build-sheets", str(tmp_a), "--apply"],
                   capture_output=True, text=True, encoding="utf-8")
eq(r.returncode, 0, "build-sheets --apply 正常退出")
after = json.loads(tmp_a.read_text(encoding="utf-8"))
ok(after["characters"][0]["sheetPrompt"].startswith(ds.FOUR_VIEW_PREFIX[:20]),
   "--apply 后 sheetPrompt 以四视图前缀开头")
ok(after["characters"][0]["generatedFrom"] ==
   ds.prompt_sha(after["characters"][0]["sheetPrompt"]), "--apply 同时盖指纹")
ok(after["scenes"][0]["generatedFrom"] ==
   ds.prompt_sha(after["scenes"][0]["sheetPrompt"]), "--apply 给手写场景提示词补盖指纹")
gates, _ = ds.validate_assets(after, SCENES)
ok(all(g["ok"] for g in gates), "build-sheets 组装后的资产册全部门通过")
tmp_a.unlink()

# ---------------- 中英镜像一致性 ----------------
for zh, en in [("SKILL.md", "SKILL.en.md"), ("README.zh.md", "README.md")]:
    ok((BASE / zh).exists() and (BASE / en).exists(), f"{zh} 与 {en} 成对存在")
zh_refs = {p.name for p in (BASE / "references").glob("*.md")}
en_refs = {p.name for p in (BASE / "references" / "en").glob("*.md")}
eq(zh_refs, en_refs, "references/ 与 references/en/ 文件名一一对应")
ok(bool(zh_refs), "中文参考非空")

print(f"自测通过：{passed} 项断言")
