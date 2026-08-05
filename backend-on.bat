@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

rem ============================================================
rem  Pasa el checkout a la rama backend-laravel
rem  Uso: backend-on.bat [ -q ]   (-q = sin pausa, para scripts)
rem ============================================================

set "TARGET=backend-laravel"
set "FOLDER=backend-laravel"
set "OTHER=frontend-react"
set "PAUSEQ="
if /i "%~1"=="-q" set "PAUSEQ=q"

for /f "delims=" %%B in ('git branch --show-current') do set "CURRENT=%%B"

if /i "%CURRENT%"=="%TARGET%" (
    echo Ya estas en la rama %TARGET%. No hay nada que hacer.
    call :maybe_pause
    exit /b 0
)

git rev-parse --verify %TARGET% >nul 2>&1
if errorlevel 1 (
    echo ERROR: no existe la rama %TARGET%.
    call :maybe_pause
    exit /b 1
)

set "DIRTY="
for /f "delims=" %%S in ('git status --porcelain') do set "DIRTY=1"
if defined DIRTY (
    echo.
    echo ERROR: hay cambios sin commitear en la rama actual ^(%CURRENT%^).
    echo        Hace commit o stash antes de cambiar de rama. Operacion cancelada.
    echo.
    call :maybe_pause
    exit /b 1
)

rem Backup de los archivos que la rama destino trackea en %FOLDER%
set "BKDIR=%TEMP%\sm_switch_%TARGET%"
if exist "%BKDIR%" rmdir /s /q "%BKDIR%"
for /f "delims=" %%F in ('git ls-tree -r --name-only %TARGET% -- %FOLDER%') do (
    set "FILE=%%F"
    if exist "%%F" (
        set "FILE=!FILE:/=\!"
        set "DEST=%BKDIR%\!FILE!"
        mkdir "!DEST!\.." >nul 2>&1
        copy /y "!FILE!" "!DEST!" >nul
    )
)

echo Cambiando a la rama %TARGET% ...
git switch %TARGET%
if errorlevel 1 (
    echo ERROR: fallo el switch a %TARGET%.
    call :maybe_pause
    exit /b 1
)

echo Restaurando %OTHER%/ en disco ...
git restore --source=%CURRENT% --worktree -- %OTHER% >nul 2>&1
if errorlevel 1 (
    echo AVISO: no se pudo restaurar %OTHER%/ desde la rama %CURRENT%.
)

echo Re-aplicando tus archivos de %FOLDER%/ ...
for /f "delims=" %%F in ('git ls-tree -r --name-only %TARGET% -- %FOLDER%') do (
    set "FILE=%%F"
    set "FILE=!FILE:/=\!"
    set "DEST=%BKDIR%\!FILE!"
    if exist "!DEST!" copy /y "!DEST!" "!FILE!" >nul
)

echo.
echo Listo. Checkout en %TARGET%.
git status --short
echo.
echo Nota: los archivos listados arriba ^(M^) son cambios que ya estaban en tu
echo carpeta %FOLDER%/ y se re-aplicaron como modificaciones visibles para git.
echo Puedes commitearlos en %TARGET%.
call :maybe_pause
exit /b 0

:maybe_pause
if not defined PAUSEQ pause
exit /b 0
