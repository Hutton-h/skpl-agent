---
name: desktop
description: Desktop automation skill — control keyboard, mouse, capture screenshots, extract UI accessibility trees, and manage application windows across Windows, macOS, and Linux.
version: 1.0.0
category: system
when_to_use: User asks to automate local desktop interactions — typing or key combos, mouse clicks/scrolls, taking screenshots, inspecting UI elements via the accessibility tree, or managing application windows.
---

# Desktop Automation Skill

Provides cross-platform desktop control for SKPL Agent through:

1. **Keyboard Control** — Type text, press key combinations, hold/release keys
2. **Mouse Control** — Move, click, double-click, right-click, drag, scroll
3. **Screen Capture** — Take screenshots of full screen, specific windows, or regions
4. **UI Tree Extraction** — Extract accessibility tree for element detection (UI-TARS grounding)
5. **Window Management** — List, focus, resize, minimize, close application windows

## Dependencies

- **Windows**: `pywin32`, `pyautogui`, `uiautomation`
- **macOS**: `pyobjc`, `Quartz`
- **Linux**: `python3-xlib`, `xdotool`

## Tools

| Tool | Description |
|------|-------------|
| `keyboard_type` | Type text or press key combinations |
| `mouse_move` | Move mouse to coordinates |
| `mouse_click` | Click at position |
| `mouse_scroll` | Scroll at position |
| `screenshot` | Capture screen or window |
| `extract_ui_tree` | Extract accessibility tree |
| `list_windows` | List open application windows |
| `focus_window` | Focus a specific window |