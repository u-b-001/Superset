"""
SamarthX AI Integration - Service Lifecycle & Process Manager
═══════════════════════════════════════════════════════════════════════════════
Ensures n8n (port 5678) and SamarthX WebSocket Server (port 5001) are
automatically detected, started, monitored, kept alive, and self-healing.

Features:
- Fully detached background processes immune to terminal closure on Windows.
- Standard I/O redirected to logs/ to avoid broken pipe crashes.
- Automatic stale/zombie port cleanup before binding.
- Continuous background watchdog daemon thread to instantly auto-revive dead services.
═══════════════════════════════════════════════════════════════════════════════
"""

import os
import sys
import io
import time
import socket
import shutil
import logging
import threading
import subprocess
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Any, Set

# Ensure UTF-8 stdout formatting on Windows console to prevent cp1252 encoding crashes
try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

# Configure logger
logger = logging.getLogger("samarthx.service_manager")
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] [ServiceMgr] %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

AI_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = AI_DIR.parent
WS_SCRIPT = AI_DIR / "websocket_server.py"

LOGS_DIR = PROJECT_ROOT / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)
WS_LOG_FILE = LOGS_DIR / "websocket_server.log"
N8N_LOG_FILE = LOGS_DIR / "n8n.log"

N8N_PORT = 5678
N8N_HEALTH_URL = f"http://127.0.0.1:{N8N_PORT}/"
N8N_WEBHOOK_URL = f"http://127.0.0.1:{N8N_PORT}/webhook/ai-chat"
WS_PORT = 5001
WS_HOST = "127.0.0.1"

# Global watchdog management
_watchdog_thread: Optional[threading.Thread] = None
_watchdog_running: bool = False
_watchdog_lock = threading.Lock()


def is_port_open(host: str, port: int, timeout: float = 0.8) -> bool:
    """Checks if a TCP port is actively listening and accepting connections on IPv4 or IPv6."""
    for h in [host, "127.0.0.1", "::1"]:
        family = socket.AF_INET6 if ":" in h else socket.AF_INET
        try:
            with socket.socket(family, socket.SOCK_STREAM) as s:
                s.settimeout(timeout)
                s.connect((h, port))
                return True
        except Exception:
            pass
    return False


def is_n8n_http_ready(timeout: float = 1.5) -> bool:
    """
    Checks if n8n is not just listening on the TCP socket,
    but actually responding to HTTP requests.
    """
    try:
        req = urllib.request.Request(
            N8N_HEALTH_URL,
            headers={"User-Agent": "SamarthX-HealthCheck/1.0"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status in (200, 301, 302, 401, 403)
    except urllib.error.HTTPError:
        # Any HTTP status response means n8n web server is alive and responding
        return True
    except Exception:
        return False


def is_websocket_ready(timeout: float = 0.5) -> bool:
    """Checks if the WebSocket server is listening on port 5001."""
    return is_port_open(WS_HOST, WS_PORT, timeout=timeout)


def kill_process_on_port(port: int) -> bool:
    """
    Finds and terminates any process currently bound to the specified TCP port.
    Prevents 'address already in use' errors and cleans up orphaned/zombie processes.
    """
    killed = False
    if os.name == "nt":
        try:
            cmd = f'netstat -ano | findstr :{port}'
            output = subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.DEVNULL)
            pids: Set[int] = set()
            for line in output.strip().splitlines():
                parts = line.split()
                if len(parts) >= 5 and "LISTENING" in parts:
                    pid_str = parts[-1]
                    if pid_str.isdigit() and int(pid_str) > 0 and int(pid_str) != os.getpid():
                        pids.add(int(pid_str))
            for pid in pids:
                logger.info(f"Terminating stale process {pid} on port {port}")
                subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True)
                killed = True
        except Exception:
            pass
    else:
        try:
            cmd = f"fuser -k {port}/tcp"
            res = subprocess.run(cmd, shell=True, capture_output=True)
            killed = res.returncode == 0
        except Exception:
            pass
    return killed


