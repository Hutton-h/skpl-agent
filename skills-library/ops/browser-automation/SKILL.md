---
name: browser-automation
description: Browser automation for logged-in operations, form filling, paginated scraping, and screenshots. Drives a real Chromium via Playwright when a task needs JS rendering, interaction, or session state that plain HTTP scraping cannot provide.
version: 1.0.0
category: ops
when_to_use: User asks to operate a real browser — auto-login, clicking, form filling, scraping pages that require JS rendering or an authenticated session, or taking webpage screenshots.
---

# Browser Automation Skill — 浏览器自动化

## Goal
Drive a real Chromium browser (Playwright) to complete interactive web tasks — login, clicking, form filling, paginated scraping, screenshots — and deliver screenshot PNGs plus structured data files (json/csv) the user can download.

## Available Tools
RunPython, Write.

There is no dedicated browser tool: every action runs through a Playwright script that you Write to the workspace and execute with RunPython.

**Division of labor with the firecrawl skill:** static content scraping goes to firecrawl (faster, cheaper, no browser). 静态抓取用 firecrawl。Use THIS skill only when the page needs JS rendering, an authenticated session, or real interaction (click / scroll / fill / paginate). 需 JS 渲染、登录态或交互才用本技能。

## Workflow

### Step 1: Environment check — 环境检测
Run this first with RunPython:

```python
try:
    import playwright  # noqa: F401
    print("playwright OK")
except ImportError:
    import subprocess, sys
    subprocess.run([sys.executable, "-m", "pip", "install", "playwright"], check=True)
    subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
    print("playwright installed")
```

If installation fails (no network, permission denied), STOP and tell the user what to install manually.

### Step 2: Write the Playwright script — 写脚本到 workspace
Write a `.py` script into the workspace. Default template:

```python
import json, os
from pathlib import Path
from playwright.sync_api import sync_playwright

WORKSPACE = Path(os.environ.get("SKPL_WORKSPACE", "."))
STATE = WORKSPACE / "browser-state.json"  # 登录态文件，跨运行复用

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)  # 可见模式优先：业务场景用户要看
    ctx = browser.new_context(storage_state=str(STATE) if STATE.exists() else None)
    page = ctx.new_page()
    page.goto("https://example.com")
    page.wait_for_selector("css-selector-here")  # 显式等待，禁止 time.sleep 猜时长
    # ... fill / click / scrape ...
    ctx.storage_state(path=str(STATE))           # 保存登录态供下次复用
    page.screenshot(path=str(WORKSPACE / "result.png"), full_page=True)
    browser.close()
```

Script rules:
- `headless=False` visible mode by default — in business scenarios the user wants to watch and, if a login captcha appears, solve it personally. 可见模式优先。Use `headless=True` only when the user explicitly asks for background runs.
- Reuse login state: save/load `storage_state` (cookies + localStorage) so the user logs in once manually, later runs reuse it. storage_state 复用登录态。
- Always `wait_for_selector` / `wait_for_url` explicit waits; never guess with fixed sleeps.
- Paginated scraping: loop "next page" until the selector disappears or the user's limit is hit; accumulate rows in memory.

### Step 3: Execute — RunPython 执行
Run the script with RunPython. Screenshots and data MUST be written under the `SKPL_WORKSPACE` directory so the user can reach them. 截图与数据存到 workspace。

### Step 4: Deliverables — 产出
- Screenshots as `.png`, scraped data as `.json` or `.csv` in the workspace.
- Report the exact file paths and tell the user the files are downloadable from the conversation. 提示用户在对话中下载。
- Summarize what was done in 2-4 bullets (pages visited, rows collected, screenshots taken).

## Quality Rules
- **Compliance first**: never bypass captchas, paywalls, or anti-bot systems; respect the target site's robots.txt and terms of service. 禁止绕过验证码/付费墙；遵守目标站 robots 与条款。If the site blocks automation, STOP and tell the user.
- Login credentials come from the user or a stored `storage_state`; never hardcode passwords in scripts.
- On failure: take a screenshot FIRST (evidence of the page state), then retry once. 失败先截图留证再重试一次。If it still fails, report the screenshot path and the error to the user.
- Keep the browser session short; close the browser in a `finally` / context manager so no orphan Chromium processes remain.
