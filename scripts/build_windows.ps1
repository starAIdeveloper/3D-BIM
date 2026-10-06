$ErrorActionPreference = 'Stop'
python -m pip install -e . pyinstaller==6.16.0
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python -m PyInstaller --noconfirm --clean --windowed --onedir --name 3D-BIM run.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host 'Desktop build available in dist/3D-BIM. Keep the entire folder together.'
