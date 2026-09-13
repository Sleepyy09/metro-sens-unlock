# MetroSensUnlock 2.0.0

An offline browser tool for adjusting Metro Exodus controller look and aiming sensitivity beyond the stock look limit. Select your own game files, choose your settings and download modified copies for manual installation.

**[Download MetroSensUnlock 2.0.0 Offline ZIP](https://github.com/Sleepyy09/metro-sens-unlock/releases/download/v2.0.0/MetroSensUnlock-2.0.0-Offline.zip)**

Extract the ZIP and open `MetroSensUnlock.html`. No installation, Python, administrator access or internet connection is needed to run the tool. Keep the extracted files together so the instructions and hashes are available.

This is the current offline edition. The native launcher has been retired. Automated tests and executable equivalence checks passed; real browser interaction and controller gameplay checks remain outstanding.

The ZIP contains four files: `MetroSensUnlock.html`, this README, `LICENSE` and `SHA256SUMS.txt`. JavaScript runs locally. There are no external assets, network calls, telemetry, update checks or persistent browser storage. No game executable is distributed.

## What it changes

- Look speed becomes a multiplier from 0.1 to 20 across sensitivity presets. Stock preset 3 has an effective maximum of about 1.5.
- Aim speed is 5% to 100% of look speed, matching the engine's limit that aiming cannot exceed hip-fire speed.
- Only the recognised sensitivity descriptors and four instructions change in the executable. Only base and active preset sensitivity lines change in the selected config.

Nothing from this tool runs while you play. Saves, input mappings and other controller systems are not edited. Single-player use only.

## How it works

Metro limits sensitivity inside its executable as well as its config. The tool changes recognised sensitivity limits and four instructions in a copy of `MetroExodus.exe`, then writes your chosen values into a copy of `user.cfg`. Config editing alone does not remove the executable's limits.

Files stay in browser memory while the tool prepares them. Selecting them does not upload them, and preparing a download does not overwrite either original. You install the downloaded copies yourself. An executable that already has the complete patch only needs a new config.

The tool rejects malformed files, ambiguous patch locations and incomplete patches. It checks its generated executable again before offering a download. Changing an input or setting clears previously prepared downloads.

## Install

1. Close Metro Exodus. Extract the ZIP into its own folder.
2. Keep original copies of `MetroExodus.exe` and your `user.cfg` in a separate backup folder. Do not replace these backups with patched downloads.
3. Open `MetroSensUnlock.html` in a current desktop browser. No Python, administrator access or server is required to open the tool.
4. Select `MetroExodus.exe` from the game installation. Steam users can find it through Properties, Installed Files, Browse. Select your profile's `user.cfg` from `%USERPROFILE%\Saved Games\Metro Exodus\<profile>\`. Launch the game once if no config exists.
5. Set look and aim speed, confirm that the game is closed and backups are kept, then select **Prepare modified files**.
6. Download the copies into a separate folder. A stock executable produces both downloads. An already patched executable produces only a config download.
7. With the game closed, manually copy the downloads into their original folders. The filenames must be exactly `MetroExodus.exe` and `user.cfg`. Remove any download-number suffix before installing. Keep your original backups.
8. Launch Metro and check look and aim speed. Increase values in small steps. Change look speed through this tool because the in-game look slider overwrites your value. The in-game aim slider can still adjust the aim fraction.

Preparing or downloading copies does not install them. The browser cannot check whether Metro is running, detect the active profile, overwrite the originals or confirm installation. Files in protected installation folders may require Windows permission to replace manually.

## Existing patches and game updates

Select the executable you currently use. If it is fully patched, only a new config is needed. Keep the old tool's original `MetroExodus.exe.sensunlock.bak` for recovery. The old launcher and its `_internal` folder are no longer needed to use this edition.

A partial or old max-only patch is refused. Restore a current clean executable using your game launcher's file verification, then select it again. Never treat a partially patched file as an original backup.

After a game update, use the current executable and make a new backup. Do not restore an executable backup from an older game build.

## Uninstall and restore

Close Metro and replace the modified executable and config with your original backups. For an old `.sensunlock.bak`, copy it and rename the copy to `MetroExodus.exe`. If the backup is missing or belongs to an older game build, use your launcher's file verification instead. File verification does not necessarily restore the personal config; reset sensitivity in the game if no config backup is available.

Restoring a config backup also restores any unrelated settings saved in it. Removing the HTML tool's extracted folder does not undo changes you manually installed.

## Compatibility and verification

The patch was developed for the Steam Enhanced Edition. In read-only testing on 2026-09-13, the HTML implementation reproduced the existing patched executable exactly from its stock backup:

| Check | Result |
|---|---|
| Stock SHA-256 | `4cd2d25479ff0b574e89bcb0351f73028bf3a232762423a5a24a5b206170f572` |
| Patched SHA-256 | `d288b82b1f17b7ffad05822cfd6586073c418f8fd9b5b1f8b2ab0878c6e7190b` |
| File size | 25,697,352 bytes, unchanged |
| Changed bytes on this build | 18 |

The byte count depends on the game build.

The original edition and GOG, Epic and Game Pass builds remain untested. Passing pattern validation is not a compatibility guarantee. The tool requires 10 unique controller descriptors and four unique instruction sites. Invalid headers, ambiguous matches, unexpected ranges and partial patches are refused. Maximum selected sizes are 128 MB for the executable and 1 MB for the config.

UTF-8 and ANSI config bytes, unrelated lines and existing LF/CRLF endings are preserved. Duplicate sensitivity keys, invalid numbers and UTF-16 configs are refused. Missing base sensitivity keys are refused; missing active preset keys are added.

Automated checks exercise patching, config preservation, UI logic and release contents. This release still needs a real local-file browser interaction check and an in-game controller check. The development browser automation policy blocked opening local HTML files, so no browser visual or interaction verification is claimed.

## Troubleshooting and trust

Open **Compatibility and diagnostics** for the executable hash and validation result. The report does not include full paths, account identifiers or the complete config. It never sends data automatically.

The browser needs JavaScript and its native Web Crypto API. If downloads acquire a numbered suffix, use the exact original filename when installing. If the launcher restores the original executable during an update or verification, recheck the new file before patching.

Browsers and antivirus scanners can flag a generated executable. This package does not guarantee a particular Nexus scan badge. Do not disable security software to use it. Consult the scanner vendor or Nexus support if a file is flagged. Nexus describes its [scan process](https://help.nexusmods.com/article/128-anti-virus-false-positives) and [quarantine review](https://help.nexusmods.com/article/117-why-has-my-mod-been-quarantined).

The download contains source and documentation only. Do not redistribute a generated game executable or personal config. No Nexus upload or current scanner review has been performed for this release.

## Development

The complete runtime is in `MetroSensUnlock.html`. No package installation is needed. Run `node tests/selftest.cjs`, then `pwsh -File build.ps1`. The build verifies the four-file archive and prints its SHA-256. [BUILDING.md](https://github.com/Sleepyy09/metro-sens-unlock/blob/main/BUILDING.md) describes the full checks and recipe.

Source: [Sleepyy09/metro-sens-unlock](https://github.com/Sleepyy09/metro-sens-unlock). Author SLEEP. MIT licence.

## Version 2.0.0

Offline HTML interface, look and ADS controls, defensive executable/config parsing, partial-patch rejection, manual downloads and restoration. The release contains no native launcher, DLLs or bundled runtime. Development was AI-assisted; the source and tests are available in this repository.
