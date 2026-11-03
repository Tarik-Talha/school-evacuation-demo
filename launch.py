"""Start or reuse this exact local pilot; never stop a different server."""
import argparse
import json
import os
from pathlib import Path
import shlex
import socket
import subprocess
import sys
import time
from urllib.request import urlopen
import webbrowser

ROOT = Path(__file__).resolve().parent
LOGS = ROOT / "runtime"


# =========================================================
# PROJECT IDENTITY AND HIDDEN LOCAL SERVER
# =========================================================
def health(port):
    try:
        with urlopen(f"http://127.0.0.1:{port}/_stcore/health", timeout=1) as response:
            return response.status == 200 and response.read(16).strip() == b"ok"
    except OSError:
        return False


def owner(port):
    script = """[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new($false)
$rows=@(Get-NetTCPConnection -State Listen -LocalPort PORT -ErrorAction SilentlyContinue | ForEach-Object {
 $taskOwner=Get-CimInstance Win32_Process -Filter ('ProcessId='+$_.OwningProcess)
 [PSCustomObject]@{pid=[int]$_.OwningProcess; address=[string]$_.LocalAddress; command=[string]$taskOwner.CommandLine}
})
ConvertTo-Json -InputObject $rows -Compress
""".replace("PORT", str(port))
    completed = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True, timeout=15, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if completed.returncode:
        raise RuntimeError("Port sahibinin kimliği doğrulanamadı.")
    rows = json.loads(completed.stdout.decode("utf-8", errors="replace").strip() or "[]")
    if len(rows) != 1 or rows[0]["address"] != "127.0.0.1":
        raise RuntimeError("Port bu okul pilotu olarak doğrulanamadı; mevcut sunucuya dokunulmadı.")
    args = [part.strip('"') for part in shlex.split(rows[0]["command"], posix=False)]
    expected = str((ROOT / "app.py").resolve()).casefold()
    if (len(args) < 5 or args[1:4] != ["-m", "streamlit", "run"]
        or not Path(args[4]).is_absolute() or str(Path(args[4]).resolve()).casefold() != expected
        or "--server.port" not in args or args[args.index("--server.port") + 1] != str(port)
        or "--server.address" not in args or args[args.index("--server.address") + 1] != "127.0.0.1"):
        raise RuntimeError("Port başka bir uygulamaya ait; mevcut sunucuya dokunulmadı.")
    return rows[0]


def launch(port=8532):
    if type(port) is not int or not 1024 <= port <= 65535:
        raise ValueError("Geçersiz port")
    if os.name != "nt":
        raise RuntimeError("Bu yerel başlatıcı Windows için hazırlanmıştır.")
    LOGS.mkdir(exist_ok=True)
    with socket.socket() as connection:
        connection.settimeout(.3)
        occupied = connection.connect_ex(("127.0.0.1", port)) == 0
    spawned = None
    if occupied:
        owner(port)
    else:
        runtime = ROOT / ".venv" / "Scripts" / "pythonw.exe"
        if not runtime.is_file():
            runtime = Path(sys.executable).with_name("pythonw.exe")
        if not runtime.is_file():
            raise RuntimeError("Python ortamı bulunamadı. README dosyasındaki kurulumu tamamlayın.")
        command = [str(runtime), "-m", "streamlit", "run", str(ROOT / "app.py"),
                   "--server.port", str(port), "--server.address", "127.0.0.1", "--server.headless", "true",
                   "--browser.gatherUsageStats", "false"]
        startup = subprocess.STARTUPINFO()
        startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startup.wShowWindow = subprocess.SW_HIDE
        with (LOGS / "server.log").open("ab", buffering=0) as log:
            process = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.DEVNULL, stdout=log,
                stderr=subprocess.STDOUT, close_fds=True, startupinfo=startup,
                creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_BREAKAWAY_FROM_JOB)
        spawned = process.pid
    deadline = time.monotonic() + 30
    while not health(port):
        if (spawned is not None and process.poll() is not None) or time.monotonic() >= deadline:
            raise RuntimeError("Okul pilotu hazır olmadı. runtime/server.log dosyasını inceleyin.")
        time.sleep(.2)
    verified = owner(port)
    result = {"url": f"http://127.0.0.1:{port}/", "app": str(ROOT / "app.py"),
              "verified_pid": verified["pid"], "spawned_pid": spawned, "hidden": True,
              "action": "reused" if occupied else "started", "health_verified": True}
    (LOGS / "launch.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8532)
    parser.add_argument("--open", action="store_true")
    arguments = parser.parse_args()
    try:
        result = launch(arguments.port)
        print(json.dumps(result))
        if arguments.open:
            webbrowser.open(result["url"])
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as error:
        LOGS.mkdir(exist_ok=True)
        (LOGS / "launcher_error.txt").write_text(str(error), encoding="utf-8")
        raise SystemExit(str(error))
