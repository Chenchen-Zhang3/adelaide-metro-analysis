@echo off
setlocal

for %%I in ("%~dp0..") do set "PROJECT_ROOT=%%~fI"
cd /d "%PROJECT_ROOT%"
if errorlevel 1 (
    echo ERROR: Cannot open project directory: %PROJECT_ROOT%
    exit /b 1
)

if not defined ADELAIDE_METRO_PYTHON set "ADELAIDE_METRO_PYTHON=%PROJECT_ROOT%\.venv\Scripts\python.exe"
if not defined ADELAIDE_METRO_STATIC_GTFS_PATH set "ADELAIDE_METRO_STATIC_GTFS_PATH=%PROJECT_ROOT%\data\static_gtfs"
if not defined ADELAIDE_METRO_DATABASE_PATH set "ADELAIDE_METRO_DATABASE_PATH=%PROJECT_ROOT%\data\historical\adelaide_metro_history.db"
if not defined ADELAIDE_METRO_LOG_PATH set "ADELAIDE_METRO_LOG_PATH=%PROJECT_ROOT%\logs\historical_collector.log"
if not defined ADELAIDE_METRO_POLLING_INTERVAL_SECONDS set "ADELAIDE_METRO_POLLING_INTERVAL_SECONDS=60"

if not exist "%ADELAIDE_METRO_PYTHON%" (
    echo ERROR: Collector Python was not found: %ADELAIDE_METRO_PYTHON%
    echo Create .venv and install requirements-collector.txt before starting.
    exit /b 2
)

if not exist "%ADELAIDE_METRO_STATIC_GTFS_PATH%\stop_times.txt" (
    echo ERROR: stop_times.txt was not found in: %ADELAIDE_METRO_STATIC_GTFS_PATH%
    exit /b 3
)

if not exist "%PROJECT_ROOT%\data\historical" mkdir "%PROJECT_ROOT%\data\historical"
if errorlevel 1 exit /b 4
if not exist "%PROJECT_ROOT%\logs" mkdir "%PROJECT_ROOT%\logs"
if errorlevel 1 exit /b 5

echo Starting Adelaide Metro historical collector...
echo Database: %ADELAIDE_METRO_DATABASE_PATH%
echo Static GTFS: %ADELAIDE_METRO_STATIC_GTFS_PATH%
echo Log: %ADELAIDE_METRO_LOG_PATH%

"%ADELAIDE_METRO_PYTHON%" -m backend.services.historical_collection %*
set "COLLECTOR_EXIT_CODE=%ERRORLEVEL%"

if not "%COLLECTOR_EXIT_CODE%"=="0" echo ERROR: Collector stopped with exit code %COLLECTOR_EXIT_CODE%.
exit /b %COLLECTOR_EXIT_CODE%
