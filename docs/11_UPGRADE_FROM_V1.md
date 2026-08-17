# Upgrade an Existing Local Installation to v2

The updated package changes the demo edge device presentation from Arduino to ESP32, adds authenticated UI simulation, an AI Operations Terminal, AI self-tests and browser voice alerts.

## Upgrade procedure

1. Preserve your existing `.env` file.
2. Replace the source folder with the v2 package, then restore `.env`.
3. Rebuild changed application images:

```powershell
docker compose down
docker compose build --no-cache backend ai-service frontend simulator mqtt-worker
docker compose up -d
```

4. The idempotent seed updates the existing demo device name/type/firmware to ESP32 while preserving telemetry.
5. Hard-refresh the browser using `Ctrl+F5`.
6. Open **AI Terminal**, run the self-test and confirm five healthy models.
7. Open **ESP32 Simulator**, submit the Normal and Smoke Emergency scenarios.

If a fully clean demonstration database is desired, use `docker compose down -v` before starting. This permanently removes all local stored data.

## Browser voice requirements

Voice uses the Web Speech API. The dashboard tab must remain open, operating-system audio must be enabled, and the browser must provide a speech voice. Voice is enabled by default and can be toggled in the header or sidebar.
