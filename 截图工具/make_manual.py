# -*- coding: utf-8 -*-
"""生成《截屏取码自动粘贴工具 使用说明书》Word 文档"""
from docx import Document
from docx.shared import Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn

FONT = "微软雅黑"
ACCENT = RGBColor(0x1F, 0x6F, 0xEB)
DARK = RGBColor(0x24, 0x29, 0x2F)


def set_font(run, size=10.5, bold=False, color=None, font=FONT):
    run.font.name = font
    run.font.size = Pt(size)
    run.font.bold = bold
    if color is not None:
        run.font.color.rgb = color
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = rpr.makeelement(qn("w:rFonts"), {})
        rpr.append(rfonts)
    rfonts.set(qn("w:eastAsia"), font)


def para(doc, text, size=10.5, bold=False, color=None, align=None, space_after=4):
    p = doc.add_paragraph()
    if align is not None:
        p.alignment = align
    p.paragraph_format.space_after = Pt(space_after)
    r = p.add_run(text)
    set_font(r, size=size, bold=bold, color=color)
    return p


def heading(doc, text, level=1):
    h = doc.add_heading("", level=level)
    r = h.add_run(text)
    sizes = {0: 20, 1: 15, 2: 12.5, 3: 11}
    set_font(r, size=sizes.get(level, 11), bold=True,
             color=ACCENT if level <= 1 else DARK)
    return h


def bullet(doc, text, bold_prefix=None):
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.space_after = Pt(2)
    if bold_prefix:
        r1 = p.add_run(bold_prefix)
        set_font(r1, bold=True)
    r = p.add_run(text)
    set_font(r)
    return p


def make_table(doc, headers, rows, widths=None):
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, htext in enumerate(headers):
        cell = t.rows[0].cells[i]
        cell.text = ""
        r = cell.paragraphs[0].add_run(htext)
        set_font(r, size=10, bold=True, color=RGBColor(0xFF, 0xFF, 0xFF))
        shd = cell._element.get_or_add_tcPr().makeelement(qn("w:shd"), {
            qn("w:val"): "clear", qn("w:fill"): "1F6FEB"})
        cell._element.get_or_add_tcPr().append(shd)
    for row in rows:
        cells = t.add_row().cells
        for i, val in enumerate(row):
            cells[i].text = ""
            r = cells[i].paragraphs[0].add_run(str(val))
            set_font(r, size=10)
    if widths:
        for i, w in enumerate(widths):
            for row in t.rows:
                row.cells[i].width = Cm(w)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return t


doc = Document()
for section in doc.sections:
    section.left_margin = Cm(2.2)
    section.right_margin = Cm(2.2)

# ============ 封面标题 ============
para(doc, "截屏取码 → 自动粘贴工具", size=24, bold=True, color=ACCENT,
     align=WD_ALIGN_PARAGRAPH.CENTER, space_after=6)
para(doc, "使 用 说 明 书", size=18, bold=True,
     align=WD_ALIGN_PARAGRAPH.CENTER, space_after=10)
para(doc, "版本 v2.3　|　适用系统：Windows 10 / 11　|　编写日期：2026-10-29",
     size=10.5, color=RGBColor(0x66, 0x66, 0x66),
     align=WD_ALIGN_PARAGRAPH.CENTER, space_after=16)

# ============ 一、程序简介 ============
heading(doc, "一、程序简介", 1)
para(doc, "本工具用于把屏幕上显示的代码 / 文字（如直播画面中的无畏契约房间代码）快速变成可粘贴的文本。"
          "它通过截屏 OCR 识别屏幕内容，识别结果自动放入剪贴板，并可按「适配档」自动切换到目标应用粘贴，"
          "或保持安全模式由你手动粘贴。")
