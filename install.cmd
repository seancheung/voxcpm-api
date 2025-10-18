@echo off
setlocal enabledelayedexpansion

cd /D "%~dp0"

@REM load env
if exist env.txt (
    for /f "delims=" %%i in (env.txt) do set %%i
)

:venv
@REM check venv
if exist "%venv_dir%" (
    call "%venv_dir%\Scripts\activate.bat" || ( echo . && echo failed activate venv && goto :error )
    goto :install
)

@REM check uv
call uv --version || ( echo . && echo uv not found && goto :error )

@REM create venv
call uv venv --seed --python "%python_ver%" "%venv_dir%" || ( echo . && echo failed to create venv && goto :error )
goto :venv

:install
@REM install deps
if not exist "%installed_file%" (
	echo Installing dependencies...
    if defined torch_cuda_install call uv pip install %torch_cuda_install% || (echo. && echo failed to install dependencies && goto :error)
    if defined extra_install call uv pip install %extra_install% || (echo. && echo failed to install dependencies && goto :error)
    if exist requirements.txt call uv pip install -r requirements.txt || ( echo. && echo failed to install dependencies && goto :error )
	echo. 2>"%installed_file%"
) else (
    echo "%installed_file%" already exists. Delete it to reinstall dependencies.
)

:end
exit /b 0

:error
pause