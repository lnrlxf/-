# -*- coding: utf-8 -*-
"""图像增强效果测试：小号字体 + 模糊的截图，对比 增强前/增强后 的 OCR 识别率"""
import io
import sys
import time

sys.path.insert(0, ".")
from PIL import Image, ImageDraw, ImageFont, ImageFilter

import code_paster

CODE = "arr = np.zeros(10)"

def make_small_blurry(font_size, blur, w=320, h=60):
    img = Image.new("RGB", (w, h), "#1e1e1e")
    d = ImageDraw.Draw(img)
    try:
        f = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", font_size)
    except Exception:
        f = ImageFont.load_default()
    d.text((8, 10), CODE, font=f, fill="#c8c8c8")
    if blur > 0:
        img = img.filter(ImageFilter.GaussianBlur(blur))
    return img

def ocr_raw(img):
    """不做增强的原始识别"""
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG")
    return code_paster.ocr_png_bytes(buf.getvalue()).strip()

def ocr_enh(img):
    """增强后识别（与主程序 ocr_pil_image 相同路径）"""
    return code_paster.ocr_pil_image(img)

cases = [
    ("小字14px 无模糊", make_small_blurry(14, 0)),
    ("小字14px 轻模糊", make_small_blurry(14, 0.6)),
    ("小字12px 轻模糊", make_small_blurry(12, 0.5)),
    ("极小10px 模糊",   make_small_blurry(10, 0.8)),
]

print(f"目标文本: {CODE!r}\n" + "=" * 64)
for name, img in cases:
    raw = ocr_raw(img)
    t0 = time.perf_counter()
    enh = ocr_enh(img)
    cost = (time.perf_counter() - t0) * 1000
    print(f"\n[{name}]  图尺寸 {img.size}")
    print(f"  增强前: {raw!r}")
    print(f"  增强后: {enh!r}  ({cost:.0f}ms)")
print("\n" + "=" * 64)
