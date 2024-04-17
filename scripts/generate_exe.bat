REM Convert the python project into executable using pyinstaller
REM Windows 
set PLAYWRIGHT_BROWSERS_PATH=0
playwright install chromium

rmdir /s /q dist\MahjongCopilot
pyinstaller --windowed --noconfirm --name=MahjongCopilot --icon=resources/icon.ico main.py 
if errorlevel 1 (
    echo PyInstaller encountered an error.
    exit /b 1
)
robocopy . .\dist\MahjongCopilot version
REM robocopy . .\dist\MahjongCopilot settings.json
REM robocopy models dist\MahjongCopilot\models /E
robocopy resources dist\MahjongCopilot\resources /E
robocopy liqi_proto dist\MahjongCopilot\liqi_proto /E
robocopy .\libriichi3p\ dist\MahjongCopilot\libriichi3p\ "Put libriichi3p files in this folder"
robocopy .venv\Lib\site-packages\playwright\driver\package\.local-browsers dist\MahjongCopilot\_internal\playwright\driver\package\.local-browsers /E
explorer.exe dist