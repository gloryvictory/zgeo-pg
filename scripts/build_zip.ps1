param(
    [string]$OutputDirectory,
    [string[]]$QGISPluginDirectories,
    [switch]$SkipQGISInstall,
    [switch]$NoRestart
)

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
$pluginName = Split-Path -Leaf $pluginRoot
$metadataPath = Join-Path $pluginRoot "metadata.txt"

if (-not (Test-Path -LiteralPath $metadataPath)) {
    throw "metadata.txt not found: $metadataPath"
}

$versionLine = Select-String -LiteralPath $metadataPath -Pattern '^version=(.+)$'
if (-not $versionLine) {
    throw "version is not defined in metadata.txt"
}
$version = $versionLine.Matches[0].Groups[1].Value.Trim()

if (-not $OutputDirectory) {
    $OutputDirectory = Join-Path $pluginRoot "dist"
}

$stagingRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("zgeo-pg-build-" + [guid]::NewGuid().ToString("N"))
$stagingPlugin = Join-Path $stagingRoot $pluginName

try {
    New-Item -ItemType Directory -Path $stagingPlugin -Force | Out-Null
    New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null

    $excludedNames = @(
        "__pycache__",
        "dist",
        "scripts",
        "tests",
        ".git",
        ".gitignore",
        ".idea",
        ".vscode",
        ".empryo",
        ".pytest_cache"
    )

    Get-ChildItem -LiteralPath $pluginRoot -Force | Where-Object {
        $excludedNames -notcontains $_.Name
    } | ForEach-Object {
        Copy-Item -LiteralPath $_.FullName -Destination $stagingPlugin -Recurse -Force
    }

    Get-ChildItem -LiteralPath $stagingPlugin -Recurse -Directory -Filter "__pycache__" |
        Remove-Item -Recurse -Force

    $zipPath = Join-Path $OutputDirectory "$pluginName-$version.zip"
    if (Test-Path -LiteralPath $zipPath) {
        Remove-Item -LiteralPath $zipPath -Force
    }

    Add-Type -AssemblyName System.IO.Compression
    Add-Type -AssemblyName System.IO.Compression.FileSystem

    $archive = [System.IO.Compression.ZipFile]::Open(
        $zipPath,
        [System.IO.Compression.ZipArchiveMode]::Create
    )
    try {
        Get-ChildItem -LiteralPath $stagingPlugin -Recurse -File | ForEach-Object {
            $relativePath = $_.FullName.Substring($stagingPlugin.Length + 1).Replace("\", "/")
            $entryName = "$pluginName/$relativePath"
            [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile(
                $archive,
                $_.FullName,
                $entryName,
                [System.IO.Compression.CompressionLevel]::Optimal
            ) | Out-Null
        }
    }
    finally {
        $archive.Dispose()
    }

    Write-Host "Created: $zipPath"

    # Keep only the latest build in the output directory.
    Get-ChildItem -LiteralPath $OutputDirectory -Filter "$pluginName-*.zip" -File |
        Where-Object { $_.FullName -ne (Resolve-Path -LiteralPath $zipPath).Path } |
        ForEach-Object {
            Remove-Item -LiteralPath $_.FullName -Force
            Write-Host "Removed stale build: $($_.Name)"
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

        foreach ($pluginsDirectory in $targets) {
            $target = Join-Path $pluginsDirectory $pluginName
            if (Test-Path -LiteralPath $target) {
                Remove-Item -LiteralPath $target -Recurse -Force
            }
            Copy-Item -LiteralPath $stagingPlugin -Destination $target -Recurse -Force
            Get-ChildItem -LiteralPath $target -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue |
                Remove-Item -Recurse -Force
            Write-Host "Installed: $target (version $version)"
        }

        if ($closed.Count -gt 0 -and -not $NoRestart) {
            Start-QGISAgain -Executables $closed
        }
    }

    Write-Host "Install in QGIS: Plugins > Manage and Install Plugins > Install from ZIP"
}
finally {
    if (Test-Path -LiteralPath $stagingRoot) {
        Remove-Item -LiteralPath $stagingRoot -Recurse -Force
    }
}
