# PyRov one-click setup for Windows.
#
#   Double-click setup.bat (next to this file), or run in PowerShell:
#       powershell -ExecutionPolicy Bypass -File setup.ps1
#   or straight from GitHub, without downloading anything first:
#       irm https://raw.githubusercontent.com/buggYateer/robotics-project/main/setup.ps1 | iex
#
# What it does: finds (or installs) Python, downloads the project into a folder
# you choose, creates a virtual environment, installs the dependencies, puts a
# PyRov shortcut on the desktop and starts the program. Running it again on an
# existing folder updates the project and the dependencies.

param([string]$Dest = "")

# Native tools (git, pip) write progress to stderr; PowerShell 5.1 would treat that as an
# error and abort under "Stop", so exit codes are checked by hand instead.
$ErrorActionPreference = "Continue"
$Repo = "https://github.com/buggYateer/robotics-project"
$Zip = "$Repo/archive/refs/heads/main.zip"

function Say($msg) { Write-Host ""; Write-Host "==> $msg" -ForegroundColor Cyan }
function Fail($msg) { Write-Host ""; Write-Host "!! $msg" -ForegroundColor Red; Read-Host "Press Enter to close"; exit 1 }

Write-Host ""
Write-Host "  PyRov - Multi-Environment Exploration Rover" -ForegroundColor Yellow
Write-Host "  Robotics team project setup" -ForegroundColor Yellow
Write-Host ""

# ------------------------------------------------------------------ destination
if (-not $Dest) {
    $default = Join-Path $env:USERPROFILE "PyRov"
    $answer = Read-Host "Where should the project live? [Enter = $default]"
    $Dest = if ($answer) { $answer } else { $default }
}
$Dest = [System.IO.Path]::GetFullPath($Dest)
if ($Dest.Length -gt 70) {
    # Windows limits paths to 260 characters and the Qt package has very deep folders
    Fail "That folder path is too long ($($Dest.Length) characters). Please choose a short one such as C:\Users\$env:USERNAME\PyRov and run the setup again."
}
Say "Project folder: $Dest"

# ------------------------------------------------------------------ python
function Find-Python {
    foreach ($cand in @("py -3.13", "py -3.12", "py -3.14", "py -3.15", "python", "python3")) {
        try {
            $v = & cmd /c "$cand -c `"import sys;print(sys.version_info[0]*100+sys.version_info[1])`"" 2>$null
            if ($LASTEXITCODE -eq 0 -and [int]$v -ge 312) { return $cand }
        } catch {}
    }
    return $null
}
$py = Find-Python
if (-not $py) {
    Say "Python 3.12 or newer was not found. Trying to install it with winget..."
    try {
        winget install --id Python.Python.3.12 --accept-source-agreements --accept-package-agreements -e | Out-Null
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
        $py = Find-Python
    } catch {}
    if (-not $py) {
        Start-Process "https://www.python.org/downloads/windows/"
        Fail "Please install Python 3.12+ from the page that just opened (tick 'Add python.exe to PATH'), then run this setup again."
    }
}
Say "Using Python: $py"

# ------------------------------------------------------------------ download
$git = Get-Command git -ErrorAction SilentlyContinue
if (Test-Path (Join-Path $Dest "main.py")) {
    if ($git -and (Test-Path (Join-Path $Dest ".git"))) {
        Say "Project already there - pulling the latest version"
        Push-Location $Dest; & cmd /c "git pull --ff-only 2>&1"; Pop-Location
    } else {
        Say "Project already there - keeping it (delete the folder to re-download)"
    }
} elseif ($git) {
    Say "Cloning the repository with git"
    & cmd /c "git clone --quiet `"$Repo`" `"$Dest`" 2>&1"
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path (Join-Path $Dest "main.py"))) { Fail "git clone failed. Check your internet connection and run the setup again." }
} else {
    Say "git is not installed - downloading the project as a zip instead"
    $tmp = Join-Path $env:TEMP "pyrov_download"
    if (Test-Path $tmp) { Remove-Item $tmp -Recurse -Force }
    New-Item -ItemType Directory -Path $tmp | Out-Null
    $zipPath = Join-Path $tmp "main.zip"
    Invoke-WebRequest -Uri $Zip -OutFile $zipPath
    Expand-Archive -Path $zipPath -DestinationPath $tmp
    $inner = Get-ChildItem $tmp -Directory | Select-Object -First 1
    New-Item -ItemType Directory -Path $Dest -Force | Out-Null
    Copy-Item (Join-Path $inner.FullName "*") $Dest -Recurse -Force
    Remove-Item $tmp -Recurse -Force
}

# ------------------------------------------------------------------ environment
$venvPy = Join-Path $Dest ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) {
    Say "Creating the virtual environment"
    & cmd /c "$py -m venv `"$Dest\.venv`""
    if (-not (Test-Path $venvPy)) { Fail "Could not create the virtual environment." }
}
Say "Installing the dependencies (this takes a few minutes the first time)"
& cmd /c "`"$venvPy`" -m pip install --upgrade pip --quiet 2>&1"
$req = Join-Path $Dest "requirements.txt"
& cmd /c "`"$venvPy`" -m pip install -r `"$req`" 2>&1"
if ($LASTEXITCODE -ne 0) { Fail "pip could not install the dependencies. Check your internet connection and run the setup again." }

# ------------------------------------------------------------------ check
Say "Checking that everything imports"
$check = & cmd /c "`"$venvPy`" -c `"import numpy, scipy, sklearn, matplotlib, PySide6; print('ok')`" 2>&1"
$check = ($check | Out-String)
if ($check -notmatch "(?m)^ok\s*$") {
    Write-Host $check
    if ($check -match "Application Control") {
        Fail "Windows 'Smart App Control' is blocking the installed packages. Turn it off in Windows Security > App & browser control > Smart App Control, then run the setup again."
    }
    Fail "Something did not install correctly (see the message above)."
}

# ------------------------------------------------------------------ shortcut
try {
    $pythonw = Join-Path $Dest ".venv\Scripts\pythonw.exe"
    $icon = Join-Path $Dest "assets\icon.ico"
    $shell = New-Object -ComObject WScript.Shell
    $lnk = $shell.CreateShortcut((Join-Path ([Environment]::GetFolderPath("Desktop")) "PyRov.lnk"))
    $lnk.TargetPath = $pythonw
    $lnk.Arguments = "main.py"
    $lnk.WorkingDirectory = $Dest
    if (Test-Path $icon) { $lnk.IconLocation = $icon }
    $lnk.Description = "PyRov - exploration rover simulator"
    $lnk.Save()
    Say "Shortcut 'PyRov' placed on the desktop"
} catch { Write-Host "(could not create the desktop shortcut: $_)" }

# ------------------------------------------------------------------ run
Say "Starting PyRov"
Write-Host "  Next time: double-click the PyRov shortcut on the desktop, or run.bat in $Dest"
Write-Host ""
Start-Process -FilePath $venvPy -ArgumentList "main.py" -WorkingDirectory $Dest