para(doc, "核心能力：", bold=True, space_after=2)
bullet(doc, "指定屏幕区域持续监控，自动提取固定格式内容（如 6 位房间码），代码一变立即复制；", "① 区域监控提取：")
bullet(doc, "指定区域一键识别全部文字原文，直接进剪贴板；", "② 区域直取：")
bullet(doc, "支持系统截图（Win+Shift+S）、微信截图（Alt+A）、工具自带框选三种取码方式，松开鼠标即自动识别；", "③ 截图自动识别：")
bullet(doc, "监听剪贴板，复制文字或截图后自动处理并投递；", "④ 剪贴板监听：")
bullet(doc, "每个目标应用一个配置档，普通应用自动粘贴，游戏走安全模式（零模拟输入，防封号）；", "⑤ 适配档体系：")
bullet(doc, "小图 / 模糊图自动增强（放大 + 灰度 + 对比度），提升识别率；端到端延迟实测约 30~110 毫秒。", "⑥ 高速低延迟：")

# ============ 二、运行环境与安装 ============
heading(doc, "二、运行环境与安装", 1)
heading(doc, "2.1 环境要求", 2)
bullet(doc, "Windows 10 / 11（64 位）；")
bullet(doc, "Python 3.10 及以上（安装时勾选 Add to PATH）；")
bullet(doc, "系统已安装 OCR 语言包（Windows 设置 → 时间和语言 → 语言 → 可选功能，含英语/中文即可，一般系统自带）。")
heading(doc, "2.2 依赖安装", 2)
para(doc, "在命令行中执行（首次使用执行一次即可）：")
para(doc, "pip install pywin32 keyboard mss pillow pyperclip pydirectinput "
          "winrt-Windows.Media.Ocr winrt-Windows.Graphics.Imaging "
          "winrt-Windows.Storage.Streams winrt-Windows.Foundation "
          "winrt-Windows.Foundation.Collections winrt-Windows.Globalization",
     size=9, color=RGBColor(0x33, 0x33, 0x33))
heading(doc, "2.3 启动方式", 2)
bullet(doc, "双击「启动工具.bat」（推荐）；")
bullet(doc, "或命令行进入工具目录执行：python code_paster.py；")
bullet(doc, "仅查看当前所有窗口标题：python code_paster.py --list。")
para(doc, "启动后会出现一个控制台窗口显示运行日志，请勿关闭它（关闭即退出工具）。", bold=True)

# ============ 三、快速上手 ============
heading(doc, "三、快速上手（3 步）", 1)
para(doc, "场景：把直播画面里的无畏契约房间代码（如 IYK210）提取出来，粘贴进游戏。", bold=True)
para(doc, "第 1 步：双击「启动工具.bat」启动（默认即为 VALORANT 安全模式档）。")
para(doc, "第 2 步：按 F5，在直播画面上框选「房间代码」显示的区域，松开鼠标，坐标自动保存（只需做一次）。")
para(doc, "第 3 步：按 F4 开始监控。主播一换房间码，工具自动识别并复制到剪贴板（控制台提示「提取到代码」），"
          "你切到游戏按 Ctrl+V 即可。再按 F4 停止监控。")
para(doc, "提示：所有热键都可以在 config.json 中改成你习惯的按键（支持组合键，如 ctrl+alt+s）。",
     color=RGBColor(0x66, 0x66, 0x66))

# ============ 四、热键一览表 ============
heading(doc, "四、热键一览表", 1)
make_table(doc,
    ["热键", "功能", "说明"],
    [
        ["F2", "框选并保存「直取区域」", "为「区域直取」功能设置识别区域，坐标永久保存"],
        ["F3", "区域直取", "识别直取区域的全部文字原文 → 直接进剪贴板 → Ctrl+V 粘贴"],
        ["F4", "开始 / 停止区域监控", "持续识别监控区域，按正则提取房间码，代码变化自动复制"],
        ["F5", "框选并保存「监控区域」", "为「房间码提取」功能设置识别区域，坐标永久保存"],
        ["F6", "一键系统截图", "呼出 Win+Shift+S，框选松开后自动 OCR 并投递"],
        ["F7", "切换适配档", "在 VALORANT安全模式 / 微信 / QQ / 通用 之间循环切换"],
        ["F8", "自带框选 OCR", "不依赖截图软件，工具自己全屏框选识别（覆盖所有显示器）"],
        ["F9", "剪贴板布防", "布防后下一次复制（文字或截图）自动投递；再按一次取消"],
        ["F10", "立即投递剪贴板", "剪贴板是图片就 OCR，是文字就直接按当前适配档投递"],
        ["F11", "列出窗口标题", "控制台打印所有可见窗口，用于确定 target_window 关键字"],
        ["F12", "退出", "退出工具"],
    ],
    widths=[1.6, 4.2, 9.5])
