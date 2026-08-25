[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [ValidateSet('setup', 'dev', 'build', 'docker', 'package', 'update')]
    [string]$Tool = 'package',
    [Parameter(ValueFromRemainingArguments)]
    [string[]]$ToolArguments
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Requirements = Join-Path $ProjectRoot 'requirements.txt'
$StateDirectory = Join-Path $ProjectRoot '.esdk'

function Write-Step([string]$Text) { Write-Host "  > $Text" -ForegroundColor Cyan }
function Write-Success([string]$Text) { Write-Host "  OK $Text" -ForegroundColor Green }
function Write-Failure([string]$Text) { Write-Host "  !! $Text" -ForegroundColor Red }

function Get-RequestedPythonVersion {
    if (-not (Test-Path -LiteralPath $Requirements)) { return '3.11' }
    $match = Select-String -LiteralPath $Requirements -Pattern '^\s*python\s*==\s*(\d+\.\d+(?:\.\d+)?)\s*$' | Select-Object -First 1
    if ($match) { return $match.Matches[0].Groups[1].Value }
    return '3.11'
}

function Find-Python([string]$Version) {
    $parts = $Version.Split('.')
    $minorVersion = "$($parts[0]).$($parts[1])"
    $launcher = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($launcher) {
        $executable = & $launcher.Source "-$minorVersion" -c "import sys; print(sys.executable)" 2>$null
        if ($LASTEXITCODE -eq 0 -and $executable) { return $executable.Trim() }
    }
    $python = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($python) {
        $actual = & $python.Source -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
        if ($LASTEXITCODE -eq 0 -and $actual -eq $minorVersion) { return $python.Source }
    }
    return $null
}

function Install-Python([string]$Version) {
    $parts = $Version.Split('.')
    $package = "Python.Python.$($parts[0]).$($parts[1])"
    $winget = Get-Command winget.exe -ErrorAction SilentlyContinue
    if (-not $winget) { throw 'Windows Package Manager (winget) is required to install Python automatically.' }
    Write-Step "Installing Python $Version..."
    & $winget.Source install --id $package --exact --silent --accept-package-agreements --accept-source-agreements --disable-interactivity
    if ($LASTEXITCODE -ne 0) { throw "Python installation failed with exit code $LASTEXITCODE." }
    $env:Path = [Environment]::GetEnvironmentVariable('Path', 'User') + ';' + [Environment]::GetEnvironmentVariable('Path', 'Machine')
}

function Invoke-Python([string]$PythonCommand, [string[]]$Arguments) {
    & $PythonCommand @Arguments
    $script:PythonExitCode = $LASTEXITCODE
}

try {
    Write-Host ''
    Write-Host '  ESDK' -ForegroundColor Magenta -NoNewline
    Write-Host "  $($Tool.ToUpperInvariant())" -ForegroundColor White

    $version = Get-RequestedPythonVersion
    $pythonCommand = Find-Python $version
    if (-not $pythonCommand) {
        Install-Python $version
        $pythonCommand = Find-Python $version
    }
    if (-not $pythonCommand) { throw "Python $version was installed but could not be located. Open a new terminal and retry." }
    Write-Success "Python $version is ready."

    New-Item -ItemType Directory -Force -Path $StateDirectory | Out-Null
    $requirementsHash = if (Test-Path $Requirements) { (Get-FileHash -LiteralPath $Requirements -Algorithm SHA256).Hash } else { 'none' }
    $stamp = Join-Path $StateDirectory 'requirements.sha256'
    $installedHash = if (Test-Path $stamp) { (Get-Content -LiteralPath $stamp -Raw).Trim() } else { '' }
    if ($requirementsHash -ne $installedHash) {
        Write-Step 'Installing project dependencies...'
        $pipFile = Join-Path $StateDirectory 'pip-requirements.txt'
        $pipLines = if (Test-Path $Requirements) {
            Get-Content -LiteralPath $Requirements | Where-Object { $_ -notmatch '^\s*python\s*==' }
        } else { @() }
        Set-Content -LiteralPath $pipFile -Value $pipLines -Encoding UTF8
        Invoke-Python $pythonCommand @('-m', 'pip', 'install', '--disable-pip-version-check', '-r', $pipFile)
        $exitCode = $script:PythonExitCode
        if ($exitCode -ne 0) { throw 'One or more Python dependencies could not be installed.' }
        Set-Content -LiteralPath $stamp -Value $requirementsHash -NoNewline
        Write-Success 'Dependencies are ready.'
    }

    $script = Join-Path $ProjectRoot "engine\tooling\$Tool.py"
    if (-not (Test-Path -LiteralPath $script)) { throw "Internal ESDK tool is missing: $script" }
    Write-Step "Starting $Tool..."
    Push-Location $ProjectRoot
    try {
        Invoke-Python $pythonCommand (@($script) + $ToolArguments)
        $exitCode = $script:PythonExitCode
    }
    finally { Pop-Location }
    if ($exitCode -ne 0) { throw "$Tool stopped with exit code $exitCode." }
    Write-Success "$Tool finished."
    exit 0
} catch {
    Write-Failure $_.Exception.Message
    exit 1
}
