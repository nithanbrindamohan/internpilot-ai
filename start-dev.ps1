$project = "E:\internpilot-ai"

Start-Process powershell.exe -ArgumentList @(
    "-NoExit"
    "-Command"
    "Set-Location '$project\backend'; & '$project\.venv\Scripts\python.exe' -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"
)

Start-Process powershell.exe -ArgumentList @(
    "-NoExit"
    "-Command"
    "Set-Location '$project\frontend'; npm run dev -- --host 127.0.0.1 --port 5173"
)