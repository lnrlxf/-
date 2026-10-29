# -*- coding: utf-8 -*-
"""
截屏取码 → 自动/手动粘贴 小工具 v2
=================================================
三种取码方式：
  1. 微信截图（推荐，框选范围可达全屏）：按微信截图键(默认 Alt+A)框选 →
     点“✓”确认后图片进入剪贴板 → 本工具自动 OCR → 文字放回剪贴板 → 按适配档投递
  2. F9 布防：在源应用按一次 Ctrl+C 复制文字 → 自动投递
  3. F8 自带框选：不依赖微信，工具自己截屏框选（主显示器全屏）→ OCR

适配档（profiles，config.json 可增删）决定“投递”方式：
  - auto_paste=false（安全模式）：绝不向目标程序发送任何模拟按键，
    识别结果只放剪贴板，由你手动切窗口按 Ctrl+V —— 对反作弊零风险。
  - auto_paste=true：自动激活目标窗口并模拟 Ctrl+V（仅建议用于微信/浏览器/编辑器等普通应用）。

热键（可在 config.json 修改，支持组合键如 "ctrl+alt+s"）：
  F2  : 框选并保存「直取区域」
  F3  : 直取：识别直取区域的全部文字 → 原文直接进剪贴板 → 可直接粘贴
  F4  : 开始/停止「区域监控」——持续识别指定区域，自动提取代码（如房间码）并复制
  F5  : 框选并保存监控区域（只需设置一次，之后按 F4 即可）
  F6  : 一键呼出系统截图(Win+Shift+S) → 框选松开后自动 OCR → 直接可粘贴
  F7  : 循环切换适配档（VALORANT安全模式 / 微信 / QQ / …）
  F8  : 自带框选截屏 OCR
  F9  : 布防：下一次复制（文字或微信截图）后自动投递
  F10 : 立即把当前剪贴板内容（文字或图片）投递到当前适配档
  F11 : 列出所有可见窗口标题
  F12 : 退出

用法：
  python code_paster.py            正常运行
  python code_paster.py --list     仅列出当前可见窗口标题
"""

import asyncio
import ctypes
import json
import os
import sys
import threading
import time
import traceback

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

# ---------------- 预置适配档 ----------------
# name            显示名
# target_window   目标窗口标题关键字（模糊匹配，F11 可查询；安全模式下仅用于提示）
# auto_paste      True=自动激活窗口并模拟 Ctrl+V；False=安全模式（只放剪贴板，手动粘贴）
# use_direct_input True=扫描码方式（游戏/DirectX 程序需要，但有被反作弊注意的风险）
DEFAULT_PROFILES = [
    {
        "name": "VALORANT安全模式",
        "target_window": "VALORANT",
        "auto_paste": False,
        "use_direct_input": False,
        "note": "不向游戏发送任何模拟输入，识别结果放剪贴板后由你手动 Ctrl+V，零封号风险"
    },
    {
        "name": "微信",
        "target_window": "微信",
        "auto_paste": True,
        "use_direct_input": False,
        "note": "自动切到微信窗口并粘贴"
    },
    {
        "name": "QQ",
        "target_window": "QQ",
        "auto_paste": True,
        "use_direct_input": False,
        "note": "自动切到QQ窗口并粘贴"
    },
    {
        "name": "通用自动粘贴",
        "target_window": "",
        "auto_paste": False,
        "use_direct_input": False,
        "note": "只把识别结果放剪贴板，手动到任意应用粘贴"
    },
]

