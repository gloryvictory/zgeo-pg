param(
    [string]$OutputDirectory
)

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
        ".vscode"
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
    Write-Host "Install in QGIS: Plugins > Manage and Install Plugins > Install from ZIP"
}
finally {
    if (Test-Path -LiteralPath $stagingRoot) {
        Remove-Item -LiteralPath $stagingRoot -Recurse -Force
    }
}
