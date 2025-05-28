@echo off
REM Voice Freight Broker - Docker Management Scripts for Windows
REM Usage: docker-scripts.bat [command]

setlocal enabledelayedexpansion

REM Check if Docker is running
:check_docker
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker is not running. Please start Docker and try again.
    exit /b 1
)

REM Check if .env file exists
:check_env
if not exist .env (
    echo [WARNING] .env file not found. Creating from template...
    if exist env.example (
        copy env.example .env >nul
        echo [WARNING] Please edit .env file with your actual API keys before running the application.
    ) else (
        echo [ERROR] env.example file not found. Please create .env manually.
        exit /b 1
    )
)

REM Main command logic
if "%1"=="start" goto start
if "%1"=="stop" goto stop
if "%1"=="restart" goto restart
if "%1"=="logs" goto logs
if "%1"=="build" goto build
if "%1"=="status" goto status
if "%1"=="cleanup" goto cleanup
if "%1"=="backup" goto backup
if "%1"=="help" goto help
if "%1"=="" goto help
goto unknown

:start
echo [INFO] Starting Voice Freight Broker application...
call :check_docker
call :check_env
docker-compose up --build -d
if %errorlevel% equ 0 (
    echo [SUCCESS] Application started successfully!
    echo [INFO] Frontend: http://localhost:3000
    echo [INFO] Backend API: http://localhost:8000
    echo [INFO] API Docs: http://localhost:8000/docs
) else (
    echo [ERROR] Failed to start application!
)
goto end

:stop
echo [INFO] Stopping application...
docker-compose down
if %errorlevel% equ 0 (
    echo [SUCCESS] Application stopped successfully!
) else (
    echo [ERROR] Failed to stop application!
)
goto end

:restart
echo [INFO] Restarting application...
call :stop
call :start
goto end

:logs
if "%2"=="" (
    echo [INFO] Showing logs for all services...
    docker-compose logs -f
) else (
    echo [INFO] Showing logs for %2...
    docker-compose logs -f %2
)
goto end

:build
echo [INFO] Building Docker images...
call :check_docker
docker-compose build
if %errorlevel% equ 0 (
    echo [SUCCESS] Images built successfully!
) else (
    echo [ERROR] Failed to build images!
)
goto end

:status
echo [INFO] Checking application status...
docker-compose ps
echo.
echo [INFO] Docker resource usage:
docker stats --no-stream
goto end

:cleanup
echo [INFO] Cleaning up Docker resources...
docker-compose down -v
docker image prune -f
docker volume prune -f
echo [SUCCESS] Cleanup completed!
goto end

:backup
echo [INFO] Backing up database...
if not exist backups mkdir backups
for /f "tokens=1-4 delims=/ " %%a in ('date /t') do set mydate=%%c%%a%%b
for /f "tokens=1-2 delims=: " %%a in ('time /t') do set mytime=%%a%%b
set mytime=%mytime: =0%
set BACKUP_FILE=./backups/transit_%mydate%_%mytime%.db
docker cp voice-freight-backend:/app/data/transit.db %BACKUP_FILE%
if %errorlevel% equ 0 (
    echo [SUCCESS] Database backed up to %BACKUP_FILE%
) else (
    echo [ERROR] Failed to backup database!
)
goto end

:help
echo Voice Freight Broker - Docker Management Script for Windows
echo.
echo Usage: %0 [command]
echo.
echo Commands:
echo   start         Build and start all services
echo   stop          Stop all services
echo   restart       Restart all services
echo   logs [service] View logs (optional: specify service name)
echo   build         Build Docker images
echo   status        Show application and Docker status
echo   cleanup       Clean up Docker resources
echo   backup        Backup database
echo   help          Show this help message
echo.
echo Examples:
echo   %0 start                    # Start the application
echo   %0 logs backend            # View backend logs
echo   %0 logs                    # View all logs
goto end

:unknown
echo [ERROR] Unknown command: %1
call :help
exit /b 1

:end
endlocal 