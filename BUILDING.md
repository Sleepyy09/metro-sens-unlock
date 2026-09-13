# Build and verification

MetroSensUnlock.html contains all runtime HTML, CSS and JavaScript. There is no compile step, package manifest or third-party dependency.

## Requirements and commands

Node.js 22 or later runs the self-check. PowerShell 7 packages the ZIP. Players need neither.

```powershell
node tests/selftest.cjs
pwsh -File build.ps1
```

The build repeats the self-check. It creates `dist/MetroSensUnlock-2.0.0-Offline.zip` with exactly four root entries: MetroSensUnlock.html, README.md, LICENSE and SHA256SUMS.txt. The manifest hashes the three payload files, excluding itself. The build prints a separate SHA-256 for the final ZIP.

The script packages an explicit file list without traversing dist, uses fixed entry timestamps, reopens the archive and compares every payload to source before replacing this version's ZIP. It does not delete previous releases. An interrupted build can leave a uniquely named .tmp archive in dist; this is never selected for release.

## Local game equivalence, read-only

Pass a stock backup and an already patched executable:

```powershell
node tests/selftest.cjs 'PATH/MetroExodus.exe.sensunlock.bak' 'PATH/MetroExodus.exe'
```

This patches a copy in memory and requires exact equality with the patched reference. It never writes either game file. Default tests use synthetic PE fixtures and sample configs with no proprietary game bytes.

## Browser and game checks before release

Open the extracted HTML directly through file:// in connected Brave. Select a stock backup and a disposable sample config. Check keyboard navigation, number inputs, slider synchronisation, 200% zoom and narrow width. Prepare both downloads, verify their bytes against the core output and confirm no network requests or console errors. Repeat with an already patched executable, malformed input, a partial patch, a replaced file selection during processing and settings edited after preparation. Stale download links must disappear.

Use a scratch directory for downloads. Never overwrite the installed game during browser verification. No server is required. Browser automation policy blocked local-file navigation on 2026-09-13, so this interaction check is outstanding. Node interface-logic tests do not establish browser behaviour, download behaviour or visual quality.

After manually installing tested copies, check turn speed and ADS with a controller, then restoration. Do not call the release play-tested until that check has run.

## File access and security

| Action | Access |
|---|---|
| Select executable/config | Reads only the selected files into browser memory |
| Prepare | Validates inputs and changes copies in memory |
| Download | Creates Blob links; the player downloads and installs manually |
| Diagnose | Shows hash, size, patch state and instruction offsets |

No registry access, process scanning, filesystem discovery, direct replacement, network, storage, services, scheduled tasks, clipboard access or game launching. A Content Security Policy blocks connections and external resources. Inline scripts and styles are required for one inspectable file. Treat selected files as untrusted bytes. Never insert filenames or config text as HTML.

The tool still produces an executable copy from the user's own game file. Source-only distribution does not establish antivirus or Nexus acceptance.

## CI and publishing

GitHub Actions runs the same build on pushes, pull requests and manual dispatches. A version tag must match the HTML version. Tag builds can attach the ZIP to a GitHub release. Creating commits, pushing tags and uploading to Nexus require the owner's approval.

Use only the Offline ZIP for this version. Publish its hash and corresponding source revision when releasing. Legacy ZIPs, local test downloads and game files are excluded. The HTML inside the ZIP must match reviewed source. Do not claim Nexus scanning has passed until a result exists.