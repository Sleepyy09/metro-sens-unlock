# Building MetroSensUnlock from source

Everything the tool does is in one file, `metro_sens_unlock.py` (Python standard library only, no third-party imports). `MetroSensUnlock.exe` is that file packaged with PyInstaller. This document lets anyone rebuild the release zip from a clean Windows machine and check it against what is uploaded to Nexus Mods.

## Requirements

- Windows 10/11 x64
- Python 3.14 x64 from python.org (release 1.0.0 was built with 3.14.7); 3.11+ should also work
- Git
- Visual Studio 2022 Build Tools with the "Desktop development with C++" workload. Only needed to compile PyInstaller's bootloader in step 3; see "Alternative: prebuilt PyInstaller" if you do not have it.

## Steps

Open PowerShell in an empty folder and run:

```powershell
git clone https://github.com/Sleepyy09/metro-sens-unlock.git
cd metro-sens-unlock
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --no-binary pyinstaller pyinstaller==6.22.0   # compiles the bootloader locally (~2 min)
.\build.ps1
```

`build.ps1` does, in order:

1. `python -m PyInstaller --clean --noconfirm MetroSensUnlock.spec` (folder build, `noarchive=True`, no UPX, no onefile).
2. Smoke test: runs `dist\MetroSensUnlock\MetroSensUnlock.exe --check` and fails if it does not exit 0.
3. Stages `dist\stage\` with the exe folder plus the source, spec, version file, this document, README and LICENSE.
4. Writes `SHA256SUMS.txt` covering every staged file and zips it all to `dist\MetroSensUnlock-<version>.zip`.
5. Prints the SHA-256 of the exe and the zip.

The same script runs on every push in GitHub Actions (`.github/workflows/build.yml`, `windows-latest` runner), so a public build log and artifact exist for each commit and each `v*` tag.

## Alternative: prebuilt PyInstaller

`pip install pyinstaller==6.22.0` (the PyPI wheel) works too and produces a functionally identical exe. The wheel ships a precompiled bootloader that some antivirus engines fingerprint generically, which is why releases compile it from source instead. The Python payload in `_internal\` is the same either way.

## Checking a release against source

PyInstaller output is not byte-identical across machines (the bootloader carries compiler and timestamp differences), so compare by content rather than by exe hash:

```powershell
# what the shipped exe is made of: the script, byte for byte
Expand-Archive MetroSensUnlock-1.0.0.zip -DestinationPath check
Get-FileHash check\metro_sens_unlock.py            # matches the tagged commit
Get-Content check\SHA256SUMS.txt                   # covers every shipped file
python check\metro_sens_unlock.py --check          # run the script directly, no exe needed
```

The exe embeds the script as bytecode. `pyi-archive_viewer dist\MetroSensUnlock\MetroSensUnlock.exe` (installed with PyInstaller) lists the bundled entries; `metro_sens_unlock` is the only application module, the rest is the standard library that `tkinter` pulls in.

## What the program touches at runtime (for reviewers)

| Action | Where |
|---|---|
| Reads `HKCU\Software\Valve\Steam\SteamPath` and `config\libraryfolders.vdf` | to find the game folder (`find_exe`) |
| Reads `MetroExodus.exe`, writes it and `MetroExodus.exe.sensunlock.bak` | only after all 10 descriptors and 4 code sites validate (`apply_patch`); `restore` copies the backup back |
| Reads/writes `%USERPROFILE%\Saved Games\Metro Exodus\<id>\user.cfg` | `joy_sens_x` / `joy_sens_aiming_x` lines only (`write_sens`) |
| Runs `tasklist` | to refuse to patch while the game is running (`game_running`) |
| Clipboard | "Copy report" button only |

No network access, no services, no scheduled tasks, no registry writes, no other files. `--check` mode is read-only and prints what the patcher sees.

## Release checklist

1. Bump `VERSION` in `metro_sens_unlock.py` and `version_info.txt`.
2. Commit, tag `vX.Y.Z`, push the tag. GitHub Actions builds and attaches `MetroSensUnlock-X.Y.Z.zip` to the release.
3. Upload that zip to Nexus unchanged, and put the release URL and the exe SHA-256 from the build log in the Nexus description.
