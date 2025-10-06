@echo off
setlocal enabledelayedexpansion

:: --- перейти в теку, де лежить скрипт ---
cd /d "%~dp0"

:: --- отримати назву поточної теки ---
for %%I in (.) do set "FOLDER_NAME=%%~nxI"

:: --- видалити старий mylist.txt, якщо є ---
if exist mylist.txt del mylist.txt

echo Generating file list...
for /r %%f in (*.mp4) do echo file '%%~ff' >> mylist.txt

echo Combining all MP4 files into "%FOLDER_NAME%.mp4" ...
ffmpeg -f concat -safe 0 -i mylist.txt -c:v copy -an "%FOLDER_NAME%.mp4"

echo.
echo Running hamster analyzer...
python "..\hamster_wheel_analyzer.py" ^
    --video "%FOLDER_NAME%.mp4" ^
    --motion_thresh 0.1 ^
    --min_blob 1 ^
    --fps_sample 1.0 ^
    --preview_out "%FOLDER_NAME%_preview.mp4"

echo.
echo Done! Results saved for: %FOLDER_NAME%
pause
