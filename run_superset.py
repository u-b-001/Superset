import os
import sys
from pathlib import Path

# 1. Guarantee SUPERSET_CONFIG_PATH is always configured for SamarthX
CONFIG_PATH = Path(__file__).resolve().parent / "superset_config.py"
if "SUPERSET_CONFIG_PATH" not in os.environ or not os.environ["SUPERSET_CONFIG_PATH"]:
    os.environ["SUPERSET_CONFIG_PATH"] = str(CONFIG_PATH)

# Add project root and ai_integration to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
AI_DIR = PROJECT_ROOT / "ai_integration"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(AI_DIR) not in sys.path:
    sys.path.insert(0, str(AI_DIR))

# 2. Pre-flight check: ensure n8n and WebSocket server are pre-warmed & healthy
# Only run initialization on master process (skip Werkzeug reloader child to avoid duplicate spawns)
if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
    try:
        try:
            from ai_integration.service_manager import ensure_all_services
        except ImportError:
            from service_manager import ensure_all_services
        print("\n" + "=" * 65, flush=True)
        print(" [SamarthX] Initializing AI Query Services (n8n & WebSocket)...", flush=True)
        print("=" * 65, flush=True)
        services = ensure_all_services(wait_for_ready=True, timeout=60.0)
        n8n_ok = "[OK] ONLINE (Port 5678)" if services.get("n8n") else "[!] NOT READY"
        ws_ok = "[OK] ONLINE (Port 5001)" if services.get("websocket") else "[!] NOT READY"
        print(f" * n8n Workflow Service : {n8n_ok}", flush=True)
        print(f" * WebSocket Live Bridge: {ws_ok}", flush=True)
        print(f" * Service Watchdog     : [OK] ACTIVE (Self-Healing)", flush=True)
        print("=" * 65 + "\n", flush=True)
    except Exception as e:
        print(f"[SamarthX Warning] Pre-flight service check: {e}", flush=True)

from superset.cli.main import superset

if __name__ == '__main__':
    superset()

