# -*- coding: utf-8 -*-
"""覆盖层冒烟测试：验证 DPI 感知 + 虚拟全屏覆盖层能正常创建/取消，且坐标为物理像素"""
import sys
import threading

sys.path.insert(0, ".")

import code_paster

code_paster.enable_dpi_awareness()

import tkinter as tk
from PIL import Image

root = tk.Tk()
root.withdraw()

# 用当前真实屏幕尺寸构造一张假截图
import mss
with mss.MSS() as sct:
    mon = sct.monitors[0]
print(f"虚拟屏幕(物理像素): {mon}")

fake = Image.new("RGB", (mon["width"], mon["height"]), "#222233")
result = {}

def on_done(cropped, rect):
    result["rect"] = rect
    result["size"] = cropped.size
    root.after(200, root.destroy)

sel = code_paster.RegionSelector(root, fake, mon, on_done)

# 验证窗口几何确实铺满整个虚拟屏幕
root.update()
root.update_idletasks()
geo = sel.top.winfo_geometry()
print(f"覆盖层 geometry: {geo}")
expected = f"{mon['width']}x{mon['height']}+{mon['left']}+{mon['top']}"
assert geo == expected, f"覆盖层未铺满全屏: {geo} != {expected}"
print("✓ 覆盖层铺满整个虚拟屏幕")

# 模拟一次拖拽选择（通过事件生成）
def simulate_drag():
    sel._press(type("E", (), {"x": 100, "y": 100})())
    sel._drag(type("E", (), {"x": 500, "y": 400})())
    sel._release(type("E", (), {"x": 500, "y": 400})())

root.after(300, simulate_drag)
root.mainloop()

assert result.get("rect") == (100, 100, 500, 400), f"坐标换算错误: {result}"
print(f"✓ 框选坐标即物理像素: {result['rect']}, 裁剪尺寸 {result['size']}")
print("覆盖层测试全部通过")
