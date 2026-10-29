# -*- coding: utf-8 -*-
"""区域监控提取测试：正则提取逻辑 + 模拟监控循环体（合成图像走完整 OCR→提取 路径）"""
import io
import re
import sys

sys.path.insert(0, ".")
from PIL import Image, ImageDraw, ImageFont

import code_paster

pattern = re.compile(code_paster.CFG.get("extract_pattern", "[A-Z0-9]{6}"))

# 1. 正则提取单元用例
cases = [
    ("房间代码 IYK210 复制你的房间代码", "IYK210"),
    ("iyk 210", "IYK210"),          # 小写+空格容错
    ("IYK-210", "IYK210"),          # 干扰符号容错
    ("当前房间:ABC9Z7", "ABC9Z7"),
    ("这里没有代码", None),
]
print("== 正则提取测试 ==")
ok = True
for text, expect in cases:
    got = code_paster.extract_code(text, pattern)
    mark = "✓" if got == expect else "✗"
    if got != expect:
        ok = False
    print(f"  {mark} {text!r} → {got!r} (期望 {expect!r})")

# 2. 模拟监控循环体：合成一张“房间代码”截图 → OCR → 提取
print("\n== 模拟区域监控（合成图像）==")
img = Image.new("RGB", (400, 120), "#101820")
d = ImageDraw.Draw(img)
try:
    f = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", 30)
    fs = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 16)
except Exception:
    f = fs = ImageFont.load_default()
d.text((20, 15), "房间代码", font=fs, fill="#888888")
d.text((20, 50), "IYK210", font=f, fill="#ffffff")

text = code_paster.ocr_pil_image(img, verbose=False)
code = code_paster.extract_code(text, pattern)
print(f"  OCR 原文: {text!r}")
print(f"  提取结果: {code!r}")
assert code == "IYK210", f"提取失败: {code!r}"
print("  ✓ 监控循环体路径测试通过")

print("\n全部通过" if ok else "\n存在失败用例！")
