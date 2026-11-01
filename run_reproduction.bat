@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 reproduce_paper1.py %*
  goto :done
)
where python >nul 2>nul
if %errorlevel%==0 (
  python reproduce_paper1.py %*
  goto :done
)
echo Python 3 was not found. Install Python 3, then run this file again.
exit /b 1
:done
if %errorlevel%==0 echo.
if %errorlevel%==0 echo Open reproduction_report.html in a browser.
exit /b %errorlevel%
