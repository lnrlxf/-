# -*- coding: utf-8 -*-
"""性能基准：定位 OCR 链路各环节耗时"""
import asyncio
import io
import sys
import time

sys.path.insert(0, ".")
from PIL import Image, ImageDraw, ImageFont

import code_paster


def make_img(w, h):
    img = Image.new("RGB", (w, h), "#1e1e1e")
    d = ImageDraw.Draw(img)
    try:
        f = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", 22)
    except Exception:
        f = ImageFont.load_default()
    y = 10
    i = 0
    while y < h - 30:
        d.text((15, y), f"result_{i} = model.predict(batch[{i}:{i}+32])  # 测试代码", font=f, fill="#d4d4d4")
        y += 30
        i += 1
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def timeit(label, fn, n=3):
    ts = []
    for _ in range(n):
        t0 = time.perf_counter()
        fn()
        ts.append(time.perf_counter() - t0)
    print(f"{label:<38} 平均 {sum(ts)/len(ts)*1000:7.1f} ms   (各次: {[f'{x*1000:.0f}' for x in ts]})")


small_png = make_img(760, 200)      # 小区域截图
big_png = make_img(1920, 1080)      # 全屏截图

# 1. 引擎创建耗时
def create_engine():
    import winrt.windows.media.ocr as ocr_mod
    from winrt.windows.globalization import Language
    return ocr_mod.OcrEngine.try_create_from_language(Language("en-US"))

timeit("创建OCR引擎(en-US)", create_engine)

# 2. 完整识别（含引擎创建+事件循环）—— 当前实现
timeit("完整OCR 小图760x200 (当前实现)", lambda: code_paster.ocr_png_bytes(small_png))
timeit("完整OCR 全屏1920x1080 (当前实现)", lambda: code_paster.ocr_png_bytes(big_png), n=2)

# 3. 拆开看：事件循环创建开销
def just_loop():
    async def nop():
        return 1
    asyncio.run(nop())
timeit("asyncio.run 空协程(事件循环开销)", just_loop)

# 4. 拆开看：解码+识别（复用引擎与循环）
import winrt.windows.media.ocr as ocr_mod
from winrt.windows.globalization import Language
from winrt.windows.storage.streams import DataWriter, InMemoryRandomAccessStream
from winrt.windows.graphics.imaging import BitmapDecoder

ENGINE = ocr_mod.OcrEngine.try_create_from_language(Language("en-US"))

async def recognize(png):
    stream = InMemoryRandomAccessStream()
    writer = DataWriter(stream)
    writer.write_bytes(bytearray(png))
    await writer.store_async()
    await writer.flush_async()
    stream.seek(0)
    decoder = await BitmapDecoder.create_async(stream)
    bitmap = await decoder.get_software_bitmap_async()
    return await ENGINE.recognize_async(bitmap)

async def bench_decode(png, n=3):
    ts = []
    for _ in range(n):
        t0 = time.perf_counter()
        await recognize(png)
        ts.append(time.perf_counter() - t0)
    print(f"{'复用引擎+复用循环 识别小图':<38} 平均 {sum(ts)/len(ts)*1000:7.1f} ms")

async def bench_decode_big(png, n=2):
    ts = []
    for _ in range(n):
        t0 = time.perf_counter()
        await recognize(png)
        ts.append(time.perf_counter() - t0)
    print(f"{'复用引擎+复用循环 识别全屏图':<36} 平均 {sum(ts)/len(ts)*1000:7.1f} ms")

loop = asyncio.new_event_loop()
loop.run_until_complete(bench_decode(small_png))
loop.run_until_complete(bench_decode_big(big_png))

# 5. 剪贴板图片读取耗时
import win32clipboard, win32con
from PIL import ImageGrab
dib = None
img = Image.open(io.BytesIO(small_png))
buf = io.BytesIO(); img.save(buf, format="BMP")
dib = buf.getvalue()[14:]
win32clipboard.OpenClipboard(); win32clipboard.EmptyClipboard()
win32clipboard.SetClipboardData(win32con.CF_DIB, dib); win32clipboard.CloseClipboard()

def grab():
    return ImageGrab.grabclipboard()
timeit("读剪贴板图片 grabclipboard", grab)

def seq():
    return win32clipboard.GetClipboardSequenceNumber()
timeit("轮询检查 GetClipboardSequenceNumber", seq, n=100)