para(doc, "注：选择框覆盖整个虚拟屏幕（所有显示器），高分屏 / 缩放屏已做 DPI 适配，可框选屏幕任意位置。",
     color=RGBColor(0x66, 0x66, 0x66))

# ============ 五、功能详解 ============
heading(doc, "五、功能详解", 1)

heading(doc, "5.1 功能一：房间码提取（F5 设区域 + F4 监控）", 2)
para(doc, "适合直播画面里持续显示的固定格式内容（如无畏契约房间代码 IYK210）。")
para(doc, "操作流程：")
bullet(doc, "按 F5 → 屏幕变暗进入框选 → 拖拽框住代码显示区域 → 松开鼠标，坐标自动保存到 config.json；")
bullet(doc, "按 F4 开始监控：工具每 1 秒（可配置）截取该区域一次 → OCR 识别 → 按正则提取代码；")
bullet(doc, "提取到新代码时自动复制到剪贴板，控制台提示「提取到代码: XXXXXX」；同一代码不会重复复制；")
bullet(doc, "再按 F4 停止监控。")
para(doc, "提取规则（extract_pattern）可自定义：", bold=True)
make_table(doc,
    ["目标内容", "正则写法"],
    [
        ["6 位大写字母 + 数字（房间码，默认）", "[A-Z0-9]{6}"],
        ["8 位字母数字码", "[A-Z0-9]{8}"],
        ["6 位纯数字", "[0-9]{6}"],
        ["字母开头 + 5 位数字", "[A-Z][0-9]{5}"],
    ],
    widths=[8.5, 6.5])
para(doc, "识别容错：结果中的空格、小写、连字符等干扰会被自动清洗（如 iyk 210 → IYK210）。")

heading(doc, "5.2 功能二：区域直取（F2 设区域 + F3 一键复制）", 2)
para(doc, "适合「把某块区域的文字原样复制走」的场景，不做正则过滤，识别多少复制多少。")
bullet(doc, "按 F2 → 框选你想复制内容的区域 → 自动保存（与监控区域互相独立）；")
bullet(doc, "需要时按 F3：工具截取该区域 → OCR 识别全部文字 → 原文进剪贴板 → 直接 Ctrl+V 粘贴。")

heading(doc, "5.3 截图自动识别（F6 / 微信截图 / F8）", 2)
make_table(doc,
    ["取码方式", "操作", "特点"],
    [
        ["F6 系统截图（推荐）", "按 F6 → 拖拽框选 → 松开鼠标", "等效 Win+Shift+S，松开即进剪贴板，无需确认"],
        ["微信截图", "Alt+A → 框选 → 点 ✓ 确认", "不依赖本工具界面，确认后自动触发"],
        ["F8 自带框选", "按 F8 → 拖拽框选 → 松开鼠标", "截图软件都没开时的备用方案，覆盖所有显示器"],
    ],
    widths=[4.2, 5.6, 5.5])
para(doc, "三种方式的图片一旦进入剪贴板，工具约 30 毫秒内自动完成 OCR，识别文字替换进剪贴板，随后按当前适配档投递。")

heading(doc, "5.4 剪贴板监听（F9 布防 / F10 立即投递）", 2)
bullet(doc, "F9 布防：之后你在任意应用按一次 Ctrl+C（或完成一次截图），工具自动处理并投递；再按一次 F9 取消布防；")
bullet(doc, "F10：立刻把当前剪贴板内容投递——是图片就先 OCR 再投递，是文字就直接投递；")
bullet(doc, "能直接选中复制的文字优先用这种方式：零延迟、零识别误差。")

heading(doc, "5.5 适配档切换（F7）", 2)
para(doc, "适配档决定「识别结果如何投递」。按 F7 在以下预置档之间循环（可自定义增删）：")
make_table(doc,
    ["适配档", "目标窗口", "自动粘贴", "适用场景"],
    [
        ["VALORANT安全模式（默认）", "VALORANT", "关", "游戏：只放剪贴板，手动 Ctrl+V，零封号风险"],
        ["微信", "微信", "开", "自动切到微信窗口并粘贴"],
        ["QQ", "QQ", "开", "自动切到 QQ 窗口并粘贴"],
        ["通用自动粘贴", "（任意）", "关", "只放剪贴板，手动到任意应用粘贴"],
    ],
    widths=[4.6, 2.6, 2.2, 6.0])