DEFAULT_CONFIG = {
    "profiles": DEFAULT_PROFILES,      # 适配档列表（可自行增加新软件的适配）
    "active_profile": 0,               # 当前使用的适配档序号
    "hotkey_screenshot": "f6",         # 一键呼出系统截图（等效 Win+Shift+S）
    "hotkey_set_region": "f5",         # 框选并保存监控区域（房间码提取用）
    "hotkey_toggle_monitor": "f4",     # 开始/停止区域监控（自动提取代码）
    "hotkey_set_region_direct": "f2",  # 框选并保存直取区域
    "hotkey_copy_region": "f3",        # 直取：识别直取区域原文 → 剪贴板
    "hotkey_cycle_profile": "f7",      # 切换适配档
    "hotkey_ocr": "f8",                # 自带框选截屏 OCR
    "hotkey_arm_clipboard": "f9",      # 布防：下一次复制后自动投递
    "hotkey_paste_now": "f10",         # 立即投递当前剪贴板
    "hotkey_list_windows": "f11",      # 列出窗口
    "hotkey_quit": "f12",              # 退出
    "watch_clipboard_image": "always", # 微信截图监听: always=随时自动OCR / armed=仅F9布防后 / off=关闭
    "paste_delay": 0.15,               # 激活窗口后等待多少秒再按 Ctrl+V（仅自动粘贴档使用）
    "ocr_language": "en-US",           # auto / en-US / zh-Hans-CN（代码识别推荐 en-US）
    "ocr_enhance": True,               # 小图/模糊图自动增强（放大+灰度+对比度），提高识别率
    "region": None,                    # 监控区域 {"left","top","width","height"}（物理像素，F5 框选自动保存）
    "region_direct": None,             # 直取区域（F2 框选自动保存，F3 识别原文）
    "region_monitor_interval": 1.0,    # 区域监控截图间隔（秒）
    "extract_pattern": "[A-Z0-9]{6}",  # 提取目标内容的正则：房间代码=6位大写字母+数字
    "clipboard_poll_interval": 0.03,   # 剪贴板轮询间隔（秒）。序号检查几乎零开销，30ms=近乎实时
    "ocr_warmup": True                 # 启动时预热 OCR 引擎，消除首次识别的冷启动延迟
}


def load_config():
    cfg = json.loads(json.dumps(DEFAULT_CONFIG))  # 深拷贝
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            # 老版本配置迁移：没有 profiles 时用 target_window 生成一个适配档
            if "profiles" not in loaded:
                tw = loaded.get("target_window", "")
                loaded["profiles"] = [{
                    "name": "迁移配置",
                    "target_window": tw,
                    "auto_paste": loaded.get("auto_paste_after_ocr", True),
                    "use_direct_input": loaded.get("use_direct_input", False),
                    "note": "由旧版 config.json 自动迁移"
                }]
                loaded["active_profile"] = 0
            cfg.update(loaded)
        except Exception as e:
            print(f"[警告] 读取 config.json 失败，使用默认配置: {e}")
    save_config(cfg)
    return cfg


def save_config(cfg=None):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg or CFG, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[警告] 保存 config.json 失败: {e}")


CFG = load_config()


def get_profile():
    """当前生效的适配档"""
    profiles = CFG.get("profiles") or []
    idx = int(CFG.get("active_profile", 0) or 0)
    if profiles and 0 <= idx < len(profiles):
        p = dict(profiles[idx])
    else:
        p = {"name": "默认", "target_window": "", "auto_paste": False, "use_direct_input": False}
    p.setdefault("auto_paste", False)
    p.setdefault("use_direct_input", False)
    p.setdefault("target_window", "")
    return p


# ---------------- Win32 相关 ----------------

import win32api
import win32con
import win32clipboard
import win32gui
import win32process
import keyboard
import pyperclip


def list_visible_windows():
    result = []

    def cb(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if title.strip():
                result.append((hwnd, title))

    win32gui.EnumWindows(cb, None)
    return result


def find_target_window(keyword):
    if not keyword:
        return None, None
    keyword_l = keyword.lower()
    matches = [(h, t) for h, t in list_visible_windows() if keyword_l in t.lower()]
    if not matches:
        return None, None
    exact = [m for m in matches if m[1].lower() == keyword_l]
    pick = exact[0] if exact else sorted(matches, key=lambda m: len(m[1]))[0]
    return pick


def activate_window(hwnd):
    """激活并前置窗口（绕过 Windows 前台锁定限制）"""
    try:
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        fg = win32gui.GetForegroundWindow()
        tid_fg = win32process.GetWindowThreadProcessId(fg)[0] if fg else 0
        tid_target = win32process.GetWindowThreadProcessId(hwnd)[0]
        if tid_fg and tid_fg != tid_target:
            ctypes.windll.user32.AttachThreadInput(tid_fg, tid_target, True)
            win32gui.BringWindowToTop(hwnd)
            win32gui.SetForegroundWindow(hwnd)
            ctypes.windll.user32.AttachThreadInput(tid_fg, tid_target, False)
        else:
            win32gui.BringWindowToTop(hwnd)
            win32gui.SetForegroundWindow(hwnd)
        return True
    except Exception:
        traceback.print_exc()
        return False


def send_ctrl_v(use_direct):
    """向当前前台窗口发送 Ctrl+V（仅在 auto_paste 适配档下被调用）"""
    if use_direct:
        import pydirectinput
        pydirectinput.keyDown("ctrl")
        time.sleep(0.03)
        pydirectinput.press("v")
        time.sleep(0.03)
        pydirectinput.keyUp("ctrl")
    else:
        win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
        win32api.keybd_event(ord("V"), 0, 0, 0)
        win32api.keybd_event(ord("V"), 0, win32con.KEYEVENTF_KEYUP, 0)
        win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)


