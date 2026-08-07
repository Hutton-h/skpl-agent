"""SKPL Desktop Node — 轻量级 Windows 桌面自动化代理。

通过 WebSocket + JWT 连接到控制中心，接收并执行：
- 鼠标操作（click, double_click, right_click, move, drag）
- 键盘操作（type, hotkey, key_press）
- 截图（screenshot）
- 滚动（scroll）
- 等待（wait）
"""

__version__ = "0.2.0"