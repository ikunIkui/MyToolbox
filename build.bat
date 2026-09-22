@echo off
chcp 65001 >nul
setlocal

echo ============================================================
echo  MyToolbox 一键打包
echo ============================================================
echo.

set VERSION=0.5.0

:: 检查虚拟环境
if not exist venv\Scripts\python.exe (
    echo [错误] 没找到 venv\Scripts\python.exe
    echo 请先运行：python -m venv venv
    pause
    exit /b 1
)

echo [1/3] 清理旧的构建产物...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist Output rmdir /s /q Output

echo.
echo [2/3] PyInstaller 打包...
venv\Scripts\python.exe -m PyInstaller ^
    -D -w ^
    --name MyToolbox ^
    --icon=res/app.ico ^
    --add-data "res;res" ^
    --hidden-import=winotify ^
    --hidden-import=winsdk ^
    --hidden-import=docx ^
    --hidden-import=reportlab ^
    --hidden-import=reportlab.pdfbase.cidfonts ^
    --hidden-import=PySide6.QtMultimedia ^
    main.py

if errorlevel 1 (
    echo.
    echo [错误] PyInstaller 打包失败
    pause
    exit /b 1
)

echo.
echo [3/3] Inno Setup 编译安装包...
set ISCC="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if not exist %ISCC% (
    set ISCC="C:\Program Files\Inno Setup 6\ISCC.exe"
)
if not exist %ISCC% (
    echo [错误] 没找到 Inno Setup 编译器
    echo 请安装 Inno Setup 6: https://jrsoftware.org/isdl.php
    pause
    exit /b 1
)

%ISCC% setup.iss

if errorlevel 1 (
    echo.
    echo [错误] Inno Setup 编译失败
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  打包完成！
echo ============================================================
echo.
echo  绿色版： dist\MyToolbox\
echo  安装包： Output\MyToolbox_Setup_%VERSION%.exe
echo.

if exist Output explorer Output

pause