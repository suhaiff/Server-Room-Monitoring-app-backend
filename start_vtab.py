#!/usr/bin/env python3
"""One-command local launcher for the complete VTAB Sentinel platform.

Run from the project root:
    python start_vtab.py

The script uses only Python's standard library. Docker Compose remains the
process manager, so service dependencies and persistent volumes work exactly
as described in docker-compose.yml.
"""

from __future__ import annotations

import argparse
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
ENV_FILE = PROJECT_ROOT / ".env"
ENV_TEMPLATE = PROJECT_ROOT / ".env.example"

APPLICATIONS = (
    ("VTAB dashboard", "http://localhost:5173", "http://localhost:5173"),
    ("Independent Test Lab", "http://localhost:5174", "http://localhost:5174"),
    ("Test Lab API", "http://localhost:8010/docs", "http://localhost:8010/health"),
    ("Backend Swagger API", "http://localhost:8000/docs", "http://localhost:8000/health"),
    ("AI service API", "http://localhost:8001/docs", "http://localhost:8001/health"),
    ("MinIO console", "http://localhost:9001", "http://localhost:9001"),
    ("Grafana", "http://localhost:3000", "http://localhost:3000/api/health"),
    ("Prometheus", "http://localhost:9090", "http://localhost:9090/-/ready"),
)


def run(command: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    """Run a command from the repository root and stream its output."""
    return subprocess.run(command, cwd=PROJECT_ROOT, text=True, check=check)


def docker_is_ready() -> bool:
    """Return True only when both Docker CLI and Docker Desktop engine work."""
    if shutil.which("docker") is None:
        print("ERROR: Docker was not found. Install and start Docker Desktop first.")
        return False
    result = subprocess.run(
        ["docker", "info"],
        cwd=PROJECT_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if result.returncode != 0:
        print("ERROR: Docker Desktop is installed, but its engine is not running.")
        print("Start Docker Desktop, wait until it says Engine running, and retry.")
        return False
    return True


def prepare_environment() -> None:
    """Create the local development .env without overwriting user settings."""
    if ENV_FILE.exists():
        print("[OK] Existing .env configuration found.")
        return
    if not ENV_TEMPLATE.exists():
        raise FileNotFoundError(".env.example is missing from the project root")
    shutil.copy2(ENV_TEMPLATE, ENV_FILE)
    print("[OK] Created .env from .env.example (local development defaults).")


def url_is_ready(url: str, timeout: float = 2.0) -> bool:
    """Treat any HTTP response as proof that the service accepts connections."""
    try:
        with urllib.request.urlopen(url, timeout=timeout):
            return True
    except urllib.error.HTTPError:
        return True
    except (urllib.error.URLError, TimeoutError, ConnectionError, socket.timeout):
        return False


def wait_for_services(timeout_seconds: int) -> dict[str, bool]:
    """Wait for user-facing HTTP endpoints, printing progress as they appear."""
    pending = {name: health_url for name, _, health_url in APPLICATIONS}
    ready: dict[str, bool] = {}
    deadline = time.monotonic() + timeout_seconds

    print(f"\nWaiting up to {timeout_seconds} seconds for application services...")
    while pending and time.monotonic() < deadline:
        for name, health_url in list(pending.items()):
            if url_is_ready(health_url):
                ready[name] = True
                del pending[name]
                print(f"[READY] {name}")
        if pending:
            time.sleep(2)

    for name in pending:
        ready[name] = False
        print(f"[WAITING] {name} did not become reachable before the timeout.")
    return ready


def print_addresses(ready: dict[str, bool]) -> None:
    """Show the complete hand-off list after startup."""
    print("\n" + "=" * 72)
    print("VTAB SENTINEL APPLICATION ADDRESSES")
    print("=" * 72)
    for name, address, _ in APPLICATIONS:
        state = "READY" if ready.get(name) else "CHECK"
        print(f"[{state:5}] {name:23} {address}")
    print("-" * 72)
    print("Dashboard login: admin@vtab.local / Admin123!")
    print("AI Operations is inside the dashboard; the ESP32 Test Lab is a separate application.")
    print("To stop everything later: python start_vtab.py --stop")
    print("=" * 72)


def start(args: argparse.Namespace) -> int:
    print("VTAB Sentinel - Complete Local Startup")
    print(f"Project: {PROJECT_ROOT}")

    if not docker_is_ready():
        return 1

    try:
        prepare_environment()
    except OSError as exc:
        print(f"ERROR: Unable to prepare environment: {exc}")
        return 1

    if args.fresh:
        print("\nFRESH START requested: removing local Docker volumes and all stored test data...")
        try:
            run(["docker", "compose", "down", "-v", "--remove-orphans"])
        except subprocess.CalledProcessError:
            print("ERROR: Unable to clear the previous local environment.")
            return 1

    command = ["docker", "compose", "up", "-d"]
    if not args.skip_build:
        command.append("--build")

    print("\nStarting database, platform services, dashboard and independent ESP32 Test Lab...")
    try:
        run(command)
    except subprocess.CalledProcessError:
        print("\nERROR: Docker Compose startup failed.")
        print("Run 'docker compose logs --tail=100' to view the detailed error.")
        return 1

    ready = wait_for_services(args.timeout)
    print_addresses(ready)

    # The dashboard is useful only after both its web server and backend respond.
    if not args.no_browser and ready.get("VTAB dashboard") and ready.get("Backend Swagger API"):
        print("\nOpening the VTAB dashboard in your default browser...")
        webbrowser.open("http://localhost:5173", new=2)
        if ready.get("Independent Test Lab"):
            webbrowser.open("http://localhost:5174", new=2)

    if not all(ready.values()):
        print("\nSome optional services are still starting. Check status with:")
        print("  python start_vtab.py --status")
        return 2
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Start and inspect VTAB Sentinel locally.")
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--stop", action="store_true", help="Stop the complete platform.")
    action.add_argument("--status", action="store_true", help="Show Docker service status and addresses.")
    action.add_argument("--logs", action="store_true", help="Follow logs from all services (Ctrl+C exits).")
    parser.add_argument("--skip-build", action="store_true", help="Start existing images without checking for code changes.")
    parser.add_argument("--fresh", action="store_true", help="Delete local Docker volumes/test data before starting (destructive).")
    parser.add_argument("--no-browser", action="store_true", help="Do not open the dashboard automatically.")
    parser.add_argument("--timeout", type=int, default=180, help="Service readiness timeout in seconds (default: 180).")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.timeout < 10:
        print("ERROR: --timeout must be at least 10 seconds.")
        return 1
    if not docker_is_ready():
        return 1

    try:
        if args.stop:
            print("Stopping the complete VTAB Sentinel platform...")
            run(["docker", "compose", "down"])
            print("[OK] VTAB Sentinel stopped. Stored database data was preserved.")
            return 0
        if args.status:
            run(["docker", "compose", "ps", "-a"])
            print_addresses({name: url_is_ready(health) for name, _, health in APPLICATIONS})
            return 0
        if args.logs:
            run(["docker", "compose", "logs", "--tail=100", "--follow"])
            return 0
        return start(args)
    except KeyboardInterrupt:
        print("\nCancelled by user. Running containers were not stopped.")
        return 130
    except subprocess.CalledProcessError as exc:
        print(f"ERROR: Command failed with exit code {exc.returncode}.")
        return exc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