# ============ 六、防封说明 ============
heading(doc, "六、适配档与无畏契约防封说明（重要）", 1)
para(doc, "反作弊系统（Vanguard）能够检测的风险行为只有一类：程序向游戏进程发送模拟按键或注入代码。因此本工具采用「安全模式」设计：", bold=True)
bullet(doc, "VALORANT 安全模式档（auto_paste: false）下，工具绝不激活游戏窗口、绝不发送任何模拟按键、绝不接触游戏进程；", "")
bullet(doc, "它做的全部事情 = 把识别出的文字放进 Windows 剪贴板；之后的 Alt+Tab 切窗口和 Ctrl+V 都是你本人的真实按键，与反作弊无关；", "")
bullet(doc, "请勿给游戏档开启 auto_paste 或 use_direct_input——那属于向游戏模拟按键的宏行为，存在封号风险；", "")
bullet(doc, "微信 / QQ / 浏览器 / 编辑器等普通应用没有反作弊，可放心使用自动粘贴。", "")
para(doc, "说明：任何第三方工具都无法替反作弊系统「打包票」，但安全模式在设计上不存在可被检测的行为，风险为零。",
     color=RGBColor(0x66, 0x66, 0x66))

# ============ 七、配置参考 ============
heading(doc, "七、config.json 完整配置参考", 1)
para(doc, "配置文件位于工具目录下，修改后重启工具生效（F7 切换适配档会自动保存）。")
make_table(doc,
    ["配置项", "默认值", "说明"],
    [
        ["profiles", "见文件", "适配档列表，每个应用一条（name / target_window / auto_paste / use_direct_input / note）"],
        ["active_profile", "0", "当前生效的适配档序号，F7 切换后自动保存"],
        ["hotkey_set_region_direct", "f2", "框选保存直取区域"],
        ["hotkey_copy_region", "f3", "直取区域原文到剪贴板"],
        ["hotkey_toggle_monitor", "f4", "开始 / 停止区域监控"],
        ["hotkey_set_region", "f5", "框选保存监控区域"],
        ["hotkey_screenshot", "f6", "一键呼出系统截图"],
        ["hotkey_cycle_profile", "f7", "切换适配档"],
        ["hotkey_ocr", "f8", "自带框选截屏 OCR"],
        ["hotkey_arm_clipboard", "f9", "剪贴板布防"],
        ["hotkey_paste_now", "f10", "立即投递剪贴板"],
        ["hotkey_list_windows", "f11", "列出窗口标题"],
        ["hotkey_quit", "f12", "退出"],
        ["region", "null", "监控区域坐标（F5 自动保存，一般无需手改）"],
        ["region_direct", "null", "直取区域坐标（F2 自动保存）"],
        ["region_monitor_interval", "1.0", "区域监控截图间隔（秒）"],
        ["extract_pattern", "[A-Z0-9]{6}", "监控提取的正则规则"],
        ["watch_clipboard_image", "always", "截图监听：always 随时自动 OCR / armed 仅布防后 / off 关闭"],
        ["ocr_language", "en-US", "OCR 语言：en-US（代码推荐）/ zh-Hans-CN / auto"],
        ["ocr_enhance", "true", "小图 / 模糊图自动增强（放大 + 灰度 + 对比度）"],
        ["ocr_warmup", "true", "启动时预热 OCR 引擎，消除首次识别冷启动延迟"],
        ["paste_delay", "0.15", "自动粘贴时，激活窗口后等待秒数再按 Ctrl+V"],
        ["clipboard_poll_interval", "0.03", "剪贴板轮询间隔（秒），检查本身零开销"],
    ],
    widths=[4.6, 2.6, 8.2])
para(doc, "所有热键均支持组合键写法，例如 \"ctrl+alt+s\"、\"shift+f4\"。",
     color=RGBColor(0x66, 0x66, 0x66))

