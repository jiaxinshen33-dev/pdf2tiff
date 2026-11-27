@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 正在打包 PDF转TIFF转换器.exe ...
python -m PyInstaller PDF转TIFF转换器.spec --noconfirm
if %errorlevel% equ 0 (
    echo.
    echo 打包完成！exe 位置：%~dp0dist\PDF转TIFF转换器.exe
) else (
    echo.
    echo 打包失败，请检查上方错误信息。
)
pause
