# desk-mcp

> **0 Trust – 100% Control | 0 Magic – 100% Transparency**

Desktop automation MCP for AI agents — screenshot, mouse, keyboard, window inspection.
Lets any MCP-capable agent (Claude, Gemini, Codex, Copilot, Vibe) see and interact
with the KpihX-Ubuntu desktop.

---

## The Problem

AI agents are blind to the desktop by default. They can read files and call APIs, but
they cannot see what is on screen, click buttons, type in forms, or react to GUI state.
`desk-mcp` bridges that gap — it exposes the desktop as a set of simple MCP tools that
any agent can call over the standard stdio transport.

```
Agent CLI  ──stdio──►  desk-mcp  ──XDG Portal──►  Screenshot
                            └───────xdotool───────►  Click / Type / Key / Scroll
                            └───────xdotool───────►  Window list & geometry
```

---

## Architecture

```
desk-mcp serve  (FastMCP, stdio transport)
│
├── screenshot()      XDG Desktop Portal  →  /usr/bin/python3 + dbus + GLib
│                     Full screen  →  optional crop (window name or {x,y,w,h})
│
├── get_windows()     xdotool search + getwindowgeometry
├── get_screen()      xdotool getdisplaygeometry + env vars
│
├── click()           xdotool mousemove + click
├── double_click()    xdotool click --repeat 2
├── right_click()     xdotool click 3
├── move_mouse()      xdotool mousemove
├── type_text()       xdotool type --delay <ms>
├── key()             xdotool key --clearmodifiers <combo>
└── scroll()          xdotool click (button 4/5/6/7)
```

**Screenshot backend:** XDG Desktop Portal via `dbus-python` + `GLib`. Works natively
on GNOME Wayland without any dialog or user interaction. Does NOT depend on
`gnome-screenshot` or `grim`.

**Input backend:** `xdotool` via XWayland. Covers all X11 and XWayland apps.
For pure Wayland-native apps (e.g. WaveTerm in native mode), mouse coordinates are
correct but window auto-detection via `get_windows()` may not see them.

---

## Install

### Prerequisites

```bash
sudo apt install xdotool python3-gi python3-dbus
```

### From PyPI

```bash
uv tool install desk-mcp
```

### Editable (development)

```bash
git clone git@github.com:KpihX/desk-mcp.git ~/Work/AI/MCPs/desk_mcp
cd ~/Work/AI/MCPs/desk_mcp
uv tool install --editable .
```

---

## Usage

### Claude Code (`~/.claude.json`)

```json
"desk-mcp": {
  "command": "/home/kpihx/.local/bin/desk-mcp",
  "args": ["serve"],
  "env": {
    "DISPLAY": ":0",
    "DBUS_SESSION_BUS_ADDRESS": "unix:path=/run/user/1000/bus",
    "XDG_RUNTIME_DIR": "/run/user/1000",
    "WAYLAND_DISPLAY": "wayland-0"
  }
}
```

> **Note:** The display env vars must be injected explicitly because Claude Code does
> not inherit the user's graphical session environment.

### Gemini (`~/.gemini/extensions/desk-mcp/gemini-extension.json`)

```json
{
  "name": "desk-mcp",
  "version": "0.2.0",
  "description": "Desktop automation MCP for Gemini — screenshot, mouse, keyboard via xdotool.",
  "mcpServers": {
    "desk-mcp": {
      "command": "/home/kpihx/.local/bin/desk-mcp",
      "args": ["serve"],
      "env": {}
    }
  }
}
```

### CLI test

```bash
desk-mcp status        # check environment and tool availability
desk-mcp screenshot    # take a test screenshot and print the path
desk-mcp serve         # start the MCP server (stdio)
```

---

## Tools

| Tool | Description |
|------|-------------|
| `screenshot` | Full screen or cropped to window name / region `{x,y,w,h}` |
| `get_windows` | List all XWayland-visible windows with IDs and geometry |
| `get_screen` | Screen resolution, session type, display vars |
| `click` | Left / right / middle click at `(x, y)` |
| `double_click` | Double-click at `(x, y)` |
| `right_click` | Right-click at `(x, y)` — opens context menu |
| `move_mouse` | Move mouse without clicking |
| `type_text` | Type text at current keyboard focus |
| `key` | Press key combo: `"ctrl+c"`, `"Return"`, `"super"`, `"alt+F4"` |
| `scroll` | Scroll up/down/left/right at `(x, y)` |

---

## Repos

- **GitHub:** https://github.com/KpihX/desk-mcp
- **GitLab:** https://gitlab.com/kpihx/desk-mcp
- **PyPI:** https://pypi.org/project/desk-mcp/
