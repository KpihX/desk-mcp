# CHANGELOG — desk-mcp

## [0.2.0] — 2026-03-22

### Changed
- [x] Renamed project `k-desktop-mcp` → `desk-mcp` (package, binary, repos)
- [x] Renamed import package `k_desktop_mcp` → `desk_mcp`
- [x] CLI binary: `desktop-mcp` → `desk-mcp`
- [x] Added `.agent/` kernel + CLAUDE/GEMINI/AGENTS/VIBE/COPILOT.md symlinks
- [x] Added CHANGELOG.md, TODO.md, `.gitignore`

## [0.1.0] — 2026-03-17

### Added
- [x] Screenshot via XDG Desktop Portal (GNOME Wayland, no dialog)
- [x] Window listing and geometry (`get_windows`)
- [x] Mouse: click, double-click, right-click, move
- [x] Keyboard: `type_text`, `key` (combo support via xdotool)
- [x] Scroll at coordinates
- [x] Calibrated screenshot with optional window crop
- [x] `desk-mcp serve` (stdio MCP transport)
- [x] `desk-mcp status` (environment + dependency check)
- [x] `desk-mcp screenshot` (CLI test command)
