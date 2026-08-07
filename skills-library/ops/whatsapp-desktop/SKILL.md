---
name: whatsapp-desktop
description: Send messages through the WhatsApp Desktop client via GUI automation with the desktop tool. For personal accounts on machines where WhatsApp Desktop is installed and logged in, without Cloud API credentials.
version: 1.0.0
category: ops
when_to_use: User asks to send results or reports to their own WhatsApp and the machine has WhatsApp Desktop installed and logged in, or asks for desktop WhatsApp automation.
---

# WhatsApp Desktop Skill — 桌面端 WhatsApp 自动发送

## Goal
Deliver a user-specified message to a user-specified contact through the WhatsApp Desktop client, using the agent's **desktop** tool (screenshot-grounded coordinate clicking + keyboard), then verify delivery with a screenshot.

## Available Tool — 唯一可用工具
The agent-facing tool is **`desktop`** (requires a connected desktop node). Supported actions:

| action | params | purpose |
|--------|--------|---------|
| `screenshot` | `quality?`, `region?` | See the screen; locate UI elements by coordinates |
| `click` / `double_click` / `right_click` | `x`, `y`, `button?`, `clicks?` | Click at coordinates |
| `type` | `text`, `interval?` | Type text into the focused field |
| `key_press` | `key` | Press one key (`enter`, `tab`, `escape`, …) |
| `hotkey` | `keys` (list) | Key combo, e.g. `['win', 'r']`, `['ctrl', 'v']` |
| `move` / `drag` / `scroll` | coordinates / `clicks` | Mouse movement |
| `wait` | `duration` | Seconds |

There is NO `list_windows` / `focus_window` / `extract_ui_tree` tool. All element location is done visually: `screenshot` → identify coordinates → `click`. 没有窗口管理/UI树工具，一切通过截图定位坐标。

**Division of labor with send_notification:** when WhatsApp Cloud API credentials are configured, ALWAYS prefer `send_notification` (stable, no GUI dependency). 有 Cloud API 凭据时优先用 send_notification。Use THIS skill only for personal accounts without API credentials. 桌面自动化仅用于无 API 凭据的个人号场景。

## Prerequisites — 前置检查
Do BOTH checks before touching WhatsApp; if either fails, STOP and tell the user:
1. Desktop node connected: call `desktop` with `action=screenshot`. If it errors (no node / permission denied), STOP — ask the user to start/connect the desktop node first. 先截屏确认桌面节点在线。
2. WhatsApp Desktop installed AND logged in: after opening it (Step 1), a QR-code login screen means NOT logged in — ask the user to scan it first. 出现二维码说明未登录。

## Workflow

### Step 1: Open WhatsApp — 启动/唤起窗口
There is no "open app" action, so drive the Windows Run dialog:
1. `hotkey` `['win', 'r']` → `wait` 1s
2. `type` text `whatsapp:` → `key_press` `enter`
3. `wait` 6–8s for the client to load, then `screenshot` to confirm the WhatsApp window is in front showing the chat list. 用 Win+R 运行 whatsapp: 协议唤起客户端。

### Step 2: Locate the contact — 定位联系人
1. `screenshot`; find the search box at the top of the chat list (放大镜图标旁的输入框) and note its center coordinates.
2. `click` the search box, then `type` the contact name EXACTLY as the user gave it. 截图定位搜索框→点击→输入联系人名。
3. `wait` 2s for results, `screenshot` again, click the matching contact row (prefer exact match; if several candidates, pick the first and say so). The chat opens.

### Step 3: Send the message — 输入并发送
1. `screenshot`; find the message input box at the bottom (消息输入框) and `click` it.
2. `type` the message text. Long messages: split into paragraph-sized segments; use Shift+Enter (`hotkey` `['shift', 'enter']`) for line breaks inside one message, Enter only at the end. 长消息分段，段内换行用 Shift+Enter。
3. `key_press` `enter` to send. Do NOT touch any other chat, group, or broadcast list.

### Step 4: Verify — 截图验证
1. `wait` 2s, then `screenshot` the chat area.
2. Confirm the LAST message bubble (outgoing, right-aligned) contains the text just sent. 确认最后一条发出气泡存在。
3. Report success to the user, and mention the message went out from their personal WhatsApp Desktop.

## Failure Handling — 失败处理
- Screenshot too ambiguous to locate an element: retry ONCE with a fresh screenshot. 截图看不清允许重试一次。
- Still failing: STOP, do not keep clicking blindly. Tell the user automation could not complete and hand over the exact message text so they can send it manually. 仍失败则停止盲点击，给出消息文本请用户手动发送。
- Contact not found in search results: do NOT guess a similar name — report back and ask the user to confirm the contact name. 找不到联系人不要猜。
- WhatsApp window lost focus mid-flow (another app popped up): re-run Step 1 (`whatsapp:` re-raises the existing window) instead of clicking taskbar coordinates. 窗口失焦时重新执行 Step 1 唤回。

## Compliance — 合规
- Send ONLY to the contact(s) and the content the user explicitly specified in this conversation. 只发用户本人明确指定的联系人和内容。
- NO bulk / broadcast messaging, NO marketing blasts, NO messaging contacts scraped from elsewhere. 禁止批量群发。
- The user's own account is used; make clear in your reply that the message went out from their personal WhatsApp.
