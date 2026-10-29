# -*- coding: utf-8 -*-
"""GUI 确认逻辑测试：连续 N 帧确认 / 去重 / 新代码切换 / 剪贴板写入"""
import importlib
import sys

sys.path.insert(0, ".")

mod = importlib.import_module("房间码极速助手")
mod.code_paster.CFG["gui_sound"] = False   # 测试时静音

app = mod.RoomCodeGUI()

import pyperclip
pyperclip.copy("初始内容")

# 1) 第一帧：不复制
app.feed_frame("ZEV600", "raw1")
assert app.copied_code is None, "第一帧不应复制"
print("✓ 单帧不复制（待确认状态）")

# 2) 第二帧相同：确认复制 + 进剪贴板
app.feed_frame("ZEV600", "raw2")
assert app.copied_code == "ZEV600", "连续两帧应确认复制"
assert pyperclip.paste() == "ZEV600", "剪贴板应为确认的代码"
print("✓ 连续两帧一致 → 确认复制并进剪贴板")

# 3) 相同代码再次出现：不重复复制（剪贴板保持）
pyperclip.copy("用户手动改的内容")
app.feed_frame("ZEV600", "raw3")
app.feed_frame("ZEV600", "raw4")
assert pyperclip.paste() == "用户手动改的内容", "同一代码不应重复覆盖剪贴板"
print("✓ 同一代码不重复复制")

# 4) 新代码：第一帧不复制，第二帧确认新代码
app.feed_frame("ABC123", "raw5")
assert app.copied_code == "ZEV600", "新代码第一帧不应切换"
app.feed_frame("ABC123", "raw6")
assert app.copied_code == "ABC123" and pyperclip.paste() == "ABC123"
print("✓ 新代码连续两帧确认后切换复制")

# 5) 闪烁干扰：两帧不一致不复制
app.copied_code = None
app.recent.clear()
app.feed_frame("QQQ111", "raw7")
app.feed_frame("WWW222", "raw8")
assert app.copied_code is None, "帧间不一致不应复制"
print("✓ 帧间不一致（识别抖动）不复制 —— 准确性保障生效")

# 6) 无代码帧清空待确认
app.feed_frame(None, "")
assert len(app.recent) == 0
print("✓ 无代码帧清空待确认队列")

app.on_close()
print("\nGUI 确认逻辑测试全部通过 ✓")
