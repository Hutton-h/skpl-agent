# SKPL Agent — Desktop Node Deployment Guide

This guide covers installing, configuring, starting, and troubleshooting the
SKPL desktop automation node on Windows.

## Overview

The desktop node is a lightweight agent that runs on a Windows machine and
connects to the SKPL control center via WebSocket. It executes desktop
automation actions (click, type, screenshot, OCR) on behalf of the control
center.

```
┌──────────────────────┐       WebSocket (TLS + JWT)       ┌──────────────────┐
│   Desktop Node       │ ◄─────────────────────────────────► │  Control Center  │
│   (Windows)          │                                     │  (Linux)         │
│                      │                                     │                  │
│  - Execute actions   │                                     │  - Schedule      │
│  - Capture screen    │                                     │  - Orchestrate   │
│  - OCR recognition   │                                     │  - API           │
│  - Heartbeat         │                                     │  - Monitor       │
└──────────────────────┘                                     └──────────────────┘
```

## Prerequisites

### Hardware

- **CPU**: x86_64, 2+ cores
- **RAM**: 4GB minimum (8GB recommended for OCR)
- **GPU**: Optional, for grounding model (CUDA-compatible NVIDIA GPU)
- **Display**: Required for GUI automation

### Software

- **Windows**: Windows 10/11 or Windows Server 2019/2022
- **Python**: 3.11 or later
- **Display**: Desktop must be logged in and unlocked for GUI automation

## Installation

### Option 1: Direct Installation

```powershell
# Clone the repository
git clone https://github.com/skpl-agent/skpl-agent.git
cd skpl-agent

# Create a virtual environment
python -m venv venv
.\venv\Scripts\activate

# Install with desktop dependencies
pip install -e ".[desktop]"

# Optional: Install OCR support
pip install -e ".[desktop-ocr]"

# Optional: Install GPU grounding support
pip install -e ".[desktop-grounding]"
```

### Option 2: Docker (Windows Container)

```powershell
# Build the desktop node image
docker build -f Dockerfile.desktop-node -t skpl-agent/desktop-node .

# Run the container
docker run --rm -it `
  -e SKPL_DESKTOP_WS_HOST=your-control-center `
  -e SKPL_DESKTOP_WS_PORT=8001 `
  -e SKPL_DESKTOP_JWT_SECRET=your-secret `
  skpl-agent/desktop-node
```

## Configuration

All configuration is done through environment variables with the `SKPL_DESKTOP_`
prefix. Create a `.env` file or set them in your shell.

### Required

| Variable | Description | Example |
|----------|-------------|---------|
| `SKPL_DESKTOP_WS_HOST` | Control center hostname or IP | `control-center.example.com` |
| `SKPL_DESKTOP_WS_PORT` | Control center WebSocket port | `8001` |
| `SKPL_DESKTOP_JWT_SECRET` | JWT secret for authentication | `your-secret-key-here` |

### Optional

| Variable | Default | Description |
|----------|---------|-------------|
| `SKPL_DESKTOP_WS_HEARTBEAT_INTERVAL` | `10` | Heartbeat interval in seconds |
| `SKPL_DESKTOP_WS_RECONNECT_BACKOFF_BASE` | `1.0` | Base for exponential backoff (seconds) |
| `SKPL_DESKTOP_WS_RECONNECT_BACKOFF_MAX` | `60.0` | Max backoff time (seconds) |
| `SKPL_DESKTOP_WS_TOKEN_EXPIRY` | `3600` | JWT token expiry in seconds |
| `SKPL_DESKTOP_ACTION_TIMEOUT` | `30` | Default action timeout (seconds) |
| `SKPL_DESKTOP_SCREENSHOT_TIMEOUT` | `10` | Screenshot timeout (seconds) |
| `SKPL_DESKTOP_OCR_TIMEOUT` | `30` | OCR timeout (seconds) |
| `SKPL_DESKTOP_OCR_ENABLED` | `true` | Enable OCR support |
| `SKPL_DESKTOP_OCR_LANG` | `ch` | OCR language (ch, en, etc.) |
| `SKPL_DESKTOP_GROUNDING_MODEL` | `microsoft/OmniParser-v2` | Grounding model name |
| `SKPL_DESKTOP_GROUNDING_DEVICE` | `cpu` | Grounding device (cpu, cuda, mps) |
| `SKPL_DESKTOP_RATE_LIMIT_PER_MINUTE` | `60` | Max actions per minute |
| `SKPL_DESKTOP_RATE_LIMIT_BURST` | `10` | Max burst actions |

## Starting the Node

### Direct

```powershell
# Activate virtual environment
.\venv\Scripts\activate

# Start the desktop node
python -m skpl_agent.desktop_node serve
```

### As a Windows Service

Create a Windows service to keep the node running after logout:

