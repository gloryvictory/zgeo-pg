param(
    [string]$OutputDirectory,
    [string[]]$QGISPluginDirectories,
    [switch]$SkipQGISInstall,
    [switch]$NoRestart
)

# Содержимое архива собирает scripts/build_zip.py: один источник правды для
# локальной сборки и CI. Этот скрипт добавляет установку в профиль QGIS и
# перезапуск QGIS Desktop.

# Profile plugins directories used by QGIS Desktop 4.x (4.2.3 on this machine).
function Get-DefaultQGISPluginDirectories {
    $profileBase = Join-Path $env:APPDATA "QGIS\QGIS4\profiles"
    if (-not (Test-Path -LiteralPath $profileBase)) {
        return @()
    }

    return @(
        Get-ChildItem -LiteralPath $profileBase -Directory | ForEach-Object {
            Join-Path $_.FullName "python\plugins"
        } | Where-Object { Test-Path -LiteralPath $_ }
    )
}

# QGIS keeps plugin modules in memory: the plugin directory must be free before
# it is replaced, so the application is closed first and reopened afterwards.
function Stop-RunningQGIS {
    $processes = @(Get-Process -Name "qgis*" -ErrorAction SilentlyContinue |
        Where-Object { $_.MainWindowHandle -ne 0 -or $_.ProcessName -like "qgis*bin*" })
    if (-not $processes) {
        return @()
    }

    # Remember the executable path before the processes disappear, so QGIS can
    # be started again afterwards.
    $executables = @()
    foreach ($process in $processes) {
        try {
            $executables += $process.MainModule.FileName
        }
        catch {
            Write-Verbose "Cannot resolve executable of $($process.ProcessName)"
        }
    }

    Write-Host "Closing QGIS: $($processes.ProcessName -join ', ')"
    foreach ($process in $processes) {
        $null = $process.CloseMainWindow()
    }

    # QGIS may show a "quit?" prompt, so a graceful close is given a few
    # seconds and then the process is terminated: the plugin directory has to be
    # free before it can be replaced.
    $deadline = (Get-Date).AddSeconds(10)
    while ((Get-Date) -lt $deadline) {
        $alive = @($processes | Where-Object { -not $_.HasExited })
        if (-not $alive) {
            break
        }
        Start-Sleep -Milliseconds 500
    }

    foreach ($process in $processes) {
        if (-not $process.HasExited) {
            Write-Warning "QGIS did not close by itself; terminating $($process.ProcessName)."
            $process.Kill()
            $null = $process.WaitForExit(15000)
        }
    }

    return $executables
}

function Start-QGISAgain {
    param([string[]]$Executables)

    foreach ($path in $Executables) {
        if ($path -and (Test-Path -LiteralPath $path)) {
            Start-Process -FilePath $path | Out-Null
            Write-Host "Started: $path"
        }
    }
}

$ErrorActionPreference = "Stop"

$pluginRoot = Split-Path -Parent $PSScriptRoot
$buildScript = Join-Path $PSScriptRoot "build_zip.py"

if (-not (Test-Path -LiteralPath $buildScript)) {
    throw "build_zip.py not found: $buildScript"
}

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    throw "python is required to build the archive"
}

if (-not $OutputDirectory) {
    $OutputDirectory = Join-Path $pluginRoot "dist"
}

# QGIS installs the archive by its top-level folder name and imports that folder
# as a Python package, so the name must be a PEP 8 identifier. The repository
# folder "zgeo-pg" contains a hyphen, therefore the archive root is "zgeo_pg".
$packageName = "zgeo_pg"

& $python.Source $buildScript --output-dir $OutputDirectory
if ($LASTEXITCODE -ne 0) {
    throw "build_zip.py failed with exit code $LASTEXITCODE"
}

$zipPath = Get-ChildItem -LiteralPath $OutputDirectory -Filter "zgeo-pg-*.zip" -File |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
if (-not $zipPath) {
    throw "archive was not created in $OutputDirectory"
}

if (-not $SkipQGISInstall) {
    $targets = if ($QGISPluginDirectories) {
        @($QGISPluginDirectories)
    } else {
        Get-DefaultQGISPluginDirectories
    }

    if (-not $targets) {
        Write-Warning "No QGIS profile plugins directory found; skipping install."
    }

    $closed = Stop-RunningQGIS

    $unpackRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("zgeo-pg-unpack-" + [guid]::NewGuid().ToString("N"))
    try {
        Expand-Archive -LiteralPath $zipPath.FullName -DestinationPath $unpackRoot -Force
        $unpacked = Join-Path $unpackRoot $packageName
        if (-not (Test-Path -LiteralPath $unpacked)) {
            throw "archive has no $packageName folder: $($zipPath.FullName)"
        }

        foreach ($pluginsDirectory in $targets) {
            $target = Join-Path $pluginsDirectory $packageName
            # Drop an install made under the old, non-identifier folder name.
            $stale = Join-Path $pluginsDirectory "zgeo-pg"
            if (Test-Path -LiteralPath $stale) {
                Remove-Item -LiteralPath $stale -Recurse -Force
                Write-Host "Removed stale install: $stale"
            }
            if (Test-Path -LiteralPath $target) {
                Remove-Item -LiteralPath $target -Recurse -Force
            }
            Copy-Item -LiteralPath $unpacked -Destination $target -Recurse -Force
            Get-ChildItem -LiteralPath $target -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue |
                Remove-Item -Recurse -Force
            Write-Host "Installed: $target"
        }
    }
    finally {
        if (Test-Path -LiteralPath $unpackRoot) {
            Remove-Item -LiteralPath $unpackRoot -Recurse -Force
        }
    }

    if ($closed.Count -gt 0 -and -not $NoRestart) {
        Start-QGISAgain -Executables $closed
    }
}

Write-Host "Install in QGIS: Plugins > Manage and Install Plugins > Install from ZIP"
