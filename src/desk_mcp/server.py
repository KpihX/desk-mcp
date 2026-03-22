"""
desk-mcp server — Desktop automation tools for Claude Code.

Tools:
  screenshot   — Take a calibrated screenshot (full screen, window, or region)
  get_windows  — List all visible windows with geometry
  get_screen   — Screen info (resolution, session type)
  click        — Left/right/middle click at coordinates
  double_click — Double-click at coordinates
  move_mouse   — Move mouse without clicking
  type_text    — Type text at current focus
  key          — Press a key combo (e.g. "ctrl+c", "Return", "super")
  scroll       — Scroll at coordinates

Screenshot backend:
  XDG Desktop Portal via system python3 + dbus-python + GLib event loop.
  Works natively on GNOME Wayland — no dialog, no user interaction required.
  Requires: /usr/bin/python3 with python3-gi and python3-dbus (standard on Ubuntu).

Input simulation: xdotool (XWayland — covers X11 and XWayland apps).
For pure Wayland-native apps (e.g. WaveTerm): mouse position is still correct,
keyboard works, but window auto-detection via get_windows() may not see them.
"""

import os
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastmcp import FastMCP

# ── Init ──────────────────────────────────────────────────────────────────────

mcp = FastMCP(
    name="desk-mcp",
    instructions=(
        "Desktop automation MCP. Use screenshot() to see the screen — "
        "pass window_name to auto-crop to a specific window, or region dict "
        "{x,y,w,h} for a precise area. Use get_windows() to discover window "
        "coordinates. Use click/type_text/key for input simulation via xdotool."
    ),
)

