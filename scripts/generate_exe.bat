REM Convert the python project into executable using pyinstaller
REM Windows 
set PLAYWRIGHT_BROWSERS_PATH=0
playwright install chromium

rmdir /s /q dist

pyinstaller --windowed --noconfirm --name=MahjongCopilot --icon=resources/icon.ico main.py 
if errorlevel 1 (
    echo PyInstaller encountered an error.
    exit /b 1
)
REM copy data/resources
REM robocopy . .\dist\MahjongCopilot settings.json
REM robocopy models dist\MahjongCopilot\models /E
robocopy resources dist\MahjongCopilot\resources /E
robocopy liqi_proto dist\MahjongCopilot\liqi_proto /E
robocopy proxinject dist\MahjongCopilot\proxinject /E
robocopy .\libriichi3p\ dist\MahjongCopilot\libriichi3p\ "Put libriichi3p files in this folder"
mkdir dist\MahjongCopilot\models
mkdir dist\MahjongCopilot\chrome_ext
robocopy . .\dist\MahjongCopilot version
robocopy .venv\Lib\site-packages\playwright\driver\package\.local-browsers dist\MahjongCopilot\_internal\playwright\driver\package\.local-browsers /E
explorer.exe dist

REM make 7z archive 
cd dist
"C:\Program Files\7-Zip\7z.exe" a -t7z MahjongCopilot.windows.7z MahjongCopilot
cd..
