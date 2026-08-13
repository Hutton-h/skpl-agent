"""Desktop Node WebSocket + One-Click Installer Download API"""
import base64 as _b64
import secrets
import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import Response

logger = logging.getLogger(__name__)

_active_tokens: set[str] = set()
_connected_nodes: dict[str, dict] = {}

install_router = APIRouter(prefix="/api/desktop", tags=["desktop-node"])


def _generate_install_token() -> str:
    token = secrets.token_urlsafe(32)
    _active_tokens.add(token)
    return token


def _get_server_url(request: Request) -> str:
    scheme = request.headers.get("x-forwarded-proto", "http")
    host = request.headers.get("host", "localhost:8000")
    return f"{scheme}://{host}"


_NODE_PY_TEMPLATE = """import json, time, logging, os, sys
import websocket

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("desktop-node")

SERVER_URL = "{server_url}/ws/desktop/{token}"
TOKEN = "{token}"
RECONNECT_DELAY = 5

def on_message(ws, message):
    try:
        data = json.loads(message)
        action = data.get("action", "")
        req_id = data.get("request_id", "")
        if action == "ping":
            ws.send(json.dumps({"type": "pong", "request_id": req_id}))
            return
        if action == "screenshot":
            import mss, base64, io
            with mss.mss() as sct:
                img = sct.grab(sct.monitors[1])
                buf = io.BytesIO()
                import mss.tools
                mss.tools.to_png(img.rgb, img.size, output=buf)
                b64 = base64.b64encode(buf.getvalue()).decode()
            ws.send(json.dumps({"type": "screenshot", "request_id": req_id, "data": b64}))
            return
        if action == "click":
            import pyautogui
            pyautogui.click(data.get("x", 0), data.get("y", 0))
            ws.send(json.dumps({"type": "done", "request_id": req_id}))
            return
        if action == "type":
            import pyautogui, pyperclip
            pyperclip.copy(data.get("text", ""))
            pyautogui.hotkey("ctrl", "v")
            ws.send(json.dumps({"type": "done", "request_id": req_id}))
            return
        if action == "key":
            import pyautogui
            pyautogui.hotkey(*data.get("keys", "").split("+"))
            ws.send(json.dumps({"type": "done", "request_id": req_id}))
            return
        if action == "move":
            import pyautogui
            pyautogui.moveTo(data.get("x", 0), data.get("y", 0))
            ws.send(json.dumps({"type": "done", "request_id": req_id}))
            return
        if action == "scroll":
            import pyautogui
            pyautogui.scroll(data.get("amount", 0))
            ws.send(json.dumps({"type": "done", "request_id": req_id}))
            return
        if action == "drag":
            import pyautogui
            pyautogui.moveTo(data.get("x1", 0), data.get("y1", 0))
            pyautogui.drag(data.get("x2", 0)-data.get("x1", 0), data.get("y2", 0)-data.get("y1", 0))
            ws.send(json.dumps({"type": "done", "request_id": req_id}))
            return
        if action == "get_position":
            import pyautogui
            x, y = pyautogui.position()
            ws.send(json.dumps({"type": "position", "request_id": req_id, "x": x, "y": y}))
            return
        if action == "get_screen_size":
            import pyautogui
            w, h = pyautogui.size()
            ws.send(json.dumps({"type": "screen_size", "request_id": req_id, "width": w, "height": h}))
            return
        ws.send(json.dumps({"type": "error", "request_id": req_id, "message": f"Unknown: {action}"}))
    except Exception as e:
        log.error(f"Error: %s" % e)

def on_error(ws, error):
    log.error(f"WS Error: %s" % error)

def on_close(ws, code, msg):
    log.warning("Disconnected, reconnecting...")
    time.sleep(RECONNECT_DELAY)
    connect()

def on_open(ws):
    log.info("Connected to control center")
    ws.send(json.dumps({"type": "register", "hostname": os.environ.get("COMPUTERNAME", "unknown"), "token": TOKEN}))

def connect():
    log.info("Connecting...")
    ws = websocket.WebSocketApp(SERVER_URL, on_open=on_open, on_message=on_message, on_error=on_error, on_close=on_close)
    ws.run_forever(ping_interval=30, ping_timeout=10)

if __name__ == "__main__":
    connect()
"""


@install_router.get("/install-token")
async def get_install_token(request: Request):
    token = _generate_install_token()
    server_url = _get_server_url(request)
    return {
        "token": token,
        "server_url": server_url,
        "download_url": f"{server_url}/api/desktop/download-installer?token={token}",
    }


@install_router.get("/download-installer")
async def download_installer(request: Request, token: str = ""):
    if token and token not in _active_tokens:
        return Response(
            content='echo Token Error & pause',
            media_type="application/octet-stream",
            status_code=403,
        )
    server_url = _get_server_url(request)
    bat_content = _build_installer_bat(server_url, token)
    return Response(
        content=bat_content,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": 'attachment; filename="SKPL-Setup.bat"',
            "Content-Type": "application/octet-stream; charset=gbk",
        },
    )


