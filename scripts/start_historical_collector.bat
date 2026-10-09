@echo off
setlocal EnableExtensions DisableDelayedExpansion
set "COLLECTOR_EXIT_CODE=0"
set "COLLECTOR_PYTHON="
set "COLLECTOR_PYTHON_OPTION="

for %%I in ("%~dp0..") do set "PROJECT_ROOT=%%~fI"
cd /d "%PROJECT_ROOT%"
if errorlevel 1 (
    echo ERROR: Cannot open project directory: "%PROJECT_ROOT%"
    set "COLLECTOR_EXIT_CODE=1"
    goto finish
)

if not defined ADELAIDE_METRO_STATIC_GTFS_PATH set "ADELAIDE_METRO_STATIC_GTFS_PATH=%PROJECT_ROOT%\data\static_gtfs"
if not defined ADELAIDE_METRO_DATABASE_PATH set "ADELAIDE_METRO_DATABASE_PATH=%PROJECT_ROOT%\data\historical\adelaide_metro_history_v2.db"
if not defined ADELAIDE_METRO_LOG_PATH set "ADELAIDE_METRO_LOG_PATH=%PROJECT_ROOT%\logs\historical_collector.log"
if not defined ADELAIDE_METRO_POLLING_INTERVAL_SECONDS set "ADELAIDE_METRO_POLLING_INTERVAL_SECONDS=60"
if not defined ADELAIDE_METRO_TRIP_UPDATE_CHECKPOINT_SECONDS set "ADELAIDE_METRO_TRIP_UPDATE_CHECKPOINT_SECONDS=900"

echo Repository: "%PROJECT_ROOT%"
call :select_python
if errorlevel 1 (
    set "COLLECTOR_EXIT_CODE=2"
    goto finish
)

echo Checking collector runtime dependencies...
"%COLLECTOR_PYTHON%" %COLLECTOR_PYTHON_OPTION% -c "from google.transit import gtfs_realtime_pb2; import google.protobuf; import tzdata; from zoneinfo import ZoneInfo; ZoneInfo('Australia/Adelaide')"
if errorlevel 1 (
    echo ERROR: Collector runtime dependency or Adelaide timezone check failed.
    echo Install requirements in the selected Python environment:
    echo "%COLLECTOR_PYTHON%" %COLLECTOR_PYTHON_OPTION% -m pip install -r "%PROJECT_ROOT%\requirements-collector.txt"
    set "COLLECTOR_EXIT_CODE=6"
    goto finish
)

if not exist "%ADELAIDE_METRO_STATIC_GTFS_PATH%\stop_times.txt" (
    echo ERROR: stop_times.txt was not found in: "%ADELAIDE_METRO_STATIC_GTFS_PATH%"
    echo Copy the real Adelaide Metro stop_times.txt there or configure ADELAIDE_METRO_STATIC_GTFS_PATH.
    set "COLLECTOR_EXIT_CODE=3"
    goto finish
)

if not exist "%PROJECT_ROOT%\data\historical" (
    mkdir "%PROJECT_ROOT%\data\historical"
    if errorlevel 1 (
        echo ERROR: Cannot create historical-data directory in "%PROJECT_ROOT%".
        set "COLLECTOR_EXIT_CODE=4"
        goto finish
    )
)
if not exist "%PROJECT_ROOT%\logs" (
    mkdir "%PROJECT_ROOT%\logs"
    if errorlevel 1 (
        echo ERROR: Cannot create log directory in "%PROJECT_ROOT%".
        set "COLLECTOR_EXIT_CODE=5"
        goto finish
    )
)

echo Starting Adelaide Metro historical collector...
echo Python command: "%COLLECTOR_PYTHON%" %COLLECTOR_PYTHON_OPTION%
echo Database: "%ADELAIDE_METRO_DATABASE_PATH%"
echo Static GTFS: "%ADELAIDE_METRO_STATIC_GTFS_PATH%"
echo Log: "%ADELAIDE_METRO_LOG_PATH%"
echo Unchanged Trip Update checkpoint: %ADELAIDE_METRO_TRIP_UPDATE_CHECKPOINT_SECONDS% seconds

"%COLLECTOR_PYTHON%" %COLLECTOR_PYTHON_OPTION% -m backend.services.historical_collection %*
set "COLLECTOR_EXIT_CODE=%ERRORLEVEL%"

if not "%COLLECTOR_EXIT_CODE%"=="0" echo ERROR: Python collector exited with code %COLLECTOR_EXIT_CODE%. Review the Python error above and log at "%ADELAIDE_METRO_LOG_PATH%".
goto finish

:select_python
if defined ADELAIDE_METRO_PYTHON (
    set "COLLECTOR_PYTHON=%ADELAIDE_METRO_PYTHON%"
    goto configured_python
)
if exist "%PROJECT_ROOT%\.venv\Scripts\python.exe" (
    set "COLLECTOR_PYTHON=%PROJECT_ROOT%\.venv\Scripts\python.exe"
    goto configured_python
)
echo Project .venv was not found; checking Windows Python 3.12 candidates...
for /f "delims=" %%P in ('where py.exe 2^>nul') do if not defined COLLECTOR_PYTHON set "COLLECTOR_PYTHON=%%P"
if not defined COLLECTOR_PYTHON goto path_python
set "COLLECTOR_PYTHON_OPTION=-3.12"
call :validate_python
if not errorlevel 1 exit /b 0

:path_python
set "COLLECTOR_PYTHON="
set "COLLECTOR_PYTHON_OPTION="
for /f "delims=" %%P in ('where python.exe 2^>nul') do if not defined COLLECTOR_PYTHON set "COLLECTOR_PYTHON=%%P"
if not defined COLLECTOR_PYTHON goto python_not_found
call :validate_python
if not errorlevel 1 exit /b 0

:python_not_found
echo ERROR: No usable Python 3.12 interpreter was found.
echo Install Python 3.12, create the project .venv, or set ADELAIDE_METRO_PYTHON to its full python.exe path.
exit /b 1

:configured_python
if not exist "%COLLECTOR_PYTHON%" (
    echo ERROR: Configured Python executable was not found: "%COLLECTOR_PYTHON%"
    echo Set ADELAIDE_METRO_PYTHON to a full python.exe path or create the project .venv.
    exit /b 1
)
call :validate_python
if not errorlevel 1 exit /b 0
echo ERROR: Selected interpreter cannot run Python 3.12: "%COLLECTOR_PYTHON%"
echo Correct ADELAIDE_METRO_PYTHON or recreate .venv using py -3.12 -m venv .venv.
exit /b 1

:validate_python
"%COLLECTOR_PYTHON%" %COLLECTOR_PYTHON_OPTION% -c "import sys; print('Interpreter:', sys.executable); print('Python:', sys.version.split()[0]); sys.exit(0 if sys.version_info[:2] == (3, 12) else 1)"
exit /b %ERRORLEVEL%

:finish
rem Opt-in only: scheduled tasks must never wait for keyboard input.
if not "%COLLECTOR_EXIT_CODE%"=="0" if "%ADELAIDE_METRO_PAUSE_ON_ERROR%"=="1" pause
exit /b %COLLECTOR_EXIT_CODE%
