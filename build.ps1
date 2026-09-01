# Builds dist\MetroSensUnlock-<version>.zip from a clean checkout. See BUILDING.md.
# Run from the repo root with PyInstaller installed in the active Python.
$ErrorActionPreference = 'Stop'
$ver = (Select-String -Path metro_sens_unlock.py -Pattern '^VERSION = "(.+)"').Matches[0].Groups[1].Value

python -m PyInstaller --clean --noconfirm MetroSensUnlock.spec
if ($LASTEXITCODE) { throw "pyinstaller failed ($LASTEXITCODE)" }

# Smoke test: the windowed exe must start and exit 0 in --check mode (no GUI, no game needed).
$p = Start-Process -FilePath (Resolve-Path dist\MetroSensUnlock\MetroSensUnlock.exe) -ArgumentList '--check' -Wait -PassThru
if ($p.ExitCode) { throw "smoke test failed ($($p.ExitCode))" }

# Stage: exe folder + everything needed to rebuild it, then checksums, then zip.
$stage = 'dist\stage'
Remove-Item -Recurse -Force $stage -ErrorAction Ignore
New-Item -ItemType Directory $stage | Out-Null
Copy-Item -Recurse dist\MetroSensUnlock $stage
Copy-Item metro_sens_unlock.py, MetroSensUnlock.spec, version_info.txt, build.ps1, README.md, BUILDING.md, LICENSE $stage
Push-Location $stage
try {
    Get-ChildItem -Recurse -File | ForEach-Object {
        $rel = (Resolve-Path -Relative $_.FullName) -replace '^\.[\\/]', '' -replace '\\', '/'
        "$((Get-FileHash $_.FullName -Algorithm SHA256).Hash.ToLower()) *$rel"
    } | Set-Content SHA256SUMS.txt -Encoding ascii
    Compress-Archive -Path * -DestinationPath "..\MetroSensUnlock-$ver.zip" -Force
} finally { Pop-Location }

"built dist\MetroSensUnlock-$ver.zip"
Get-FileHash dist\MetroSensUnlock\MetroSensUnlock.exe, "dist\MetroSensUnlock-$ver.zip" -Algorithm SHA256 | Format-Table -AutoSize Hash, Path
