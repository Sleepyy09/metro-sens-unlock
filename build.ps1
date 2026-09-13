$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
Push-Location $PSScriptRoot
try {
    node tests/selftest.cjs
    if ($LASTEXITCODE -ne 0) { throw 'Self-check failed. No release produced.' }
    $version = (Select-String -LiteralPath MetroSensUnlock.html -Pattern 'const VERSION = "([0-9]+\.[0-9]+\.[0-9]+)"').Matches[0].Groups[1].Value
    $files = @('MetroSensUnlock.html', 'README.md', 'LICENSE')
    $utf8 = [System.Text.UTF8Encoding]::new($false)
    $sums = ($files | ForEach-Object { "$((Get-FileHash -LiteralPath $_ -Algorithm SHA256).Hash.ToLowerInvariant()) *$_" }) -join "`n"
    $distPath = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot 'dist'))
    [System.IO.Directory]::CreateDirectory($distPath) | Out-Null
    $archivePath = Join-Path $distPath "MetroSensUnlock-$version-Offline.zip"
    $temporaryPath = "$archivePath.$([guid]::NewGuid().ToString('N')).tmp"
    Add-Type -AssemblyName System.IO.Compression
    $stream = [System.IO.File]::Open($temporaryPath, [System.IO.FileMode]::CreateNew)
    try {
        $zip = [System.IO.Compression.ZipArchive]::new($stream, [System.IO.Compression.ZipArchiveMode]::Create, $true)
        try {
            foreach ($name in @($files) + @('SHA256SUMS.txt')) {
                $entry = $zip.CreateEntry($name, [System.IO.Compression.CompressionLevel]::Optimal)
                $entry.LastWriteTime = [DateTimeOffset]::new(2000, 1, 1, 0, 0, 0, [TimeSpan]::Zero)
                $data = if ($name -eq 'SHA256SUMS.txt') { $utf8.GetBytes($sums + "`n") } else { [System.IO.File]::ReadAllBytes((Join-Path $PSScriptRoot $name)) }
                $output = $entry.Open()
                try { $output.Write($data, 0, $data.Length) } finally { $output.Dispose() }
            }
        } finally { $zip.Dispose() }
    } finally { $stream.Dispose() }
    # Reopen and verify all payloads before replacing only this version's generated ZIP.
    $verifyStream = [System.IO.File]::OpenRead($temporaryPath)
    try {
        $verify = [System.IO.Compression.ZipArchive]::new($verifyStream, [System.IO.Compression.ZipArchiveMode]::Read)
        try {
            $expected = @($files) + @('SHA256SUMS.txt')
            if ($verify.Entries.Count -ne 4 -or (Compare-Object $expected @($verify.Entries.FullName))) { throw 'Unexpected archive contents.' }
            foreach ($entry in $verify.Entries) {
                $input = $entry.Open()
                $memory = [System.IO.MemoryStream]::new()
                try {
                    $input.CopyTo($memory)
                    $actual = [Convert]::ToBase64String($memory.ToArray())
                    $data = if ($entry.FullName -eq 'SHA256SUMS.txt') { $utf8.GetBytes($sums + "`n") } else { [System.IO.File]::ReadAllBytes((Join-Path $PSScriptRoot $entry.FullName)) }
                    if ($actual -cne [Convert]::ToBase64String($data)) { throw "Archive payload mismatch: $($entry.FullName)" }
                } finally { $input.Dispose(); $memory.Dispose() }
            }
        } finally { $verify.Dispose() }
    } finally { $verifyStream.Dispose() }
    [System.IO.File]::Move($temporaryPath, $archivePath, $true)
    Write-Output "Built $archivePath"
    Get-FileHash -LiteralPath $archivePath -Algorithm SHA256 | Format-List
} finally { Pop-Location }