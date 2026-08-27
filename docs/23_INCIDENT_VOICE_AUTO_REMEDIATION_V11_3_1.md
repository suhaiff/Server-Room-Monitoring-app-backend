# V11.3.1 Incident Voice and Backend Auto-Remediation Fix

## Corrections

- Spoken messages no longer say the product name. They announce the actual incident description.
- Recovery wording now states: the named incident has normalized, therefore the related ticket is being closed.
- The MQTT/backend worker now owns automatic remediation. Closing no longer depends on a delayed browser-lab task.
- L1/L2 software tests record: detection and classification, root-cause signature match, remediation start, recovery health verification and automatic closure.
- L3 remains human-approved by design because database/data-integrity recovery must not be performed blindly.

## Expected L1/L2 test timeline

1. Click **Inject L1 failure** or **Inject L2 failure** in Software / AI Lab.
2. Within the next dashboard polling cycle, a real ticket appears.
3. Ticket history shows `software fault injected`, `AI root cause identified` and `AI remediation started`.
4. About eight seconds later, the backend recovery worker performs the controlled verification.
5. The alert resolves, the incident becomes closed and history shows `AI verified recovery`.
6. Voice announces the incident name, says it normalized and says the related ticket is being closed.

## Upgrade

```powershell
docker compose down
docker compose up -d --build backend mqtt-worker software-lab simulator-ui frontend
```

Open `http://localhost:5173` and `http://localhost:5174`, then use `Ctrl+Shift+R` once on both pages.