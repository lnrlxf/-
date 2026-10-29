# -*- coding: utf-8 -*-
"""端到端延迟测试：模拟真实流程，测量「截图进剪贴板 → 识别文本进剪贴板」的总延迟"""
import io
import sys
import threading
import time

sys.path.insert(0, ".")

import win32clipboard
import win32con
from PIL import Image, ImageDraw, ImageFont

import code_paster

app = code_paster.App()
t0 = None
RESULT_MARK = "numpy"


def make_screenshot():
    """模拟用户按 Win+Shift+S / 微信截图后，图片进入剪贴板"""
    global t0
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
    dib = buf.getvalue()[14:]

    time.sleep(1.5)  # 等 App 启动、OCR 预热完成
    # 清空剪贴板避免残留文本干扰
    win32clipboard.OpenClipboard()
    win32clipboard.EmptyClipboard()
    win32clipboard.CloseClipboard()
    time.sleep(0.1)

    t0 = time.perf_counter()  # ← 用户截图确认的瞬间
    win32clipboard.OpenClipboard()
    win32clipboard.EmptyClipboard()
    win32clipboard.SetClipboardData(win32con.CF_DIB, dib)
    win32clipboard.CloseClipboard()


threading.Thread(target=make_screenshot, daemon=True).start()

# 等待剪贴板出现识别文本
deadline = time.time() + 15
text = ""
while time.time() < deadline:
    text = app._safe_clipboard()
    if RESULT_MARK in text:
        break
    time.sleep(0.005)

if RESULT_MARK in text:
    latency = (time.perf_counter() - t0) * 1000
    print("=" * 50)
    print(f"端到端延迟（截图进剪贴板 → 识别文本进剪贴板）: {latency:.0f} ms")
    print(f"识别结果: {text!r}")
    print("=" * 50)
else:
    print("超时：15 秒内剪贴板未出现识别文本！")
app.quit()
