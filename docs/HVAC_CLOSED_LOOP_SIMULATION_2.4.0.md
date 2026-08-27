# VTAB Sentinel 2.4.0 — Closed-loop AI Cooling Simulation

## Outcome

The independent Test Lab now contains a per-device cooling/HVAC simulator. It models room temperature over time instead of directly forcing a final temperature value. Every thermal step publishes the modeled temperature through MQTT, so PostgreSQL/TimescaleDB ingestion, adaptive thresholds, alerts, incidents, AI analysis, the dashboard and recovery workflow are all exercised.

## What was missing before 2.4.0

The earlier system could detect a high temperature and record a `balance_cooling_setpoint` recommendation. It did not model ambient heat, server heat, cooling output or thermal inertia. It also had no lower-temperature safety alert, so excessive cooling was not treated as a harmful condition. Physical HVAC control remains intentionally disabled until a real actuator gateway is configured.

## Thermal model

Each registered device has an independent state containing:

- room temperature;
- outside/ambient temperature;
- server heat load in kW;
- cooling output from 0 to 100%;
- target temperature;
- Off, Manual or AI Auto control mode;
- temperature trend and simulated elapsed time.

One UI step represents one simulated minute. The model combines server heat gain, heat exchange with ambient air and cooling removal. It is deterministic, so the same starting state and controls produce the same result.

## Safety and AI policy

| Condition | Result |
|---|---|
| 18°C to active upper limit | Safe operating band |
| Below the adaptive minimum | Excessive-cooling warning and `reduce_cooling_output` action |
| At or below 15°C | Critical cold alert and incident |
| Above the active upper limit | High-temperature alert and `balance_cooling_setpoint` action |
| At or above 40°C | Critical high safety ceiling |
| Three consecutive safe readings | AI-verified recovery and automatic ticket closure |

In Manual threshold mode, the minimum safe temperature is 18°C. In Auto mode, the minimum is learned from the recent normal baseline minus 5°C, constrained to 18–22°C. The 15°C critical floor cannot be learned away. The existing adaptive high limit remains the greater of the configured limit and learned baseline plus 3°C, capped by the 40°C hard safety ceiling.

## Test Lab procedure

1. Start the full application with `python start_vtab.py`.
2. Open `http://localhost:5174`.
3. Select the registered device.
4. Open **AI Cooling System** in **Devices / Components**.
5. Select a control mode:
   - **Off**: cooling is disabled; server and ambient heat can raise room temperature.
   - **Manual**: the operator controls cooling output.
   - **AI Auto**: the controller recalculates output each minute to approach the target.
6. Adjust ambient temperature, server heat load, cooling output and target temperature.
7. Use **Step 1 minute** for controlled testing or **Start live model** for continuous operation.
8. Watch the room trend and MQTT/AI pipeline state in the Test Lab.
9. Open the main dashboard at `http://localhost:5173` and verify the same temperature in Overview/Telemetry, then inspect Alerts, Incidents and AI Operations.

## Recommended acceptance scenarios

### Cooling failure / overheating

Set mode to Off, ambient to 40°C and server heat to 35–50 kW. Run until the active upper threshold is crossed. Confirm a high-temperature ticket and an increase-cooling AI action.

### Excessive cooling

Set Manual mode, cooling output to 100%, ambient to 10–15°C and server heat to 0 kW. Run until the room falls below 18°C. Confirm `temperature_low_threshold`; continue to 15°C or below to verify critical escalation.

### AI Auto recovery

Start from a hot room, select AI Auto and a 22°C target. Confirm output rises when hot, reduces when cold and settles as the room approaches target. The modeled temperature continues through MQTT and is not written directly to the dashboard.

### Verified ticket closure

After creating a hot or cold ticket, return the modeled room to its safe band. Publish at least three consecutive safe thermal steps. Confirm the alert closes, the incident timeline records normalization and AI verification, and the climate action becomes verified.

## Production boundary

This feature is a software actuator simulation. It does not switch a real compressor, fan or relay. Production HVAC control requires an authenticated actuator gateway, device acknowledgements, command timeout/fail-safe behavior, maintenance interlocks, role approval policy and site-specific safety review. The backend reports `physical_hvac_configured: false` until that integration exists.

## Verification

- Simulator/API tests: 17 passed.
- Backend workflow tests: 31 passed.
- Dashboard tests: 31 passed.
- Main React production build: passed.
- Test Lab React production build: passed.