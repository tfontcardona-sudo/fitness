@echo off
rem Demo de Professional — DOBLE CLIC y listo (Windows).
rem Este .bat existe porque Windows bloquea los .ps1 por defecto ("ejecución de
rem scripts deshabilitada"): un .bat no sufre ese bloqueo y lanza el script
rem saltándose la política SOLO para esta ejecución.
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0demo.ps1"