def deliver(text_preview=None):
    """按当前适配档投递剪贴板内容：自动粘贴 或 安全模式提示手动粘贴"""
    p = get_profile()
    if not p["auto_paste"]:
        where = f"“{p['target_window']}”" if p["target_window"] else "目标应用"
        print(f"[安全模式·{p['name']}] 文本已在剪贴板 → 请手动切换到 {where} 按 Ctrl+V")
        print(f"[安全模式] 本次未向任何程序发送模拟按键（{p.get('note', '')}）")
        return True
    if not p["target_window"]:
        print(f"[失败] 适配档 “{p['name']}” 是自动粘贴模式但没填 target_window")
        return False
    hwnd, title = find_target_window(p["target_window"])
    if not hwnd:
        print(f"[失败] 找不到标题包含 “{p['target_window']}” 的窗口。按 F11 查看窗口列表。")
        print("[提示] 文本仍保留在剪贴板中，可手动粘贴")
        return False
    print(f"[信息] 切换到目标窗口: {title} (hwnd={hwnd})")
    if not activate_window(hwnd):
        print("[失败] 激活目标窗口失败（文本仍在剪贴板，可手动粘贴）")
        return False
    time.sleep(float(CFG.get("paste_delay", 0.4)))
    send_ctrl_v(p["use_direct_input"])
    print(f"[完成] 已粘贴{('（' + text_preview[:40] + '…）') if text_preview else ''}")
    return True


# ---------------- OCR（Windows 自带识别引擎） ----------------

_OCR_LOCK = threading.Lock()
_OCR_ENGINE = None          # 引擎缓存（创建一次复用，避免每次识别重复初始化）
_OCR_ENGINE_LANG = None


def _get_ocr_engine(lang):
    """获取（并缓存）OCR 引擎"""
    global _OCR_ENGINE, _OCR_ENGINE_LANG
    if _OCR_ENGINE is not None and _OCR_ENGINE_LANG == lang:
        return _OCR_ENGINE
    import winrt.windows.media.ocr as ocr_mod
    engine = None
    if lang and lang != "auto":
        from winrt.windows.globalization import Language
        try:
            engine = ocr_mod.OcrEngine.try_create_from_language(Language(lang))
        except Exception:
            engine = None
    if engine is None:
        engine = ocr_mod.OcrEngine.try_create_from_user_profile_languages()
    if engine is None:
        raise RuntimeError("无法创建 OCR 引擎（系统未安装任何 OCR 语言包）")
    _OCR_ENGINE = engine
    _OCR_ENGINE_LANG = lang
    return engine


