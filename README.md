# Metro Exodus – Controller Sensitivity Unlock

Metro Exodus caps controller look speed far too low, and editing `joy_sens_x` in `user.cfg` doesn't help: the engine clamps it to 1.0 on load, and on the default sensitivity preset it isn't even a multiplier — it's a slider position mapped to a hard-coded 0.5×–1.5× range. This tool patches that out and lets you set any look / aim speed you like.

## What it does

Patches `MetroExodus.exe` (a backup `MetroExodus.exe.sensunlock.bak` is kept next to it) so that:

- **Look speed = `joy_sens_x`**, a plain multiplier, on every sensitivity preset. The stock in-game slider maxes out at the equivalent of **1.5**; the tool lets you go up to 20.
- **ADS speed = `joy_sens_aiming_x` × look speed** (0.05–1.0). The engine never lets ADS exceed hip-fire speed; this keeps that but makes the fraction honest.
- Raises the engine's built-in maximum for `joy_sens_x` (and its four preset copies) from 1.0 to 20.0.

It then writes the look and ADS values you choose into `user.cfg` (`%USERPROFILE%\Saved Games\Metro Exodus\<id>\user.cfg`).

Nothing runs while you play — no background process, no memory editing, no DLL injection, no input remapping. Adaptive triggers, haptics, aim assist and every other controller feature are untouched. 14 bytes change in the exe: ten descriptor max values and four instruction operands.

## Use

1. Close the game.
2. Extract the zip anywhere and run `MetroSensUnlock\MetroSensUnlock.exe` (keep the `_internal` folder next to it). Steam installs are found automatically; for GOG / Epic / Game Pass click **Browse…** and pick the game folder (the one containing `MetroExodus.exe`).
3. Set **Look speed** (stock max ≈ 1.5; 2.5–5 is a good starting range) and **ADS speed** (fraction of look speed; stock presets use 0.45–0.7) and click **Apply**.
4. Play. Re-run and Apply any time to change values.

Don't touch the in-game *look* sensitivity slider afterwards — it only writes 0.1–1.0 and will overwrite your value. The in-game *aim* slider is fine (it writes the same 0.01–1.0 fraction the tool does).

Something not working? Click **Copy report** and paste the result in your bug report — it lists the exe hash, every descriptor and code site the tool found, and the current state. It reads only, never writes.

**Restore original** puts the backup exe back. If Steam updates or verifies the game, the exe is replaced — just run the tool and Apply again.

## Compatibility

- Tested: Metro Exodus Enhanced Edition, Steam, exe SHA-256 `43dd7b0d…bb4cd9` (build current as of 2026-08).
- Fail-closed: if any descriptor is missing or ambiguous, or the code-site count isn't exactly 4, nothing is written. The backup is only ever (re)taken from an exe that verifies as stock, so a Steam update can't leave you with a stale backup.
- The patcher locates everything by pattern (cvar descriptor layout, then the instructions that read those cvars), not by fixed offsets. It refuses to patch — and changes nothing — unless it can validate all ten descriptors and all four code sites.
- Original (non-Enhanced) Metro Exodus, GOG, Epic and Game Pass builds: untested. Browse to the game folder and try; it will either work or tell you it's unsupported.
- Works with ReShade / RenoDX / DLSS swaps — different files.

## Building from source

Single-file Python (3.11+, stdlib only). Full clean-machine recipe, reviewer notes and the CI workflow that builds every release: [BUILDING.md](BUILDING.md).

```
python metro_sens_unlock.py            # GUI
python metro_sens_unlock.py --check    # print what the patcher sees, change nothing
pip install --no-binary pyinstaller pyinstaller==6.22.0
.\build.ps1                            # exe (onedir, noarchive, no UPX) + SHA256SUMS + zip in dist\
```

Source and release builds: https://github.com/Sleepyy09/metro-sens-unlock

## How it works

The exe holds a static console-variable descriptor table (`name*, 0, value*, f32 min, f32 max, f32 value, type*`, 0x30 bytes per entry). `joy_sens_x` is declared `min 0.1, max 1.0, default 0.95`; `user.cfg` values are clamped to that range at load.

The gamepad look code has two paths, selected by the hidden `_gamepad_preset_sens` cvar (the in-game "sensitivity preset"):

- **Preset 3 (default):** `t = (joy_sens_x − min) / (max − min)`, `look = 0.5·(1−t) + 1.5·t`, `ads = 0.05·(1−ta) + look·ta`. Turn rate per frame is `dt · π / joy_time_to_rotate_180 · look · stick^joy_prepare_mode`, ramping toward `π / joy_time_to_rotate_180_fast` when the stick is pegged. Because `t` is normalised against the descriptor's own max, raising max alone just rescales the slider — the 1.5× ceiling is in the two constants. The patch repoints those two operands at the descriptor's own `min`/`max` fields, so `look = min·(1−t) + max·t = joy_sens_x`.
- **Presets 0–2 (legacy):** `look = sqrt(joy_sens_x)`, `ads = sqrt(joy_sens_x · joy_sens_aiming_x)`, plus the `joy_zone_*` / `joy_boost_*` stick-zone model. The patch turns the two `sqrtss` loads into `movss` so the values are the same plain multipliers as preset 3.

Stock feel is preserved at stock values (0.95 ≈ 1.44× on preset 3 before, 0.95× after — set 1.5 for the old max).

MIT licence.
