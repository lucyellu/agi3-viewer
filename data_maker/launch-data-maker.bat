@echo off
setlocal

set PORT=8080
set ROOT=%~dp0..\..

REM Probe port 8080 first. If anything is listening, verify it's OUR server by
REM fetching the manifest — if that 404s, the port is held by something else
REM (or a server rooted at the wrong directory), so kill it and restart.
set PORT_OK=0
netstat -ano | findstr ":%PORT% " | findstr "LISTENING" >nul 2>&1
if %errorlevel% == 0 (
    curl -sf -o nul "http://localhost:%PORT%/agi3_v3/data_maker/manifest.json" >nul 2>&1
    if %errorlevel% == 0 (
        echo Server already running on port %PORT% and serving correct root
        set PORT_OK=1
    ) else (
        echo Port %PORT% is held but not serving our content - killing stale server
        for /f "tokens=5" %%P in ('netstat -ano ^| findstr ":%PORT% " ^| findstr "LISTENING"') do (
            taskkill /F /PID %%P >nul 2>&1
        )
        timeout /t 1 /nobreak >nul
    )
)
if %PORT_OK% == 0 (
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
    start "" %CHROME% --app="http://localhost:%PORT%/agi3_v3/data_maker/index_controls.html"
) else (
    start "" "http://localhost:%PORT%/agi3_v3/data_maker/index_controls.html"
)

endlocal
