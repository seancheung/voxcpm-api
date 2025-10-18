@echo off
setlocal enabledelayedexpansion

cd /D "%~dp0"

set HF_HOME=%~dp0huggingface
set TORCH_HOME=%~dp0torch
set MODELSCOPE_CACHE=%~dp0modelscope
set HF_ENDPOINT=https://hf-mirror.com

call install.cmd

@REM run
call uv run api.py || ( echo. && echo failed to start app && goto :error )

:end
exit /b 0

:error
pause