def find_n8n_command() -> List[str]:
    """
    Determines the best command to start n8n across Windows, Linux, and Mac.
    Prioritizes node with direct n8n bin path, then npm bin, then system PATH.
    """
    # 1. Check user AppData global npm directory on Windows
    appdata = os.environ.get("APPDATA", "")
    if appdata:
        npm_n8n_bin = Path(appdata) / "npm" / "node_modules" / "n8n" / "bin" / "n8n"
        node_exe = shutil.which("node") or r"C:\Program Files\nodejs\node.exe"
        if npm_n8n_bin.exists() and os.path.exists(node_exe):
            return [str(node_exe), str(npm_n8n_bin), "start"]

        n8n_cmd = Path(appdata) / "npm" / "n8n.cmd"
        if n8n_cmd.exists():
            return [str(n8n_cmd), "start"]

    # 2. Check system PATH
    n8n_path = shutil.which("n8n")
    if n8n_path:
        return [n8n_path, "start"]

    node_path = shutil.which("node")
    if node_path:
        return ["n8n", "start"]

    # Default fallback
    return ["n8n", "start"]


def start_n8n_process(force_restart: bool = False) -> Optional[subprocess.Popen[Any]]:
    """Starts n8n in a detached, persistent background process with log redirection."""
    if not force_restart and is_n8n_http_ready():
        logger.info(f"n8n is already active and responding on port {N8N_PORT}.")
        return None

    if force_restart:
        kill_process_on_port(N8N_PORT)
        time.sleep(0.6)

    cmd = find_n8n_command()
    logger.info(f"Launching n8n service: {' '.join(cmd)}")

    env = os.environ.copy()
    env["NODE_OPTIONS"] = "--max-old-space-size=4096"
    env.setdefault("N8N_HOST", "0.0.0.0")
    env.setdefault("N8N_PORT", str(N8N_PORT))
    env.setdefault("N8N_DIAGNOSTICS_ENABLED", "false")
    env.setdefault("N8N_VERSION_NOTIFICATIONS_ENABLED", "false")
    env.setdefault("N8N_TEMPLATES_ENABLED", "false")
    env.setdefault("N8N_HIRING_BANNER_ENABLED", "false")
    env.setdefault("N8N_DISABLE_PRODUCTION_MAIN_PROCESS_WARN", "true")

    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_out = open(N8N_LOG_FILE, "a", encoding="utf-8", buffering=1)

    try:
        if os.name == "nt":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0  # SW_HIDE: hide console window completely
            flags = subprocess.CREATE_NO_WINDOW | 0x00000200  # CREATE_NEW_PROCESS_GROUP
            use_shell = cmd[0].lower().endswith((".cmd", ".bat"))
            proc = subprocess.Popen(
                cmd,
                env=env,
                shell=use_shell,
                stdout=log_out,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                startupinfo=startupinfo,
                creationflags=flags,
                close_fds=True
            )
        else:
            proc = subprocess.Popen(
                cmd,
                env=env,
                stdout=log_out,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                start_new_session=True,
                close_fds=True
            )

        logger.info(f"n8n process launched (PID: {proc.pid}, Log: {N8N_LOG_FILE})")
        return proc
    except Exception as e:
        logger.error(f"Failed to launch n8n process: {e}")
        return None


def start_websocket_process(force_restart: bool = False) -> Optional[subprocess.Popen[Any]]:
    """Starts the WebSocket server in a detached, persistent background process with log redirection."""
    if not force_restart and is_websocket_ready():
        logger.info(f"WebSocket server is already active on port {WS_PORT}.")
        return None

    if force_restart:
        kill_process_on_port(WS_PORT)
        time.sleep(0.6)

    if not WS_SCRIPT.exists():
        logger.error(f"WebSocket server script not found at {WS_SCRIPT}")
        return None

    venv_python = PROJECT_ROOT / "venv_310" / "Scripts" / "python.exe"
    if venv_python.exists():
        python_exe = venv_python
    else:
        python_exe = sys.executable or "python"
    cmd = [str(python_exe), str(WS_SCRIPT)]
    logger.info(f"Launching WebSocket Server: {' '.join(cmd)}")

    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"

    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_out = open(WS_LOG_FILE, "a", encoding="utf-8", buffering=1)

    try:
        if os.name == "nt":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0  # SW_HIDE: hide console window completely
            flags = subprocess.CREATE_NO_WINDOW | 0x00000200  # CREATE_NEW_PROCESS_GROUP
            proc = subprocess.Popen(
                cmd,
                env=env,
                stdout=log_out,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                startupinfo=startupinfo,
                creationflags=flags,
                close_fds=True
            )
        else:
            proc = subprocess.Popen(
                cmd,
                env=env,
                stdout=log_out,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                start_new_session=True,
                close_fds=True
            )

        logger.info(f"WebSocket server process launched (PID: {proc.pid}, Log: {WS_LOG_FILE})")
        return proc
    except Exception as e:
        logger.error(f"Failed to launch WebSocket server process: {e}")
        return None


