# -*- coding: utf-8 -*-
"""剪贴板图片链路测试：模拟微信截图（图片进剪贴板）→ 工具自动 OCR → 文字回剪贴板"""
import io
import sys
import time

sys.path.insert(0, ".")

import win32clipboard
import win32con
from PIL import Image, ImageDraw, ImageFont

# 1. 生成一张代码截图并放入剪贴板（CF_DIB，等价于微信截图确认后的剪贴板状态）
img = Image.new("RGB", (760, 200), "#1e1e1e")
d = ImageDraw.Draw(img)
try:
    f = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", 28)
except Exception:
    f = ImageFont.load_default()
d.text((20, 30), "import numpy as np", font=f, fill="#d4d4d4")
d.text((20, 90), "arr = np.zeros(10)", font=f, fill="#9cdcfe")

buf = io.BytesIO()
img.save(buf, format="BMP")
dib = buf.getvalue()[14:]  # 去掉 BMP 文件头即为 DIB
win32clipboard.OpenClipboard()
win32clipboard.EmptyClipboard()
win32clipboard.SetClipboardData(win32con.CF_DIB, dib)
win32clipboard.CloseClipboard()
print("已模拟微信截图：图片已放入剪贴板")

# 2. 启动 App，重置序号基线，触发一次剪贴板检查
import code_paster

app = code_paster.App()
app._last_clip_seq = 0          # 强制认为剪贴板已变化
app._check_clipboard_once()     # 应检测到图片并启动 OCR 线程

# 3. 等待 OCR 完成，检查剪贴板是否变成了识别文本
time.sleep(6)
result = app._safe_clipboard()
print("=" * 40)
print("剪贴板最终内容：")
print(result)
assert "numpy" in result, "OCR 结果未进入剪贴板！"
print("=" * 40)
print("剪贴板图片链路测试通过 ✓（安全模式下未发送任何模拟按键）")
app.quit()
