$root = "E:\internpilot-ai"
$python = "$root\.venv\Scripts\python.exe"

$backend = @{
    File = $python
    Args = @("-m", "uvicorn", "app.main:app",
             "--host", "127.0.0.1", "--port", "8000")
    Folder = "$root\backend"
}

$frontend = @{
    File = "cmd.exe"
    Args = @("/c", "npm run dev -- --host 127.0.0.1 --port 5173")
    Folder = "$root\frontend"
}

function Start-Server($server) {
    Start-Process `
        -FilePath $server.File `
        -ArgumentList $server.Args `
        -WorkingDirectory $server.Folder `
        -PassThru `
        -WindowStyle Hidden
}

$backendProcess = $null
$frontendProcess = $null

while ($true) {
    if ($null -eq $backendProcess -or $backendProcess.HasExited) {
        $backendProcess = Start-Server $backend
    }

    if ($null -eq $frontendProcess -or $frontendProcess.HasExited) {
        $frontendProcess = Start-Server $frontend
    }

    Start-Sleep -Seconds 10
}