def wait_for_n8n(timeout: float = 60.0, poll_interval: float = 1.0) -> bool:
    """
    Waits until n8n is responding over HTTP.
    Returns True when n8n is verified ready, False if timeout reached.
    """
    start_time = time.time()
    logger.info(f"Waiting for n8n to warm up on http://127.0.0.1:{N8N_PORT}/ (timeout: {timeout}s)...")

    while time.time() - start_time < timeout:
        if is_n8n_http_ready(timeout=1.0):
            elapsed = round(time.time() - start_time, 1)
            logger.info(f"[OK] n8n is ready and responding! (took {elapsed}s)")
            time.sleep(0.5)
            return True
        time.sleep(poll_interval)

    elapsed = round(time.time() - start_time, 1)
    logger.warning(f"Timed out waiting for n8n after {elapsed}s.")
    return False


def wait_for_websocket(timeout: float = 15.0, poll_interval: float = 0.5) -> bool:
    """
    Waits until the WebSocket server is listening on port 5001.
    Returns True when verified ready, False if timeout reached.
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        if is_websocket_ready(timeout=0.4):
            elapsed = round(time.time() - start_time, 1)
            logger.info(f"[OK] WebSocket server is ready on port {WS_PORT}! (took {elapsed}s)")
            return True
        time.sleep(poll_interval)

    elapsed = round(time.time() - start_time, 1)
    logger.warning(f"Timed out waiting for WebSocket server after {elapsed}s.")
    return False


def ensure_n8n_running(timeout: float = 60.0) -> bool:
    """
    Guarantees n8n is running and responding.
    If not running, starts it and waits for readiness.
    """
    if is_n8n_http_ready():
        return True

    start_n8n_process()
    return wait_for_n8n(timeout=timeout)


def ensure_websocket_running(timeout: float = 15.0) -> bool:
    """
    Guarantees the WebSocket server is running.
    If not running, starts it and waits for readiness.
    """
    if is_websocket_ready():
        return True

    start_websocket_process()
    return wait_for_websocket(timeout=timeout)


def start_service_watchdog(interval: float = 5.0) -> None:
    """
    Starts a persistent daemon thread that monitors both n8n and WebSocket server.
    If either service stops responding or crashes, the watchdog immediately revives it.
    """
    global _watchdog_thread, _watchdog_running
    with _watchdog_lock:
        if _watchdog_thread is not None and _watchdog_thread.is_alive():
            return
        _watchdog_running = True

        def _watchdog_loop():
            logger.info(f"Service Watchdog started (polling every {interval}s)")
            while _watchdog_running:
                try:
                    time.sleep(interval)
                    # Check WebSocket server
                    if not is_websocket_ready(timeout=0.8):
                        logger.warning("Watchdog: WebSocket server not responding on port 5001. Auto-reviving...")
                        start_websocket_process(force_restart=True)
                        wait_for_websocket(timeout=10.0)

                    # Check n8n service
                    if not is_n8n_http_ready(timeout=1.5):
                        logger.warning("Watchdog: n8n service not responding on port 5678. Auto-reviving...")
                        start_n8n_process(force_restart=True)
                        wait_for_n8n(timeout=30.0)
                except Exception as ex:
                    logger.debug(f"Watchdog loop exception: {ex}")

        _watchdog_thread = threading.Thread(
            target=_watchdog_loop,
            daemon=True,
            name="SamarthX-AI-Watchdog"
        )
        _watchdog_thread.start()


def ensure_all_services(wait_for_ready: bool = True, timeout: float = 60.0) -> Dict[str, bool]:
    """
    Ensures both n8n and WebSocket server are running and verified ready.
    Also starts the standing watchdog thread so services remain self-healing forever.
    """
    status = {"n8n": False, "websocket": False}

    if not is_n8n_http_ready():
        start_n8n_process()
    else:
        status["n8n"] = True

    if not is_websocket_ready():
        start_websocket_process()
    else:
        status["websocket"] = True

    if wait_for_ready:
        if not status["n8n"]:
            status["n8n"] = wait_for_n8n(timeout=timeout)
        if not status["websocket"]:
            status["websocket"] = wait_for_websocket(timeout=15.0)

    # Start the continuous watchdog daemon thread
    start_service_watchdog(interval=5.0)

    return status


def stop_all_services() -> None:
    """Stops the services and terminates any listening processes."""
    global _watchdog_running
    _watchdog_running = False
    logger.info("Stopping SamarthX AI services...")
    kill_process_on_port(WS_PORT)
    kill_process_on_port(N8N_PORT)
    logger.info("Services stopped.")


def get_status() -> Dict[str, Any]:
    """Returns current health status of AI integration services."""
    n8n_http = is_n8n_http_ready(timeout=1.0)
    n8n_port = is_port_open("127.0.0.1", N8N_PORT, timeout=0.5)
    ws_port = is_websocket_ready(timeout=0.5)

    return {
        "n8n": {
            "port": N8N_PORT,
            "port_open": n8n_port,
            "http_ready": n8n_http,
            "status": "ONLINE" if n8n_http else ("STARTING" if n8n_port else "OFFLINE")
        },
        "websocket": {
            "port": WS_PORT,
            "port_open": ws_port,
            "status": "ONLINE" if ws_port else "OFFLINE"
        },
        "watchdog": {
            "active": _watchdog_thread is not None and _watchdog_thread.is_alive()
        }
    }


def main():
    """CLI tool for checking and managing background services."""
    action = sys.argv[1].lower() if len(sys.argv) > 1 else "status"

    if action == "status":
        st = get_status()
        print("\n" + "=" * 50)
        print(" SamarthX AI Integration Service Status")
        print("=" * 50)
        print(f" • n8n Service (Port {st['n8n']['port']})      : {st['n8n']['status']}")
        print(f" • WebSocket Server (Port {st['websocket']['port']}) : {st['websocket']['status']}")
        print(f" • Watchdog Monitor           : {'RUNNING' if st['watchdog']['active'] else 'STANDBY'}")
        print("=" * 50 + "\n")
    elif action == "start":
        print("\n[SamarthX] Starting AI Integration Services...")
        res = ensure_all_services(wait_for_ready=True)
        print(f" * n8n Service      : {'[OK] ONLINE' if res['n8n'] else '[!] FAILED'}")
        print(f" * WebSocket Server : {'[OK] ONLINE' if res['websocket'] else '[!] FAILED'}")
        print(" * Service Watchdog : [OK] ACTIVE\n")
    elif action == "stop":
        stop_all_services()
        print("[SamarthX] All services stopped.\n")
    elif action == "restart":
        print("\n[SamarthX] Restarting AI Integration Services...")
        stop_all_services()
        time.sleep(1.0)
        res = ensure_all_services(wait_for_ready=True)
        print(f" * n8n Service      : {'[OK] ONLINE' if res['n8n'] else '[!] FAILED'}")
        print(f" * WebSocket Server : {'[OK] ONLINE' if res['websocket'] else '[!] FAILED'}\n")
    elif action == "watchdog":
        print("\n[SamarthX] Starting persistent Service Watchdog (Press Ctrl+C to stop)...")
        ensure_all_services(wait_for_ready=True)
        try:
            while True:
                time.sleep(1.0)
        except KeyboardInterrupt:
            print("\nWatchdog stopped.")
    else:
        print(f"Unknown action: {action}. Use 'status', 'start', 'stop', 'restart', or 'watchdog'.")


if __name__ == "__main__":
    main()
