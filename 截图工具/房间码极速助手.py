# -*- coding: utf-8 -*-
"""
房间码极速助手（图形界面版）
================================
- 选择识别区域 / 开始识别 / 停止识别
- 连续 N 帧（默认 2 帧）识别到相同代码才复制 → 保证提取内容准确一致
- 复制成功后：声音提示 + 绿色状态 + 代码已进剪贴板，游戏中直接 Ctrl+V
- Ctrl + Alt + K 紧急停止（在任何界面都有效）

复用 code_paster.py 的 OCR 引擎 / 图像增强 / 正则提取 / 全屏区域选择。
"""

import os
import sys
import threading
import time
import traceback
from collections import deque

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

import code_paster  # 复用：OCR、增强、提取、区域选择、配置

import tkinter as tk
import pyperclip
import keyboard

# ---------------- 颜色 ----------------
GREEN = "#1a7f37"
ORANGE = "#b45309"
GRAY = "#6b7280"
BLUE = "#1f6feb"
PANEL = "#f5f6f8"
RED = "#c0392b"


def play_success_sound():
    """复制成功声音提示（可用 config.json 的 gui_sound 关闭）"""
    if not code_paster.CFG.get("gui_sound", True):
        return
    import winsound
    try:
        winsound.PlaySound("SystemAsterisk", winsound.SND_ALIAS | winsound.SND_ASYNC)
    except Exception:
        try:
            winsound.MessageBeep(winsound.MB_ICONASTERISK)
        except Exception:
            pass


