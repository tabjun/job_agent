@echo off
setlocal EnableExtensions DisableDelayedExpansion
chcp 65001 >nul
title Resume Workspace - PC Connector
cd /d "%~dp0" || goto failed
if not exist "pyproject.toml" goto extract_first
if not exist "uv.lock" goto extract_first
if not exist "job_agent\ui\launcher.py" goto extract_first
set "PATH=%USERPROFILE%\.local\bin;%LOCALAPPDATA%\Microsoft\WinGet\Links;%PATH%"
where uv >nul 2>&1
if errorlevel 1 goto install_uv
:ready
echo [1/2] 연결 도구 준비 중입니다. 첫 실행은 인터넷과 몇 분의 시간이 필요합니다.
call uv sync --locked --extra browser
if errorlevel 1 goto failed
echo [2/2] 본인 PC의 연결 창을 엽니다. 이 창은 사용 중 닫지 마세요.
call uv run --no-sync python -m job_agent.ui.launcher %*
if errorlevel 1 goto failed
echo 연결 도구를 종료했습니다.
pause
exit /b 0
:install_uv
echo 실행에 필요한 uv가 없습니다. 공식 WinGet 패키지로 설치할 수 있습니다.
choice /C YN /N /M "uv 설치를 진행할까요? [Y/N] "
if errorlevel 2 goto no_uv
where winget >nul 2>&1
if errorlevel 1 goto no_uv
call winget install --id astral-sh.uv --exact --source winget
if errorlevel 1 goto no_uv
where uv >nul 2>&1
if errorlevel 1 goto no_uv
goto ready
:extract_first
echo ZIP 안에서 실행하지 마세요. 먼저 '모두 압축 풀기'로 새 폴더에 압축을 풀어 주세요.
goto failed
:no_uv
echo uv 설치 후 이 파일을 다시 실행하세요. WinGet이 없으면 Microsoft 앱 설치 관리자가 필요합니다.
echo 공식 설치 안내: https://docs.astral.sh/uv/getting-started/installation/
echo 회사 PC의 설치 제한은 관리자에게 문의하세요. 보안 경고를 우회하지 마세요.
:failed
echo 실행을 완료하지 못했습니다. 위 오류를 확인하고 사용 예시의 수동 실행 안내를 보세요.
pause
exit /b 1
