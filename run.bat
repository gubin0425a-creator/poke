@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

cd /d "%~dp0"

echo ======================================================================
echo   ⚡ 포켓몬 챔피언스 AI 자동 편집 & 유튜브 업로드 시스템 (테디님 스타일) ⚡
echo ======================================================================

set "INPUT_FILE=%~1"

if "%INPUT_FILE%"=="" (
    echo.
    echo ℹ️ 드래그 앤 드롭된 파일이 없습니다. input 폴더를 검색합니다...
    if exist "input\*.mp4" (
        for %%f in ("input\*.mp4") do (
            set "INPUT_FILE=%%f"
            goto :FOUND
        )
    )
    echo.
    echo ⚠️ 실행 방법:
    echo   1. 편집할 게임 녹화본(.mp4) 파일을 이 run.bat 파일 위로 드래그 앤 드롭하세요!
    echo   2. 또는 이 폴더 안의 'input' 폴더에 녹화본(.mp4)을 넣고 다시 실행하세요.
    echo.
    pause
    exit /b 1
)

:FOUND
echo.
echo 🎬 입력 영상 감지됨: %INPUT_FILE%
echo.

python main.py "%INPUT_FILE%"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ❌ 파이프라인 실행 중 오류가 발생했습니다. (위 로그를 확인하세요)
) else (
    echo.
    echo ✨ 모든 작업이 성공적으로 완료되었습니다! output 폴더를 확인하세요.
)

echo.
pause
