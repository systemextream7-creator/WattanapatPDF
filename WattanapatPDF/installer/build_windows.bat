@echo off
rem ============================================================================
rem  Builds WattanapatPDF-Setup-<version>.exe on Windows 10/11 (64-bit).
rem  Needs: Python 3.12 (python.org, tick "py launcher") and, for the installer,
rem         Inno Setup 6 (https://jrsoftware.org/isdl.php). Internet is needed
rem         ONLY while building (to download the Python packages).
rem ============================================================================
setlocal
cd /d "%~dp0\.."
set VERSION=1.0.0

where py >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python launcher "py" not found. Install Python 3.12 x64 from python.org first.
  exit /b 1
)
if not exist .venv (
  py -3.12 -m venv .venv
  if errorlevel 1 py -3 -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip || exit /b 1
pip install -r requirements.txt pyinstaller || exit /b 1

echo.
echo === Running engine tests ===
python -m unittest tests.test_engine
if errorlevel 1 echo [WARNING] Some engine tests failed - review the output above before distributing.

echo.
echo === Building application folder (PyInstaller) ===
pyinstaller --noconfirm --clean installer\wattanapat_pdf.spec || exit /b 1

set "ISCC="
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"

if defined ISCC (
  echo.
  echo === Building installer (Inno Setup) ===
  "%ISCC%" /DAppVersion=%VERSION% installer\installer.iss || exit /b 1
  echo.
  echo DONE: dist\installer\WattanapatPDF-Setup-%VERSION%.exe
) else (
  echo.
  echo [INFO] Inno Setup 6 not found - creating a portable zip instead.
  powershell -NoProfile -Command "Compress-Archive -Path 'dist\WattanapatPDF' -DestinationPath 'dist\WattanapatPDF-portable-%VERSION%.zip' -Force"
  echo DONE: dist\WattanapatPDF-portable-%VERSION%.zip  ^(install Inno Setup 6 and re-run to get a Setup.exe^)
)
endlocal
