# TODO — desk-mcp

## Roadmap

### Transport & Admin
- [ ] HTTP transport layer — expose desk-mcp over streamable-HTTP for homelab deployment (Traefik), following the tick-mcp/whats-mcp pattern.
- [ ] Admin CLI — `desk-admin` with status, diagnostics, reconnect commands.

### Publish
- [ ] Push to GitHub (`KpihX/desk-mcp`) and GitLab (`kpihx-labs/desk-mcp`)
- [ ] Publish to PyPI (`desk-mcp`)
- [ ] Add to Claude Code MCP config as `desk-mcp` (stdio → http after homelab deploy)

### Features
- [ ] `find` — locate UI element by text (OCR or accessibility tree)
- [ ] `read_page` — extract visible text from screen (OCR)
- [ ] Wayland-native input via ydotool (parallel to xdotool)
- [ ] Region screenshot — screenshot of a bounding box without full-screen capture