def ocr_warmup():
    """预热：提前加载引擎和 WinRT 组件，消除首次识别的冷启动延迟"""
    try:
        import io
        from PIL import Image
        img = Image.new("RGB", (64, 32), "white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        t0 = time.perf_counter()
        ocr_png_bytes(buf.getvalue())
        print(f"[预热] OCR 引擎就绪（{(time.perf_counter()-t0)*1000:.0f}ms），后续识别无冷启动延迟")
    except Exception as e:
        print(f"[预热] OCR 引擎预热失败（不影响使用）: {e}")


def ocr_png_bytes(png_bytes):
    """用 Windows.Media.Ocr 识别 PNG 字节，返回文本"""
    from winrt.windows.storage.streams import DataWriter, InMemoryRandomAccessStream
    from winrt.windows.graphics.imaging import BitmapDecoder

    async def _run():
        stream = InMemoryRandomAccessStream()
        writer = DataWriter(stream)
        writer.write_bytes(bytearray(png_bytes))
        await writer.store_async()
        await writer.flush_async()
        stream.seek(0)
        decoder = await BitmapDecoder.create_async(stream)
        bitmap = await decoder.get_software_bitmap_async()

        engine = _get_ocr_engine(CFG.get("ocr_language", "auto"))
        result = await engine.recognize_async(bitmap)
        lines = []
        for line in result.lines:
            lines.append(" ".join(w.text for w in line.words))
        return "\n".join(lines)

    with _OCR_LOCK:
        return asyncio.run(_run())


def enhance_for_ocr(pil_img):
    """小图/模糊图增强：放大 + 灰度 + 对比度拉伸，显著提升 OCR 识别率"""
    from PIL import Image, ImageOps
    w, h = pil_img.size
    # 小图放大（文字像素太少是识别不准的主因）
    scale = 1
    longest = max(w, h)
    if longest < 400:
        scale = 4
    elif longest < 800:
        scale = 3
    elif longest < 1400:
        scale = 2
    if scale > 1:
        pil_img = pil_img.resize((w * scale, h * scale), Image.LANCZOS)
    # 灰度 + 自动对比度（对深色主题代码截图效果明显）
    pil_img = pil_img.convert("L")
    pil_img = ImageOps.autocontrast(pil_img, cutoff=1)
    return pil_img


def ocr_pil_image(pil_img, verbose=True):
    """OCR 一张 PIL 图像，返回识别文本（失败抛异常）。verbose=False 时不打印增强日志"""
    import io
    if CFG.get("ocr_enhance", True):
        t0 = time.perf_counter()
        before = pil_img.size
        pil_img = enhance_for_ocr(pil_img)
        cost = (time.perf_counter() - t0) * 1000
        if verbose and pil_img.size != before:
            print(f"[增强] {before[0]}x{before[1]} → {pil_img.size[0]}x{pil_img.size[1]}（{cost:.0f}ms）")
    buf = io.BytesIO()
    pil_img.convert("RGB").save(buf, format="PNG")
    return ocr_png_bytes(buf.getvalue()).strip()


def extract_code(text, pattern):
    """从 OCR 文本中按正则提取目标内容（如房间代码）。
    先去除空白/常见干扰符号并转大写，提高对 'IYK 210' 这类识别结果的容错。"""
    import re
    if not text:
        return None
    cleaned = re.sub(r"[\s\-_.,:;|/\\'\"`~!@#$%^&*()+=\[\]{}<>]+", "", text).upper()
    m = pattern.search(cleaned)
    return m.group(0) if m else None


# ---------------- 屏幕框选（F8 备用方式） ----------------

def enable_dpi_awareness():
    """让进程 DPI 感知：tk 坐标与物理像素 1:1，选择框才能真正铺满全屏。
    必须在创建任何 Tk 窗口之前调用。"""
    try:
        # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 (-4)
        ctypes.windll.user32.SetProcessDpiAwarenessContext(-4)
    except Exception:
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PER_MONITOR_AWARE
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass


def grab_virtual_screen():
    """截取整个虚拟屏幕（所有显示器），返回 (PIL图像, monitor信息，物理像素坐标)"""
    import mss
    from PIL import Image
    with mss.MSS() as sct:
        mon = sct.monitors[0]  # 整个虚拟屏幕
        shot = sct.grab(mon)
        img = Image.frombytes("RGB", shot.size, shot.rgb)
    return img, mon


class RegionSelector:
    """全屏覆盖层（覆盖所有显示器），鼠标拖拽框选区域。
    依赖进程 DPI 感知：画布坐标 == 物理像素坐标，无需缩放换算。"""

    def __init__(self, root, pil_img, monitor, on_done):
        import tkinter as tk
        from PIL import ImageTk, ImageEnhance
        self.on_done = on_done
        self.pil_img = pil_img
        self.monitor = monitor
        self.start = None
        self.rect_id = None
        self.done = False

        dark = ImageEnhance.Brightness(pil_img).enhance(0.45)
        self.bg = ImageTk.PhotoImage(dark)

        self.top = tk.Toplevel(root)
        self.top.overrideredirect(True)      # 无边框，铺满整个虚拟屏幕
        self.top.attributes("-topmost", True)
        self.top.geometry(f"{monitor['width']}x{monitor['height']}+{monitor['left']}+{monitor['top']}")
        self.top.configure(cursor="crosshair")
        self.canvas = tk.Canvas(self.top, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.create_image(0, 0, image=self.bg, anchor="nw")
        self.canvas.create_text(
            monitor["width"] // 2, 40,
            text="拖拽框选区域，松开鼠标完成；按 Esc 取消",
            fill="#00FFCC", font=("Microsoft YaHei", 14, "bold"))

        self.canvas.bind("<ButtonPress-1>", self._press)
        self.canvas.bind("<B1-Motion>", self._drag)
        self.canvas.bind("<ButtonRelease-1>", self._release)
        self.top.bind("<Escape>", lambda e: self._cancel())
        self.top.focus_force()

    def _press(self, e):
        self.start = (e.x, e.y)
        self.rect_id = self.canvas.create_rectangle(
            e.x, e.y, e.x, e.y, outline="#00FFCC", width=2)

    def _drag(self, e):
        if self.rect_id and self.start:
            self.canvas.coords(self.rect_id, self.start[0], self.start[1], e.x, e.y)

    def _release(self, e):
        if self.done or not self.start:
            return
        self.done = True
        x1, y1 = self.start
        x2, y2 = e.x, e.y
        self.top.destroy()
        if abs(x2 - x1) < 5 or abs(y2 - y1) < 5:
            print("[取消] 框选区域太小")
            return
        # DPI 感知下画布坐标即物理像素坐标，直接裁剪（夹取到图像边界）
        W, H = self.pil_img.size
        px1 = max(0, min(x1, x2))
        py1 = max(0, min(y1, y2))
        px2 = min(W, max(x1, x2))
        py2 = min(H, max(y1, y2))
        cropped = self.pil_img.crop((px1, py1, px2, py2))
        self.on_done(cropped, (px1, py1, px2, py2))

    def _cancel(self):
        self.done = True
        self.top.destroy()
        print("[取消] 已取消框选")


# ---------------- 主程序 ----------------

class App:
    def __init__(self):
        import tkinter as tk
        enable_dpi_awareness()   # 必须在 Tk 之前：保证选择框铺满全屏
        self.root = tk.Tk()
        self.root.withdraw()
        self.root.title("CodePaster")

        self.armed = False               # F9 布防状态
        self.busy = False                # OCR 处理中，防止重入
        self.monitoring = False          # 区域监控开关
        self.last_code = None            # 上次提取到的代码（去重用）
        self.last_clipboard = self._safe_clipboard()
        self._last_clip_seq = self._seq()
        self.selector = None

        keyboard.add_hotkey(CFG["hotkey_screenshot"], self.system_screenshot)
        keyboard.add_hotkey(CFG["hotkey_set_region"], lambda: self.root.after(0, lambda: self.set_region_flow("region", "监控区域（房间码提取）")))
        keyboard.add_hotkey(CFG["hotkey_toggle_monitor"], self.toggle_monitor)
        keyboard.add_hotkey(CFG["hotkey_set_region_direct"], lambda: self.root.after(0, lambda: self.set_region_flow("region_direct", "直取区域（原文复制）")))
        keyboard.add_hotkey(CFG["hotkey_copy_region"], self.copy_region_now)
        keyboard.add_hotkey(CFG["hotkey_cycle_profile"], self.cycle_profile)
        keyboard.add_hotkey(CFG["hotkey_ocr"], lambda: self.root.after(0, self.start_ocr_flow))
        keyboard.add_hotkey(CFG["hotkey_arm_clipboard"], self.arm_clipboard)
        keyboard.add_hotkey(CFG["hotkey_paste_now"], lambda: threading.Thread(target=self._paste_now, daemon=True).start())
        keyboard.add_hotkey(CFG["hotkey_list_windows"], self.print_windows)
        keyboard.add_hotkey(CFG["hotkey_quit"], self.quit)

        threading.Thread(target=self._clipboard_poll, daemon=True).start()
        if CFG.get("ocr_warmup", True):
            threading.Thread(target=ocr_warmup, daemon=True).start()

        p = get_profile()
        watch = CFG.get("watch_clipboard_image", "always")
        print("=" * 62)
        print("  截屏取码 → 粘贴工具 v2 已启动")
        print(f"  当前适配档: {p['name']}  |  自动粘贴: {'开' if p['auto_paste'] else '关(安全模式)'}")
        print(f"  微信截图监听: {watch}  →  用微信截图(Alt+A)框选并确认后自动 OCR")
        print(f"  {CFG['hotkey_screenshot'].upper()}  一键系统截图(推荐)   {CFG['hotkey_cycle_profile'].upper()} 切换适配档")
        print(f"  {CFG['hotkey_set_region'].upper()}  框选监控区域   {CFG['hotkey_toggle_monitor'].upper()} 开始/停止房间码监控")
        print(f"  {CFG['hotkey_set_region_direct'].upper()}  框选直取区域   {CFG['hotkey_copy_region'].upper()} 直取区域原文→剪贴板")
        print(f"  {CFG['hotkey_ocr'].upper()}  自带框选OCR   {CFG['hotkey_arm_clipboard'].upper()} 布防下一次复制")
        print(f"  {CFG['hotkey_paste_now'].upper()} 立即投递剪贴板   {CFG['hotkey_list_windows'].upper()} 列出窗口   {CFG['hotkey_quit'].upper()} 退出")
        if CFG.get("region"):
            r = CFG["region"]
            print(f"  监控区域: 左{r['left']} 上{r['top']} 宽{r['width']} 高{r['height']}（{CFG['hotkey_toggle_monitor'].upper()} 启动）")
        if CFG.get("region_direct"):
            r = CFG["region_direct"]
            print(f"  直取区域: 左{r['left']} 上{r['top']} 宽{r['width']} 高{r['height']}（{CFG['hotkey_copy_region'].upper()} 直取）")
        print("=" * 62)

    # ---- 工具函数 ----
    def _safe_clipboard(self):
        try:
            return pyperclip.paste()
        except Exception:
            return ""

    def _seq(self):
        try:
            return win32clipboard.GetClipboardSequenceNumber()
        except Exception:
            return 0

    # ---- F6: 一键呼出系统截图 ----
    def system_screenshot(self):
        print(f"[信息] 已呼出系统截图：拖拽框选后松开鼠标，识别结果会自动进入剪贴板")
        try:
            keyboard.send("win+shift+s")
        except Exception:
            traceback.print_exc()
            print("[失败] 呼出系统截图失败，请手动按 Win+Shift+S 或用 F8")

    def cycle_profile(self):
        profiles = CFG.get("profiles") or []
        if not profiles:
            print("[失败] config.json 中没有 profiles")
            return
        CFG["active_profile"] = (int(CFG.get("active_profile", 0)) + 1) % len(profiles)
        save_config()
        p = get_profile()
        print(f"[切换] 适配档 → {p['name']}  |  目标窗口: {p['target_window'] or '(任意)'}  |  "
              f"自动粘贴: {'开' if p['auto_paste'] else '关(安全模式，手动Ctrl+V)'}")

    def print_profile_status(self):
        p = get_profile()
        print(f"[状态] 适配档: {p['name']}  自动粘贴: {'开' if p['auto_paste'] else '关(安全模式)'}")

    # ---- OCR 统一出口 ----
    def ocr_and_deliver(self, pil_img, source="截图"):
        if self.busy:
            print("[信息] 上一张图还在识别中，请稍候…")
            return
        self.busy = True
        t_start = time.perf_counter()
        try:
            try:
                text = ocr_pil_image(pil_img)
            except Exception:
                traceback.print_exc()
                print("[失败] OCR 识别出错")
                return
            t_ocr = time.perf_counter()
            if not text:
                print("[失败] 未识别到文字（尽量框选清晰、字号较大的代码）")
                return
            print(f"[信息] 识别到 {len(text)} 个字符（OCR耗时 {(t_ocr-t_start)*1000:.0f}ms）：")
            print(f"{'-' * 40}\n{text[:300]}\n{'-' * 40}")
            pyperclip.copy(text)
            self.last_clipboard = text
            self._last_clip_seq = self._seq()   # 防止自己的 copy 再次触发监听
            print(f"[信息] 文本已放入剪贴板（总耗时 {(time.perf_counter()-t_start)*1000:.0f}ms）")
            deliver(text)
        finally:
            self.busy = False

    # ---- F8: 自带框选 OCR ----
    def start_ocr_flow(self):
        if self.selector:
            return
        try:
            pil_img, monitor = grab_virtual_screen()
        except Exception:
            traceback.print_exc()
            print("[失败] 截屏出错")
            return
        print("[信息] 请在屏幕上拖拽框选代码区域…")

        def on_region(cropped, rect):
            self.selector = None
            threading.Thread(target=self.ocr_and_deliver,
                             args=(cropped, "框选区域"), daemon=True).start()

        self.selector = RegionSelector(self.root, pil_img, monitor, on_region)

    # ---- F5/F2: 框选并保存区域 ----
    def set_region_flow(self, region_key="region", label="监控区域"):
        if self.selector:
            return
        try:
            pil_img, monitor = grab_virtual_screen()
        except Exception:
            traceback.print_exc()
            print("[失败] 截屏出错")
            return
        print(f"[信息] 请框选要保存的{label}（可覆盖任意屏幕的任意位置）…")

        def on_region(cropped, rect):
            self.selector = None
            x1, y1, x2, y2 = rect
            region = {
                "left": int(monitor["left"] + x1),
                "top": int(monitor["top"] + y1),
                "width": int(x2 - x1),
                "height": int(y2 - y1),
            }
            CFG[region_key] = region
            save_config()
            print(f"[信息] {label}已保存: {region}")
            if region_key == "region":
                print(f"[提示] 按 {CFG['hotkey_toggle_monitor'].upper()} 开始自动提取"
                      f"（提取规则: {CFG.get('extract_pattern', '[A-Z0-9]{6}')}）")
            else:
                print(f"[提示] 按 {CFG['hotkey_copy_region'].upper()} 一键识别该区域原文到剪贴板")

        self.selector = RegionSelector(self.root, pil_img, monitor, on_region)

    # ---- F3: 直取区域原文 ----
    def copy_region_now(self):
        region = CFG.get("region_direct")
        if not region:
            print(f"[提示] 尚未设置直取区域，请先按 {CFG['hotkey_set_region_direct'].upper()} 框选保存")
            return
        threading.Thread(target=self._grab_region_once, daemon=True).start()

    def _grab_region_once(self):
        import mss
        from PIL import Image
        t0 = time.perf_counter()
        try:
            with mss.MSS() as sct:
                shot = sct.grab(CFG["region_direct"])
            img = Image.frombytes("RGB", shot.size, shot.rgb)
            text = ocr_pil_image(img).strip()
        except Exception:
            traceback.print_exc()
            print("[失败] 直取区域识别出错")
            return
        cost = (time.perf_counter() - t0) * 1000
        if not text:
            print(f"[直取] 该区域未识别到文字（{cost:.0f}ms）")
            return
        print(f"[直取] 识别 {len(text)} 个字符（{cost:.0f}ms）：\n{'-' * 40}\n{text[:300]}\n{'-' * 40}")
        pyperclip.copy(text)
        self.last_clipboard = text
        self._last_clip_seq = self._seq()   # 防止触发剪贴板监听
        print("[直取] 原文已复制到剪贴板，可直接 Ctrl+V")
        deliver(text)

    # ---- F4: 区域监控开关 ----
    def toggle_monitor(self):
        if self.monitoring:
            self.monitoring = False
            print("[停止] 区域监控已停止")
            return
        region = CFG.get("region")
        if not region:
            print(f"[提示] 尚未设置监控区域，请先按 {CFG['hotkey_set_region'].upper()} 框选保存")
            return
        self.monitoring = True
        print(f"[开始] 区域监控中：每 {CFG.get('region_monitor_interval', 1.0)}s 识别一次，"
              f"自动提取 {CFG.get('extract_pattern', '[A-Z0-9]{6}')} 并复制到剪贴板")
        threading.Thread(target=self._region_monitor_loop, daemon=True).start()

    def _region_monitor_loop(self):
        import re
        import mss
        from PIL import Image
        pattern = re.compile(CFG.get("extract_pattern", "[A-Z0-9]{6}"))
        region = CFG.get("region")
        while self.monitoring:
            t0 = time.perf_counter()
            try:
                with mss.MSS() as sct:
                    shot = sct.grab(region)
                img = Image.frombytes("RGB", shot.size, shot.rgb)
                text = ocr_pil_image(img, verbose=False)
                code = extract_code(text, pattern)
                if code and code != self.last_code:
                    self.last_code = code
                    pyperclip.copy(code)
                    self._last_clip_seq = self._seq()   # 防止触发剪贴板监听
                    print(f"[识别] 提取到代码: {code}  → 已复制到剪贴板")
                    deliver(code)
            except Exception:
                if self.monitoring:
                    traceback.print_exc()
            elapsed = time.perf_counter() - t0
            time.sleep(max(0.1, float(CFG.get("region_monitor_interval", 1.0)) - elapsed))

    # ---- F9: 布防 ----
    def arm_clipboard(self):
        if self.armed:
            self.armed = False
            print("[取消] 已解除剪贴板布防")
            return
        self.last_clipboard = self._safe_clipboard()
        self.armed = True
        p = get_profile()
        print(f"[布防] 已开启：现在去复制文字(Ctrl+C)或微信截图(Alt+A→确认)，"
              f"工具会自动处理并按 “{p['name']}” 档投递。再按一次 "
              f"{CFG['hotkey_arm_clipboard'].upper()} 取消。")

    # ---- 剪贴板监听（核心：微信截图 = 剪贴板里出现图片） ----
    def _clipboard_poll(self):
        while True:
            time.sleep(float(CFG.get("clipboard_poll_interval", 0.4)))
            try:
                self._check_clipboard_once()
            except Exception:
                traceback.print_exc()

    def _check_clipboard_once(self):
        seq = self._seq()
        if seq == self._last_clip_seq:
            return
        self._last_clip_seq = seq

        watch = CFG.get("watch_clipboard_image", "always")
        img = None
        if watch != "off":
            img = self._clipboard_image()
        if img is not None:
            if watch == "armed" and not self.armed:
                return  # 未布防，忽略图片
            self.armed = False
            threading.Thread(target=self.ocr_and_deliver,
                             args=(img, "剪贴板截图(微信截图)"), daemon=True).start()
            return

        # 文字变化：仅在布防状态下自动投递
        if self.armed:
            cur = self._safe_clipboard()
            if cur and cur != self.last_clipboard:
                self.last_clipboard = cur
                self.armed = False
                print(f"[触发] 检测到新复制文字（{len(cur)} 字符），开始投递…")
                deliver(cur)

    def _clipboard_image(self):
        """剪贴板里如果有图片（微信截图确认后/复制图片文件），返回 PIL 图像，否则 None"""
        from PIL import Image as PILImage, ImageGrab
        try:
            if not (win32clipboard.IsClipboardFormatAvailable(win32con.CF_DIB)
                    or win32clipboard.IsClipboardFormatAvailable(win32con.CF_BITMAP)):
                # 也支持“复制的图片文件”
                if not win32clipboard.IsClipboardFormatAvailable(win32con.CF_HDROP):
                    return None
        except Exception:
            return None
        try:
            clip = ImageGrab.grabclipboard()
        except Exception:
            return None
        if isinstance(clip, PILImage.Image):
            return clip
        if isinstance(clip, (list, tuple)):  # 复制的是图片文件
            for path in clip:
                if isinstance(path, str) and path.lower().endswith(
                        (".png", ".jpg", ".jpeg", ".bmp", ".webp")):
                    try:
                        return PILImage.open(path)
                    except Exception:
                        continue
        return None

    # ---- F10: 立即投递 ----
    def _paste_now(self):
        img = self._clipboard_image()
        if img is not None:
            self.ocr_and_deliver(img, "剪贴板截图")
            return
        cur = self._safe_clipboard()
        if not cur:
            print("[失败] 剪贴板为空")
            return
        deliver(cur)

    # ---- F11 ----
    def print_windows(self):
        print("\n--- 当前可见窗口标题 ---")
        for hwnd, title in list_visible_windows():
            print(f"  [{hwnd:>10}] {title}")
        print("------------------------\n")

    def quit(self):
        print("[信息] 正在退出…")
        keyboard.unhook_all_hotkeys()
        self.root.after(0, self.root.destroy)
        time.sleep(0.3)
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(0)

    def run(self):
        self.root.mainloop()


def main():
    if "--list" in sys.argv:
        for hwnd, title in list_visible_windows():
            print(f"[{hwnd:>10}] {title}")
        return
    app = App()
    app.run()


if __name__ == "__main__":
    main()
