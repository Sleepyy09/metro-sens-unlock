# MetroSensUnlock

## Scope and stack
Offline HTML controller sensitivity patcher. MetroSensUnlock.html owns the complete browser runtime. No package manager, dependencies, install command or framework. tests/selftest.cjs uses Node assertions and synthetic PE files. DESIGN.md is the UI contract.

## Commands
- Test and syntax checks: `node tests/selftest.cjs`
- Read-only game parity: `node tests/selftest.cjs STOCK_BACKUP PATCHED_EXE`
- Build and archive integrity check: `pwsh -File build.ps1`
- Lint/typecheck: no separate tools configured; selftest parses both scripts.
- Security/audit: inspect the complete HTML, build script and CI diff. Check PE/config inputs, absence of network/storage, stale output invalidation and the four-file ZIP allowlist. Run the required security review workflow for security changes.
- Browser smoke check: open the HTML through file:// in connected Brave and follow BUILDING.md. Never bypass a browser automation security block.

## Contracts
- Require 10 unique descriptors and four unique instruction sites. Reject partial, malformed and ambiguous executables.
- Preserve executable length, unrelated bytes, config encoding and unrelated settings.
- Never write the installed game, original backups or user profile during automated checks.
- No external runtime assets, storage, telemetry, native installer or packaged executable.
- Never distribute game binaries or local profile configs.
- Release whitelist: MetroSensUnlock.html, README.md, LICENSE, SHA256SUMS.txt.
- Preserve untracked design/media work and historical releases unless separately authorised.
- Do not claim Nexus acceptance, browser verification or play testing without evidence.
- No commits, pushes or uploads without current-turn approval.

## Lab notes
- [2026-09-13] Browser automation rejected file:// navigation under its URL policy. Do not work around this through another browser or indirect navigation. Browser verification remains outstanding.
- [2026-09-13] Raw movss prefix matches exceed 1024 in the real executable. Limit matches after filtering RIP targets, or valid builds fail the ambiguity check.
- [2026-09-13] The current stock-to-patched pair differs by 18 bytes. Compare full output rather than asserting the old README's fixed 14-byte count.
- [2026-09-13] Light-mode input borders needed a darker token for 3:1 contrast. Check colours from the actual CSS.