```powershell
# Using NSSM (Non-Sucking Service Manager)
nssm install SKPLDesktopNode "C:\path\to\venv\Scripts\python.exe" `
  "-m skpl_agent.desktop_node serve"
nssm set SKPLDesktopNode AppDirectory "C:\path\to\skpl-agent"
nssm set SKPLDesktopNode Start SERVICE_AUTO_START
nssm start SKPLDesktopNode
```

### On Startup

Add to Windows Task Scheduler:

1. Open **Task Scheduler**
2. Create **Basic Task**
3. Trigger: **When the computer starts**
4. Action: **Start a program**
5. Program: `C:\path\to\venv\Scripts\python.exe`
6. Arguments: `-m skpl_agent.desktop_node serve`
7. Start in: `C:\path\to\skpl-agent`

## Verifying the Connection

Once the node is running, you should see it appear in the control center:

1. Open the SKPL frontend
2. Navigate to **Desktop Agents**
3. The node should appear with status **Online**
4. You should see the node's hostname, OS, and version

### Logs

The node logs to stdout by default. Expected startup output:

```
[INFO] Desktop node starting...
[INFO] Connecting to control center at your-server:8001
[INFO] WebSocket connected
[INFO] Node registered as node-xxxx
[INFO] Heartbeat loop started (interval=10s)
```

## Supported Actions

| Action | Description | Parameters |
|--------|-------------|------------|
| `click` | Mouse click at coordinates | x, y, button (left/right/middle) |
| `double_click` | Double click at coordinates | x, y |
| `type` | Type text | text, interval (ms between keystrokes) |
| `scroll` | Scroll mouse wheel | clicks (positive=up, negative=down) |
| `screenshot` | Capture screen | region (x,y,w,h), format (png/jpeg) |
| `ocr` | Extract text from screen region | region (x,y,w,h), language |
| `drag` | Drag from one point to another | from_x, from_y, to_x, to_y |
| `hotkey` | Press key combination | keys (e.g., "ctrl+c") |
| `wait` | Wait for specified duration | seconds |
| `move` | Move mouse to coordinates | x, y |
| `get_position` | Get current mouse position | — |
| `get_screen_size` | Get screen dimensions | — |

## Security Considerations

### Authentication

The desktop node uses JWT tokens for authentication. The token is signed with
the shared secret configured in `SKPL_DESKTOP_JWT_SECRET`. Both the control
center and the node must use the same secret.

### Network Security

- **Always use TLS** in production. The control center should be behind a
  reverse proxy (nginx) with TLS termination.
- **Firewall rules**: The node only needs outbound access to the control
  center's WebSocket port. No inbound ports are required.
- **VPN**: For remote nodes, use a VPN to secure the connection.

### Action Whitelisting

The control center can configure which actions are allowed per node. This is
managed through the quota and permission system.

## Troubleshooting

### Node won't connect

```powershell
# Check network connectivity
Test-NetConnection -ComputerName your-control-center -Port 8001

# Check if the control center is running
curl http://your-control-center:8000/health

# Check JWT secret matches
echo $env:SKPL_DESKTOP_JWT_SECRET
```

### Actions fail with timeout

- Increase `SKPL_DESKTOP_ACTION_TIMEOUT`
- Check if the desktop is locked (GUI actions require unlocked desktop)
- Verify the application window is visible and not minimized

### Screenshot is black

- This happens when connected via RDP with no active session
- Use a physical display or configure the RDP session to stay active
- Consider using a virtual display driver

### OCR fails

- Install OCR dependencies: `pip install -e ".[desktop-ocr]"`
- Check `SKPL_DESKTOP_OCR_ENABLED=true`
- Verify the correct language is set in `SKPL_DESKTOP_OCR_LANG`

### Node marked as offline

- Check heartbeat interval: `SKPL_DESKTOP_WS_HEARTBEAT_INTERVAL`
- The control center marks nodes offline after `node_max_offline_seconds`
- Check network stability and firewall rules

### High CPU usage

- Reduce `SKPL_DESKTOP_WS_HEARTBEAT_INTERVAL` (less frequent heartbeats)
- Disable OCR if not needed: `SKPL_DESKTOP_OCR_ENABLED=false`
- Use CPU grounding device: `SKPL_DESKTOP_GROUNDING_DEVICE=cpu`

## Uninstalling

```powershell
# Stop the service
nssm stop SKPLDesktopNode
nssm remove SKPLDesktopNode confirm

# Remove the virtual environment
Remove-Item -Recurse -Force .\venv

# Remove the repository
Remove-Item -Recurse -Force .\skpl-agent
```

## Docker Uninstall

```powershell
# Stop and remove the container
docker stop skpl-desktop-node
docker rm skpl-desktop-node

# Remove the image
docker rmi skpl-agent/desktop-node
```