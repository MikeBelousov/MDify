param(
  [ValidateSet("lite", "ocr")]
  [string]$Variant = "lite",
  [string]$Python = "python",
  [string]$DistDir = ".build/workers/win-x64"
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = (Resolve-Path (Join-Path $ScriptDir "../..")).Path
$VenvDir = Join-Path $RootDir ".build/worker-$Variant-win-x64-venv"
$WorkDir = Join-Path $RootDir ".build/pyinstaller-$Variant-win-x64"
$ResolvedDistDir = if ([System.IO.Path]::IsPathRooted($DistDir)) {
  $DistDir
} else {
  Join-Path $RootDir $DistDir
}
$Entry = Join-Path $RootDir "workers/$Variant/mdify_worker_$Variant.py"
$Requirements = Join-Path $RootDir "workers/$Variant/requirements-$Variant.txt"
$Name = "mdify-worker-$Variant"

function Add-PyInstallerData {
  param(
    [string]$Source,
    [string]$Destination
  )

  return "$Source;$Destination"
}

& $Python -m venv $VenvDir
$VenvPython = Join-Path $VenvDir "Scripts/python.exe"
if (-not (Test-Path $VenvPython)) {
  throw "Virtual environment did not create Python executable: $VenvPython"
}

& $VenvPython -m pip install --upgrade pip
& $VenvPython -m pip install -r $Requirements

if ($Variant -eq "ocr") {
  & $VenvPython (Join-Path $RootDir "workers/build/download_models.py")
}

$PyInstallerArgs = @(
  "--clean",
  "--noconfirm",
  "--onedir",
  "--name", $Name,
  "--distpath", $ResolvedDistDir,
  "--workpath", $WorkDir,
  "--specpath", $WorkDir,
  "--paths", $RootDir,
  "--collect-all", "markitdown",
  "--collect-all", "magika",
  $Entry
)

if ($Variant -eq "ocr") {
  $PyInstallerArgs = @(
    "--clean",
    "--noconfirm",
    "--onedir",
    "--name", $Name,
    "--distpath", $ResolvedDistDir,
    "--workpath", $WorkDir,
    "--specpath", $WorkDir,
    "--paths", $RootDir,
    "--collect-all", "markitdown",
    "--collect-all", "magika",
    "--collect-all", "rapidocr",
    "--collect-all", "onnxruntime",
    "--collect-all", "cv2",
    "--collect-all", "pypdfium2",
    "--collect-all", "PIL",
    "--add-data", (Add-PyInstallerData (Join-Path $RootDir "workers/ocr/model_manifest.json") "workers/ocr"),
    "--add-data", (Add-PyInstallerData (Join-Path $RootDir "workers/ocr/models") "workers/ocr/models"),
    $Entry
  )
}

try {
  & $VenvPython -m PyInstaller @PyInstallerArgs
} catch {
  Write-Error @"
PyInstaller failed while building $Variant worker for win-x64.
Python: $Python
Virtual environment: $VenvDir
Target entry: $Entry
"@
  throw
}

$BuiltWorker = Join-Path $ResolvedDistDir "$Name/$Name.exe"
if (-not (Test-Path $BuiltWorker -PathType Leaf)) {
  throw "PyInstaller did not create executable worker: $BuiltWorker"
}

Write-Output $BuiltWorker
