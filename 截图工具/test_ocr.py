# -*- coding: utf-8 -*-
"""OCR 链路自检：生成一张代码图片 → 调用与主程序相同的 OCR 函数"""
import io
import sys

sys.path.insert(0, ".")
from PIL import Image, ImageDraw, ImageFont

img = Image.new("RGB", (760, 200), "#1e1e1e")
d = ImageDraw.Draw(img)
try:
    f = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", 26)
except Exception:
    f = ImageFont.load_default()
code = 'def hello(name):\n    print(f"Hi, {name}!")\n    return name * 2'
d.text((20, 20), code, font=f, fill="#d4d4d4")
buf = io.BytesIO()
img.save(buf, format="PNG")

import code_paster

text = code_paster.ocr_png_bytes(buf.getvalue())
print("OCR RESULT:")
print(text)
