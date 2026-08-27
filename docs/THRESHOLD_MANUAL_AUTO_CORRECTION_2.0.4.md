# Manual and Auto Threshold Modes — Version 2.0.4

## Corrected requirement

Temperature and humidity thresholds have two explicitly selected operating modes.

### Manual mode

- Manual is the default.
- The alert engine uses exactly the value entered by the operator in Settings.
- Incoming normal readings do not change the active threshold.
- The selected mode and active value are displayed on Overview, Telemetry and AI Operations.

### Auto mode

- Auto operates only after the user selects Auto and saves that sensor.
- The system initially uses the configured value as a safe fallback.
- It collects eight valid temperature or humidity readings.
- The median of recent readings becomes the normal operating baseline.
- Temperature auto threshold is the higher of the configured minimum or baseline + 3°C.
- Humidity auto threshold is the higher of the configured minimum or baseline + 5%.
- The calculated threshold is displayed as the active threshold throughout the main application.
- Settings shows AUTO LEARNING until enough data is available, then AUTO ACTIVE with baseline and active threshold evidence.

### Safety

The hard safety ceiling is independent of the selected mode:

- Temperature: 40°C.
- Humidity: 90%.

These ceilings prevent either a manual configuration or an automatically learned baseline from suppressing a critical environmental condition.

## Persistence

The selection is stored per organization and measurement type in the existing `system_configurations` table under the `threshold_modes` key. This avoids an unsafe automatic database-column migration on existing installations.

## Verification

The backend regression test performs the following sequence:

1. Select Manual with humidity threshold 70 and verify the effective threshold remains 70.
2. Select Auto and verify the saved mode is returned.
3. Publish stable 77% readings.
4. Verify Auto becomes active with baseline 77 and active threshold 82.
5. Publish 92% humidity and verify the hard ceiling creates a critical alert.

