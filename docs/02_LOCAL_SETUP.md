# Local setup and VS Code guide

## Docker path

1. Install Docker Desktop and VS Code.
2. Open the `vtab-sentinel` folder in VS Code.
3. In the integrated PowerShell terminal run `Copy-Item .env.example .env`.
4. Run `docker compose up --build`, or select **Terminal > Run Task > VTAB: Start everything**.
5. After services start, open `http://localhost:5173` and sign in with the README demo credentials.
6. Open the independent Test Lab at `http://localhost:5174`; it starts with the normal Compose stack.

The seed command is idempotent and runs when the backend starts.

## Native Python/Node path

Start PostgreSQL/TimescaleDB, Redis, Mosquitto and MinIO yourself, then update `.env` hostnames from service names to `localhost`.

Backend:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
$env:PYTHONPATH="$PWD\backend"
python -m app.seed
uvicorn app.main:app --app-dir backend --reload --port 8000
```

AI service (new terminal): `pip install -r ai_service\requirements.txt` then `uvicorn app:app --app-dir ai_service --reload --port 8001`.

Frontend (new terminal): `cd frontend`, `npm install`, then `npm run dev`.

Simulator (new terminal): `pip install -r simulator\requirements.txt`, then `python simulator\simulate_hardware.py`.
