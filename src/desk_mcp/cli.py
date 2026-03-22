"""desk-mcp CLI — admin and diagnostic commands."""

import os
import shutil
import subprocess

import typer
from rich.console import Console
from rich.table import Table
from rich import print as rprint

app = typer.Typer(name="desktop-mcp", help="desk-mcp — Desktop automation MCP")
console = Console()


@app.command()
def serve():
    """Start the MCP server (stdio transport for Claude Code)."""
    from desk_mcp.server import serve as _serve
    _serve()


@app.command()
def status():
    """Show environment and tool availability."""
    console.rule("[bold blue]desk-mcp status[/]")

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Component", style="white")
    table.add_column("Status")
    table.add_column("Details")

    # Session type
    session = os.environ.get("XDG_SESSION_TYPE", "unknown")
    display = os.environ.get("DISPLAY", "")
    wayland = os.environ.get("WAYLAND_DISPLAY", "")
    table.add_row(
        "Session",
        f"[green]{session}[/]",
        f"DISPLAY={display}  WAYLAND={wayland}"
    )

    # xdotool
    xt = shutil.which("xdotool")
    if xt:
        r = subprocess.run(["xdotool", "getdisplaygeometry"],
                           capture_output=True, text=True)
        res = r.stdout.strip() if r.returncode == 0 else "error"
        table.add_row("xdotool", "[green]✓ installed[/]",
                      f"Resolution: {res}")
    else:
        table.add_row("xdotool", "[red]✗ missing[/]",
                      "sudo apt install xdotool")

    # python3-dbus + python3-gi (XDG portal screenshot backend)
    r = subprocess.run(
        ["/usr/bin/python3", "-c", "import dbus, dbus.mainloop.glib; from gi.repository import GLib; print('ok')"],
        capture_output=True, text=True
    )
    portal_ok = r.returncode == 0
    table.add_row(
        "python3-gi / dbus",
        "[green]✓ available[/]" if portal_ok else "[red]✗ missing[/]",
        "XDG portal screenshot backend" if portal_ok else "sudo apt install python3-gi python3-dbus"
    )

    # ydotool (Wayland-native input)
    yd = shutil.which("ydotool")
    table.add_row(
        "ydotool",
        "[green]✓ installed[/]" if yd else "[dim]not installed[/]",
        "Wayland-native input (optional)" if not yd else "Available"
    )

    # wmctrl
    wm = shutil.which("wmctrl")
    table.add_row(
        "wmctrl",
        "[green]✓ installed[/]" if wm else "[dim]not installed[/]",
        "Window management (optional)"
    )

    # Pillow
    try:
        import PIL
        table.add_row("Pillow", f"[green]✓ {PIL.__version__}[/]",
                      "Image cropping for calibrated shots")
    except ImportError:
        table.add_row("Pillow", "[red]✗ missing[/]", "pip install Pillow")

    console.print(table)

    rprint("\n[bold]Screenshot backend:[/]")
    rprint("  [green]XDG Desktop Portal[/] via /usr/bin/python3 + python3-gi + dbus-python")
    rprint("  Requires: [cyan]sudo apt install python3-gi python3-dbus[/] (standard on Ubuntu)")
    rprint("\n[bold]Input simulation:[/] xdotool (XWayland — works for most apps)")
    rprint("[dim]For Wayland-native windows: coordinates work, window auto-detect may not.[/]")


@app.command()
def screenshot(
    output: str = typer.Option("/tmp/k_desktop/test.png", help="Output path"),
    window: str = typer.Option(None, help="Window name to capture"),
):
    """Test screenshot from the CLI."""
    from desk_mcp.server import _take_screenshot, _get_window_geometry, _crop_image  # noqa: F401
    from pathlib import Path

    dest = Path(output)
    dest.parent.mkdir(parents=True, exist_ok=True)

    console.print(f"[cyan]Taking screenshot → {dest}[/]")
    ok = _take_screenshot(dest)
    if not ok:
        rprint("[red]Screenshot failed. Install gnome-screenshot:[/] sudo apt install gnome-screenshot")
        raise typer.Exit(1)

    if window:
        geom = _get_window_geometry(window)
        if geom:
            cropped = dest.with_stem(dest.stem + "_cropped")
            _crop_image(dest, {**geom, "w": geom["w"], "h": geom["h"]}, cropped)
            dest.unlink()
            rprint(f"[green]✓ Window '{window}' captured → {cropped}[/]")
            rprint(f"  Geometry: x={geom['x']} y={geom['y']} {geom['w']}×{geom['h']}")
        else:
            rprint(f"[yellow]Window '{window}' not found via xdotool — full screenshot saved.[/]")
            rprint(f"[green]✓ Full screenshot → {dest}[/]")
    else:
        rprint(f"[green]✓ Full screenshot → {dest}[/]")


if __name__ == "__main__":
    app()