# ============ 八、速度与识别率 ============
heading(doc, "八、速度与识别准确率提示", 1)
bullet(doc, "截图进剪贴板 → 识别文本进剪贴板，实测端到端约 30~110 毫秒；OCR 本身 9~60 毫秒（取决于截图大小）；")
bullet(doc, "框选区域越小、文字越大越清晰，识别越快越准；")
bullet(doc, "极小字号（≤10px）或严重模糊的图片，数字可能有个别误差（如 10 识别为 to），这是系统 OCR 引擎的物理极限；")
bullet(doc, "能选中复制的文字请优先用 F9 方式（零延迟、零误差），OCR 留给不可复制的画面；")
bullet(doc, "中文注释多的代码可把 ocr_language 改为 zh-Hans-CN 或 auto。")

# ============ 九、常见问题 ============
heading(doc, "九、常见问题（FAQ）", 1)
qa = [
    ("截图后工具没反应？", "确认截图是「复制到剪贴板」模式（Win+Shift+S 松开即复制；微信截图需点 ✓ 确认）；确认 watch_clipboard_image 不是 off；查看控制台日志是否有报错。"),
    ("按 F5/F2 框选时选择框太小？", "请确认运行的是最新版本（v2.3 已修复高分屏 DPI 问题，选择框覆盖整个虚拟屏幕）。若仍异常，重启工具再试。"),
    ("监控区域位置变了怎么办？", "重新按 F5 框选一次即可，新坐标自动覆盖旧坐标。"),
    ("OCR 识别不准？", "框选时贴紧文字、避免框入过多无关内容；字体放大后再截；小图会自动增强。对准确率敏感的内容优先用复制（F9）方式。"),
    ("自动粘贴不生效？", "按 F11 核对 target_window 关键字是否匹配窗口标题；目标应用若以管理员权限运行，本工具也需以管理员身份运行（右键 bat → 以管理员身份运行）。"),
    ("热键和别的软件冲突？", "在 config.json 里把对应 hotkey_* 改成不冲突的按键（支持组合键），重启工具生效。"),
    ("修改 config.json 后没生效？", "修改配置后需重启工具（F12 退出 → 重新双击 bat）。注意：工具运行中按 F7 会自动保存配置，可能覆盖你手改的内容，建议先退出工具再改配置。"),
    ("全屏独占游戏里 F6 弹不出截图？", "全屏独占模式下系统截图界面可能无法叠加，请先 Alt+Tab 切出游戏，或改用 F8 / 微信截图。"),
]
for q, a in qa:
    para(doc, "Q：" + q, bold=True, space_after=1)
    para(doc, "A：" + a, space_after=8, color=RGBColor(0x33, 0x33, 0x33))

# ============ 十、附录 ============
heading(doc, "十、附录：文件清单", 1)
make_table(doc,
    ["文件", "用途"],
    [
        ["code_paster.py", "主程序"],
        ["config.json", "配置文件（热键 / 适配档 / 区域 / 提取规则）"],
        ["启动工具.bat", "一键启动脚本"],
        ["README.md", "简明说明（本文档的精简版）"],
        ["test_ocr.py", "测试：OCR 引擎"],
        ["test_clipboard_image.py", "测试：剪贴板截图链路（会覆盖剪贴板）"],
        ["test_latency.py", "测试：端到端延迟"],
        ["test_region_extract.py", "测试：正则提取逻辑"],
        ["test_overlay.py", "测试：全屏覆盖层"],
        ["test_smoke.py", "测试：启动自检"],
        ["bench.py", "性能基准测试"],
    ],
    widths=[5.5, 9.8])
para(doc, "")
para(doc, "—— 完 ——", align=WD_ALIGN_PARAGRAPH.CENTER,
     color=RGBColor(0x99, 0x99, 0x99))

out = r"C:\Users\lf\Desktop\截图工具（lnrlxf）\使用说明书.docx"
doc.save(out)
print("saved:", out)

# ---- 校验 ----
d2 = Document(out)
heads = [p.text for p in d2.paragraphs if p.style.name.startswith("Heading")]
print("paragraphs:", len(d2.paragraphs), "tables:", len(d2.tables), "headings:", len(heads))
for h in heads:
    print(" -", h)
