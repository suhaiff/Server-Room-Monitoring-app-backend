# VTAB Sentinel — Second Video Review (V6)

This update is based on the complete feedback recording captured on 14 August 2026 at 08:21.

## Confirmed findings, root causes and fixes

| # | Finding | Root cause | Fix |
|---|---|---|---|
| 1 | A temperature above 30 °C raised a ticket, but the Overview graph remained green | The chart used a fixed green stroke and fill | The trend now changes to red, displays `HAZARD` and receives a red glow above 30 °C |
| 2 | Test Lab displayed `MQTT WAITING` although packets and receipts worked | The label relied on a transient Paho socket flag rather than verified processing | Removed the misleading badge; the header reports stream state and the process strip reports MQTT/database/AI progress |
| 3 | Test Lab header and process strip were poorly aligned and static | The strip contained passive labels with no state | Added aligned stream status, animated transport indicators and explicit stage states |
| 4 | Live streaming had to be started manually | Initial React state was disabled | Live streaming now starts by default and publishes every eight seconds |
| 5 | Devices page was blank | `DeviceInventory` used `Cpu` without importing it, causing a `ReferenceError` | Imported the icon and retained the ESP32 plus five sensor-module inventory |
| 6 | Telemetry did not identify chart lines | No Recharts legend or friendly series names were configured | Added a Temperature/Humidity legend and labelled thresholds |
| 7 | Leak, door and smoke activity had no chart | Only continuous environmental measurements were visualized | Added a separate NORMAL/TRIGGERED step chart for all three binary sensors |
| 8 | Reports page was blank | A PostgreSQL diagnostic object was rendered directly, causing React error 31 | Diagnostic objects are converted into readable key/value text; request errors have a visible panel |
| 9 | Page exceptions produced an unexplained blank screen | No top-level React error boundary existed | Added a clear recovery screen with a reload action |
| 10 | Simulator tests failed after the earlier status change | Test MQTT clients did not implement `is_connected()` | Successful QoS-1 acknowledgement is now authoritative connection evidence |

## Verification results

- Backend API: **10 passed**.
- Independent simulator, including all six scenarios: **9 passed**.
- AI model service: **5 passed**.
- Dashboard production build: **passed**.
- Test Lab production build: **passed**.
- Browser reproduction confirmed both original blank-page exceptions.
- Corrected Test Lab preview rendered without JavaScript errors.

## Retest procedure

Rebuild the changed images so Docker does not serve an older browser bundle:

```powershell
python start_vtab.py --fresh
```

To preserve existing test history, use:

```powershell
docker compose up -d --build frontend simulator-api simulator-ui
```

Then press `Ctrl+F5` on `http://localhost:5173` and `http://localhost:5174`.

