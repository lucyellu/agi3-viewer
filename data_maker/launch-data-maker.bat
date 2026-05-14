@echo off
setlocal

set PORT=8080
set ROOT=%~dp0..\..

netstat -ano | findstr ":%PORT% " | findstr "LISTENING" >nul 2>&1
if %errorlevel% == 0 (
    echo Server already running on port %PORT%
) else (
    echo Starting server on port %PORT% from %ROOT%
    start /min "" cmd /c "cd /d %ROOT% && python -m http.server %PORT%"
    timeout /t 2 /nobreak >nul
)

set CHROME=
for %%P in (
    "%ProgramFiles%\Google\Chrome\Application\chrome.exe"
    "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
    "%LocalAppData%\Google\Chrome\Application\chrome.exe"
) do (
    if exist %%P set CHROME=%%P
)

if defined CHROME (
    start "" %CHROME% --app="http://localhost:%PORT%/agi3_v3/data_maker/"
) else (
    start "" "http://localhost:%PORT%/agi3_v3/data_maker/"
)

endlocal
