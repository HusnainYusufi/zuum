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
        echo [WARNING] Required keys: OPENAI_API_KEY, NGROK_AUTH_TOKEN, RETELL_API_KEY, WORKFLOW_RETELL_AGENT_ID, CHECKIN_RETELL_AGENT_ID
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
if "%1"=="shell" goto shell
if "%1"=="help" goto help
if "%1"=="" goto help
goto unknown

:start
echo [INFO] Starting Voice Freight Broker backend...
call :check_docker
call :check_env
docker-compose up --build -d
if %errorlevel% equ 0 (
    echo [SUCCESS] Backend started successfully!
    echo [INFO] API: http://localhost:8000
    echo [INFO] API Docs: http://localhost:8000/docs
    echo [INFO] Ngrok Dashboard: http://localhost:4040
    timeout /t 3 >nul
    echo [INFO] Checking service health...
    docker-compose ps
) else (
    echo [ERROR] Failed to start backend!
    echo [INFO] Run 'docker-compose logs' to see error details.
)
goto end

:stop
echo [INFO] Stopping backend...
docker-compose down
if %errorlevel% equ 0 (
    echo [SUCCESS] Backend stopped successfully!
) else (
    echo [ERROR] Failed to stop backend!
)
goto end

:restart
echo [INFO] Restarting backend...
call :stop
timeout /t 2 >nul
call :start
goto end

:logs
if "%2"=="" (
    echo [INFO] Showing backend logs...
    docker-compose logs -f backend
) else (
    echo [INFO] Showing logs for %2...
    docker-compose logs -f %2
)
goto end

:build
echo [INFO] Building Docker images...
call :check_docker
docker-compose build --no-cache
if %errorlevel% equ 0 (
    echo [SUCCESS] Images built successfully!
) else (
    echo [ERROR] Failed to build images!
)
goto end

:status
echo [INFO] Checking application status...
echo.
docker-compose ps
echo.
echo [INFO] Container health:
docker ps --filter "name=voice-freight" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo.
echo [INFO] Docker resource usage:
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"
goto end

:cleanup
echo [WARNING] This will remove all containers, volumes, and images for this project.
set /p confirm="Are you sure? (y/N): "
if /i "%confirm%" neq "y" (
    echo [INFO] Cleanup cancelled.
    goto end
)
echo [INFO] Cleaning up Docker resources...
docker-compose down -v --rmi all
docker image prune -f
docker volume prune -f
echo [SUCCESS] Cleanup completed!
goto end

:backup
echo [INFO] Backing up database...
if not exist backups mkdir backups
for /f "tokens=2-4 delims=/ " %%a in ('date /t') do set mydate=%%c%%a%%b
for /f "tokens=1-2 delims=: " %%a in ('time /t') do set mytime=%%a%%b
set mytime=%mytime: =0%
set BACKUP_FILE=backups\transit_%mydate%_%mytime%.db
docker cp voice-freight-backend:/app/data/transit.db %BACKUP_FILE%
if %errorlevel% equ 0 (
    echo [SUCCESS] Database backed up to %BACKUP_FILE%
) else (
    echo [ERROR] Failed to backup database!
)
goto end

:shell
echo [INFO] Opening shell in backend container...
docker exec -it voice-freight-backend /bin/bash
goto end

:help
echo Voice Freight Broker - Docker Management Script for Windows
echo.
echo Usage: %0 [command]
echo.
echo Commands:
echo   start         Build and start the backend service
echo   stop          Stop the backend service
echo   restart       Restart the backend service
echo   logs [service] View logs (default: backend)
echo   build         Build Docker images with no cache
echo   status        Show application and container status
echo   cleanup       Clean up all Docker resources (WARNING: removes data)
echo   backup        Backup database to ./backups/
echo   shell         Open bash shell in backend container
echo   help          Show this help message
echo.
echo Examples:
echo   %0 start                    # Start the backend
echo   %0 logs                     # View backend logs
echo   %0 logs backend             # View backend logs (explicit)
echo   %0 backup                   # Backup the database
echo.
echo Environment:
echo   Make sure .env file exists with required API keys
echo   See env.example for required variables
goto end

:unknown
echo [ERROR] Unknown command: %1
echo.
call :help
exit /b 1

:end
endlocal 