SHOT_DIR = Path(os.environ.get("K_DESKTOP_SHOT_DIR", "/tmp/k_desktop"))
SHOT_DIR.mkdir(parents=True, exist_ok=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _run(cmd: list[str], timeout: int = 10) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def _ts() -> str:
    return datetime.now().strftime("%H%M%S_%f")[:10]


def _crop_image(src: Path, region: dict, dest: Path) -> Path:
    """Crop image to region {x, y, w, h} using Pillow."""
    from PIL import Image as PILImage
    with PILImage.open(src) as img:
        box = (region["x"], region["y"],
               region["x"] + region["w"], region["y"] + region["h"])
        # Clamp to image bounds
        box = (
            max(0, box[0]), max(0, box[1]),
            min(img.width, box[2]), min(img.height, box[3]),
        )
        if box[2] <= box[0] or box[3] <= box[1]:
            return src  # Region is outside image bounds — return uncropped
        cropped = img.crop(box)
        cropped.save(dest)
    return dest


def _get_window_geometry(window_name: str) -> Optional[dict]:
    """Find a window by name and return its geometry via xdotool."""
    r = _run(["xdotool", "search", "--name", window_name])
    if r.returncode != 0 or not r.stdout.strip():
        # Try class-based search
        r = _run(["xdotool", "search", "--class", window_name])
    if r.returncode != 0 or not r.stdout.strip():
        return None
    wid = r.stdout.strip().splitlines()[-1]  # Take last (most recent) match
    r2 = _run(["xdotool", "getwindowgeometry", "--shell", wid])
    if r2.returncode != 0:
        return None
    vals = {}
    for line in r2.stdout.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            vals[k.strip()] = int(v.strip())
    if all(k in vals for k in ("X", "Y", "WIDTH", "HEIGHT")):
        return {"x": vals["X"], "y": vals["Y"],
                "w": vals["WIDTH"], "h": vals["HEIGHT"]}
    return None


_PORTAL_SCRIPT = """\
import sys, dbus, dbus.mainloop.glib
from gi.repository import GLib

dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
bus = dbus.SessionBus()
loop = GLib.MainLoop()
result = {}

def on_response(response, results, **kwargs):
    if response == 0:
        result['uri'] = str(results.get('uri', ''))
    loop.quit()

def on_timeout():
    loop.quit()
    return False

try:
    portal = bus.get_object('org.freedesktop.portal.Desktop', '/org/freedesktop/portal/desktop')
    portal_iface = dbus.Interface(portal, 'org.freedesktop.portal.Screenshot')
    options = dbus.Dictionary({'interactive': dbus.Boolean(False)}, signature='sv')
    request_path = str(portal_iface.Screenshot('', options))
    request_obj = bus.get_object('org.freedesktop.portal.Desktop', request_path)
    request_iface = dbus.Interface(request_obj, 'org.freedesktop.portal.Request')
    request_iface.connect_to_signal('Response', on_response)
    GLib.timeout_add_seconds(15, on_timeout)
    loop.run()
except Exception:
    pass

print(result.get('uri', ''), end='')
"""


def _take_screenshot(dest: Path) -> bool:
    """Take a screenshot via XDG Desktop Portal (system python3 + dbus + GLib)."""
    r = subprocess.run(
        ["/usr/bin/python3", "-c", _PORTAL_SCRIPT],
        capture_output=True, text=True, timeout=20,
    )
    uri = r.stdout.strip()
    if uri.startswith("file://"):
        src = Path(uri[len("file://"):])
        if src.exists():
            shutil.copy2(src, dest)
            return True
    return False


# ── Tools ─────────────────────────────────────────────────────────────────────

@mcp.tool()
def screenshot(
    window_name: Optional[str] = None,
    region: Optional[dict] = None,
) -> dict:
    """
    Take a screenshot and return the image.

    Args:
        window_name: Name (or partial name) of the window to capture.
                     Automatically finds the window and crops to its bounds.
                     Works for XWayland apps (Chromium, TickTick, Bitwarden, etc.).
                     For Wayland-native apps, use region instead.
        region:      Explicit crop region: {"x": int, "y": int, "w": int, "h": int}.
                     Takes priority over window_name if both provided.

    Returns:
        Dict with "path" (absolute path to PNG file) and "geometry" info.
        Use the Read tool on the returned path to view the image.

    Notes:
        Uses XDG Desktop Portal via /usr/bin/python3 + dbus-python + GLib.
        Works natively on GNOME Wayland. No extra tools needed.
    """
    ts = _ts()
    full_path = SHOT_DIR / f"full_{ts}.png"
    final_path = SHOT_DIR / f"shot_{ts}.png"

    if not _take_screenshot(full_path):
        raise RuntimeError(
            "Screenshot failed. Install: sudo apt install gnome-screenshot\n"
            "Or run: sudo apt install grim  (for Wayland-native)"
        )

    # Resolve crop region
    crop = None
    geom_used = None
    if region:
        crop = region
        geom_used = region
    elif window_name:
        geom = _get_window_geometry(window_name)
        if geom:
            pad = 4
            crop = {
                "x": max(0, geom["x"] - pad),
                "y": max(0, geom["y"] - pad),
                "w": geom["w"] + pad * 2,
                "h": geom["h"] + pad * 2,
            }
            geom_used = geom
        # If window not found, return full screenshot (don't error)

    if crop:
        _crop_image(full_path, crop, final_path)
        full_path.unlink(missing_ok=True)
    else:
        final_path = full_path

    result = {
        "path": str(final_path),
        "note": "Use the Read tool on 'path' to view this image",
    }
    if geom_used:
        result["geometry"] = geom_used
    if window_name and not geom_used:
        result["warning"] = f"Window '{window_name}' not found via xdotool — full screenshot returned"
    return result


@mcp.tool()
def get_windows() -> list[dict]:
    """
    List all visible windows with their IDs, names, and screen geometry.

    Note: Only shows XWayland-accessible windows. Pure Wayland-native apps
    (e.g. WaveTerm running in native Wayland mode) may not appear here.
    Use screenshot() with a known region for those.

    Returns:
        List of dicts: {id, name, x, y, width, height}
    """
    r = _run(["xdotool", "search", "--name", ""])
    if r.returncode != 0:
        return []

    windows = []
    for wid in r.stdout.strip().splitlines():
        name_r = _run(["xdotool", "getwindowname", wid])
        geom_r = _run(["xdotool", "getwindowgeometry", "--shell", wid])
        if name_r.returncode != 0:
            continue
        name = name_r.stdout.strip()
        if not name or name in ("", "mutter guard window"):
            continue
        vals = {}
        for line in geom_r.stdout.splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                vals[k.strip()] = v.strip()
        windows.append({
            "id": int(wid),
            "name": name,
            "x": int(vals.get("X", 0)),
            "y": int(vals.get("Y", 0)),
            "width": int(vals.get("WIDTH", 0)),
            "height": int(vals.get("HEIGHT", 0)),
        })
    return windows


@mcp.tool()
def get_screen() -> dict:
    """
    Return screen information: resolution, session type, display.

    Returns:
        {width, height, session_type, display, wayland_display}
    """
    r = _run(["xdotool", "getdisplaygeometry"])
    w, h = 0, 0
    if r.returncode == 0:
        parts = r.stdout.strip().split()
        if len(parts) == 2:
            w, h = int(parts[0]), int(parts[1])
    return {
        "width": w,
        "height": h,
        "session_type": os.environ.get("XDG_SESSION_TYPE", "unknown"),
        "display": os.environ.get("DISPLAY", ""),
        "wayland_display": os.environ.get("WAYLAND_DISPLAY", ""),
        "gnome_screenshot_available": bool(shutil.which("gnome-screenshot")),
    }


@mcp.tool()
def click(x: int, y: int, button: str = "left") -> str:
    """
    Click at screen coordinates.

    Args:
        x: X coordinate in pixels
        y: Y coordinate in pixels
        button: "left" (default), "right", or "middle"

    Returns:
        Confirmation string.
    """
    btn_map = {"left": "1", "middle": "2", "right": "3"}
    btn = btn_map.get(button.lower(), "1")
    _run(["xdotool", "mousemove", "--sync", str(x), str(y)])
    _run(["xdotool", "click", btn])
    return f"Clicked {button} at ({x}, {y})"


@mcp.tool()
def double_click(x: int, y: int) -> str:
    """
    Double-click at screen coordinates.

    Args:
        x: X coordinate in pixels
        y: Y coordinate in pixels
    """
    _run(["xdotool", "mousemove", "--sync", str(x), str(y)])
    _run(["xdotool", "click", "--repeat", "2", "--delay", "100", "1"])
    return f"Double-clicked at ({x}, {y})"


@mcp.tool()
def right_click(x: int, y: int) -> str:
    """
    Right-click at screen coordinates (opens context menu).

    Args:
        x: X coordinate in pixels
        y: Y coordinate in pixels
    """
    _run(["xdotool", "mousemove", "--sync", str(x), str(y)])
    _run(["xdotool", "click", "3"])
    return f"Right-clicked at ({x}, {y})"


@mcp.tool()
def move_mouse(x: int, y: int) -> str:
    """
    Move mouse to coordinates without clicking.

    Args:
        x: X coordinate in pixels
        y: Y coordinate in pixels
    """
    _run(["xdotool", "mousemove", str(x), str(y)])
    return f"Mouse moved to ({x}, {y})"


@mcp.tool()
def type_text(text: str, delay_ms: int = 12) -> str:
    """
    Type text at the current keyboard focus.

    Args:
        text:     Text to type
        delay_ms: Delay between keystrokes in ms (default 12 — natural speed)

    Returns:
        Confirmation string.

    Note:
        For special characters or passwords, prefer key() with individual keys.
        For apps running natively on Wayland, focus the window first with a click().
    """
    _run(["xdotool", "type", "--delay", str(delay_ms), "--", text])
    preview = text[:40] + ("..." if len(text) > 40 else "")
    return f"Typed: {repr(preview)}"


@mcp.tool()
def key(combo: str) -> str:
    """
    Press a key or key combination.

    Args:
        combo: Key combo string. Examples:
               "Return"         — Enter key
               "ctrl+c"         — Copy
               "ctrl+v"         — Paste
               "ctrl+shift+t"   — New tab (in many apps)
               "super"          — Super/Windows key
               "alt+F4"         — Close window
               "ctrl+alt+t"     — Open terminal (GNOME default)
               "Escape"         — Escape
               "Tab"            — Tab
               "BackSpace"      — Backspace
               "ctrl+a"         — Select all

    Returns:
        Confirmation string.
    """
    _run(["xdotool", "key", "--clearmodifiers", combo])
    return f"Key pressed: {combo}"


@mcp.tool()
def scroll(x: int, y: int, direction: str = "down", clicks: int = 3) -> str:
    """
    Scroll at screen coordinates.

    Args:
        x:         X coordinate
        y:         Y coordinate
        direction: "up", "down", "left", or "right"
        clicks:    Number of scroll ticks (default 3)

    Returns:
        Confirmation string.
    """
    btn_map = {"up": "4", "down": "5", "left": "6", "right": "7"}
    btn = btn_map.get(direction.lower(), "5")
    _run(["xdotool", "mousemove", "--sync", str(x), str(y)])
    for _ in range(clicks):
        _run(["xdotool", "click", btn])
    return f"Scrolled {direction} {clicks}x at ({x}, {y})"


# ── Entry point ───────────────────────────────────────────────────────────────

def serve():
    mcp.run(transport="stdio")
