# -*- coding: utf-8 -*-
"""冒烟测试：启动主程序 3 秒后自动退出，并验证目标窗口匹配"""
import sys
import threading

sys.path.insert(0, ".")
import code_paster

# 验证窗口匹配（用真实存在的窗口关键字测试）
for kw in ["QQ", "微信", "不存在的窗口xyz"]:
    hwnd, title = code_paster.find_target_window(kw)
    print(f"关键字 {kw!r} -> hwnd={hwnd}, title={title!r}")

app = code_paster.App()
app.root.after(3000, lambda: (print("smoke ok, quitting"), threading.Thread(target=app.quit, daemon=True).start()))
app.run()
print("app exited cleanly")