class RoomCodeGUI:
    def __init__(self):
        code_paster.enable_dpi_awareness()
        self.root = tk.Tk()
        self.root.title("房间码极速助手")
        self.root.geometry("700x640")
        self.root.configure(bg="white")
        self.root.resizable(False, False)

        self.monitoring = False
        self.copied_code = None          # 已复制（确认过）的代码
        self.frames_needed = max(2, int(code_paster.CFG.get("gui_confirm_frames", 2)))
        self.recent = deque(maxlen=self.frames_needed)   # 最近 N 帧的识别结果
        self.selector = None
        self._monitor_thread = None

        self._build_ui()
        keyboard.add_hotkey("ctrl+alt+k", self._emergency_stop)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # 启动时若已有区域，提示可直接开始
        if code_paster.CFG.get("region"):
            self.hint_label.config(
                text="已加载上次保存的识别区域，点击「开始识别」即可。", fg=GRAY)

    # ---------------- 界面 ----------------
    def _build_ui(self):
        pad = {"padx": 24}

        tk.Label(self.root, text="房间码极速助手", bg="white",
                 font=("Microsoft YaHei", 22, "bold"), anchor="w").pack(fill="x", **pad, pady=(20, 2))
        tk.Label(self.root, text=f"识别 {code_paster.CFG.get('extract_pattern', '[A-Z0-9]{6}')} 格式的房间码，"
                                 f"连续 {self.frames_needed} 帧一致后自动复制到剪贴板。",
                 bg="white", fg=GRAY, font=("Microsoft YaHei", 10), anchor="w").pack(fill="x", **pad)

        # 按钮行
        btn_bar = tk.Frame(self.root, bg="white")
        btn_bar.pack(fill="x", **pad, pady=(16, 8))
        btn_font = ("Microsoft YaHei", 11)
        self.btn_region = tk.Button(btn_bar, text="  选择识别区域  ", font=btn_font,
                                    command=self.choose_region)
        self.btn_region.pack(side="left", padx=(0, 12))
        self.btn_start = tk.Button(btn_bar, text="  开始识别  ", font=btn_font,
                                   command=self.start)
        self.btn_start.pack(side="left", padx=(0, 12))
        self.btn_stop = tk.Button(btn_bar, text="  停止识别  ", font=btn_font,
                                  command=self.stop, state="disabled")
        self.btn_stop.pack(side="left")

        self.hint_label = tk.Label(self.root, text="第一步：点击「选择识别区域」框选直播画面中房间码的位置。",
                                   bg="white", fg=GRAY, font=("Microsoft YaHei", 9), anchor="w")
        self.hint_label.pack(fill="x", **pad)

        # 当前房间码面板
        panel = tk.Frame(self.root, bg=PANEL)
        panel.pack(fill="x", **pad, pady=(14, 6))
        tk.Label(panel, text="当前房间码", bg=PANEL, fg=GRAY,
                 font=("Microsoft YaHei", 10), anchor="w").pack(fill="x", padx=16, pady=(12, 4))

        code_box = tk.Frame(panel, bg="white", highlightbackground=BLUE, highlightthickness=2)
        code_box.pack(fill="x", padx=16, pady=(0, 10))
        self.code_label = tk.Label(code_box, text="——", bg="white", fg="#111827",
                                   font=("Consolas", 40, "bold"))
        self.code_label.pack(pady=14)

        self.status_label = tk.Label(panel, text="尚未开始识别", bg=PANEL, fg=GRAY,
                                     font=("Microsoft YaHei", 10), anchor="w")
        self.status_label.pack(fill="x", padx=16)
        self.pending_label = tk.Label(panel, text="", bg=PANEL, fg=GRAY,
                                      font=("Microsoft YaHei", 9), anchor="w")
        self.pending_label.pack(fill="x", padx=16)
        self.ocr_label = tk.Label(panel, text="最近 OCR：（无）", bg=PANEL, fg=GRAY,
                                  font=("Microsoft YaHei", 9), anchor="w", justify="left")
        self.ocr_label.pack(fill="x", padx=16, pady=(2, 12))

        # 底部说明
        tk.Label(self.root, text="识别成功后按 Ctrl + V 粘贴    |    Ctrl + Alt + K 紧急停止",
                 bg="white", fg="#111827", font=("Microsoft YaHei", 10, "bold"),
                 anchor="w").pack(fill="x", **pad, pady=(14, 2))
        tk.Label(self.root,
                 text=f"识别到连续 {self.frames_needed} 帧相同的房间码后，程序会立即复制并发出声音提示、显示绿色状态；"
                      f"切换到游戏输入框后按 Ctrl + V。",
                 bg="white", fg=ORANGE, font=("Microsoft YaHei", 9), anchor="w",
                 justify="left", wraplength=640).pack(fill="x", **pad)

    # ---------------- 选择区域 ----------------
    def choose_region(self):
        if self.selector:
            return
        self.root.withdraw()   # 先隐藏主窗口，避免遮挡
        try:
            pil_img, monitor = code_paster.grab_virtual_screen()
        except Exception:
            traceback.print_exc()
            self.root.deiconify()
            self.status_label.config(text="截屏失败，请重试", fg=RED)
            return

        def on_region(cropped, rect):
            self.selector = None
            x1, y1, x2, y2 = rect
            region = {
                "left": int(monitor["left"] + x1),
                "top": int(monitor["top"] + y1),
                "width": int(x2 - x1),
                "height": int(y2 - y1),
            }
            code_paster.CFG["region"] = region
            code_paster.save_config()
            self.root.after(0, lambda: self._on_region_saved(region))

        self.selector = code_paster.RegionSelector(self.root, pil_img, monitor, on_region)

    def _on_region_saved(self, region):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        self.hint_label.config(
            text=f"识别区域已保存：左{region['left']} 上{region['top']} "
                 f"宽{region['width']} 高{region['height']}。可随时重新框选。", fg=GRAY)
        self.status_label.config(text="区域已就绪，点击「开始识别」", fg=BLUE)

    # ---------------- 开始 / 停止 ----------------
    def start(self):
        if self.monitoring:
            return
        region = code_paster.CFG.get("region")
        if not region:
            self.status_label.config(text="请先点击「选择识别区域」", fg=RED)
            return
        self.monitoring = True
        self.copied_code = None
        self.recent.clear()
        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="normal")
        self.status_label.config(text="识别中… 等待房间码出现", fg=BLUE)
        self.code_label.config(text="——")
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()

    def stop(self):
        if not self.monitoring:
            return
        self.monitoring = False
        self.btn_start.config(state="normal")
        self.btn_stop.config(state="disabled")
        self.status_label.config(text="已停止识别", fg=GRAY)
        self.pending_label.config(text="")

    def _emergency_stop(self):
        self.root.after(0, self.stop)

    # ---------------- 监控循环 ----------------
    def _monitor_loop(self):
        import re
        import mss
        from PIL import Image
        pattern = re.compile(code_paster.CFG.get("extract_pattern", "[A-Z0-9]{6}"))
        region = code_paster.CFG.get("region")
        interval = float(code_paster.CFG.get("region_monitor_interval", 1.0))
        while self.monitoring:
            t0 = time.perf_counter()
            text, code = "", None
            try:
                with mss.MSS() as sct:
                    shot = sct.grab(region)
                img = Image.frombytes("RGB", shot.size, shot.rgb)
                text = code_paster.ocr_pil_image(img, verbose=False)
                code = code_paster.extract_code(text, pattern)
            except Exception:
                if self.monitoring:
                    traceback.print_exc()
            # 交给主线程处理（确认逻辑 + 界面刷新）
            self.root.after(0, lambda c=code, t=text: self.feed_frame(c, t))
            elapsed = time.perf_counter() - t0
            time.sleep(max(0.1, interval - elapsed))

    # ---------------- 核心：连续 N 帧确认 ----------------
    def feed_frame(self, code, text):
        """处理一帧识别结果。连续 N 帧相同且未复制过 → 确认复制。
        （单独抽出便于单元测试）"""
        self.ocr_label.config(text="最近 OCR：" + (text[:60] + "…" if len(text) > 60 else text)
                              if text else "最近 OCR：（本帧未识别到文字）")
        if not code:
            self.recent.clear()
            self.pending_label.config(text="")
            if self.monitoring and self.copied_code is None:
                self.status_label.config(text="识别中… 等待房间码出现", fg=BLUE)
            return

        self.recent.append(code)
        if len(self.recent) == self.frames_needed and \
                all(c == code for c in self.recent) and code != self.copied_code:
            self._confirm(code)
            self.pending_label.config(text="")
        else:
            self.pending_label.config(
                text=f"待确认：{code}（已连续 {len([c for c in self.recent if c == code])}/"
                     f"{self.frames_needed} 帧一致）", fg=GRAY)
            if self.copied_code is None:
                self.status_label.config(text="识别中… 正在连续帧确认", fg=BLUE)

    def _confirm(self, code):
        """确认成功：复制到剪贴板 + 声音提示 + 绿色状态"""
        pyperclip.copy(code)
        self.copied_code = code
        self.recent.clear()
        play_success_sound()
        self.code_label.config(text=code)
        self.status_label.config(
            text=f"已复制房间码 {code}，现在可在游戏中按 Ctrl+V 粘贴", fg=GREEN)

    # ---------------- 退出 ----------------
    def on_close(self):
        self.monitoring = False
        try:
            keyboard.unhook_all_hotkeys()
        except Exception:
            pass
        self.root.destroy()

    def run(self):
        self.root.mainloop()


def main():
    app = RoomCodeGUI()
    app.run()


if __name__ == "__main__":
    main()