def _build_installer_bat(server_url: str, token: str) -> str:
    # Use replace() instead of format() because the template contains
    # Python dict braces and f-string braces that would break .format().
    node_py = _NODE_PY_TEMPLATE.replace('{server_url}', server_url).replace('{token}', token)
    node_b64 = _b64.b64encode(node_py.encode("utf-8")).decode("ascii")

    return f"""@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
title SKPL Setup

echo.
echo ========================================
echo    SKPL Desktop Node - Auto Install
echo ========================================
echo.
echo    Fully automatic, no input needed
echo ========================================
echo.

:: 1. Check Python
echo [1/5] Checking Python...
set PYCMD=
python --version >nul 2>&1 && (set PYCMD=python & goto :pyok)
py -3 --version >nul 2>&1 && (set PYCMD=py -3 & goto :pyok)
echo    Downloading Python...
set PI=%TEMP%\\python-installer.exe
curl -L -o "%PI%" "https://www.python.org/ftp/python/3.12.4/python-3.12.4-amd64.exe" 2>nul
if not exist "%PI%" powershell -Command "Invoke-WebRequest 'https://www.python.org/ftp/python/3.12.4/python-3.12.4-amd64.exe' -OutFile '%PI%'" 2>nul
if not exist "%PI%" (echo Download failed & pause & exit /b 1)
"%PI%" /quiet InstallAllUsers=1 PrependPath=1 Include_test=0
del /q "%PI%" 2>nul
set PYCMD=python
echo    Python installed

:pyok
echo.

:: 2. Create dir
echo [2/5] Creating install directory...
set DIR=%USERPROFILE%\\skpl-desktop-node
if not exist "%DIR%" mkdir "%DIR%"
echo.

:: 3. Install deps
echo [3/5] Installing dependencies...
%PYCMD% -m pip install --quiet --upgrade pip 2>nul
%PYCMD% -m pip install --quiet websocket-client pyautogui mss pillow pyperclip keyboard 2>nul
echo    Done
echo.

:: 4. Write node.py (base64 decode)
echo [4/5] Writing node program...
echo {node_b64} > "%DIR%\\node.b64"
%PYCMD% -c "import base64; p=open(r'%DIR%\\node.b64'); d=base64.b64decode(p.read().strip()); open(r'%DIR%\\node.py','w',encoding='utf-8').write(d.decode('utf-8'))" 2>nul
del "%DIR%\\node.b64" 2>nul
set NF=%DIR%\\node.py
echo    Done
echo.

:: 5. Create shortcut
echo [5/5] Creating desktop shortcut...
set SB=%DIR%\\start.bat
(echo @echo off
echo cd /d "%DIR%"
echo title SKPL Node
echo echo SKPL Desktop Node running...
echo echo Close this window to stop
echo echo.
echo %PYCMD% "%NF%"
echo pause) > "%SB%"
powershell -Command "$s=(New-Object -ComObject WScript.Shell).CreateShortcut([Environment]::GetFolderPath('Desktop')+'\\SKPL-Node.lnk');$s.TargetPath='%SB%';$s.IconLocation='shell32.dll,13';$s.Save()" 2>nul
echo    Done
echo.

echo ========================================
echo    Install Complete!
echo    Desktop shortcut: SKPL-Node
echo ========================================
echo Starting node...
start "" "%SB%"
timeout /t 3 >nul
exit /b 0
"""


def setup_desktop_ws(app, settings):
    """Register desktop node WebSocket and installer download API."""
    app.include_router(install_router)

    @app.websocket("/ws/desktop/{token}")
    async def desktop_node_ws(websocket: WebSocket, token: str):
        if token not in _active_tokens:
            await websocket.close(code=4001, reason="invalid token")
            return

        await websocket.accept()
        node_id = None

        try:
            while True:
                raw = await websocket.receive_text()
                msg = json.loads(raw)
                msg_type = msg.get("type", "")

                if msg_type == "register":
                    node_id = msg.get("hostname", token[:8])
                    _connected_nodes[node_id] = {
                        "token": token,
                        "hostname": node_id,
                        "connected_at": datetime.now(timezone.utc).isoformat(),
                        "websocket": websocket,
                    }
                    logger.info(f"Desktop node registered: {node_id}")
                    await websocket.send_json({"type": "registered", "node_id": node_id})

                elif msg_type == "pong":
                    pass
                else:
                    logger.debug(f"Node message: {msg_type}")

        except WebSocketDisconnect:
            logger.info(f"Desktop node disconnected: {node_id or token[:8]}")
        except Exception as e:
            logger.error(f"Desktop node WS error: {e}")
        finally:
            if node_id and node_id in _connected_nodes:
                del _connected_nodes[node_id]
