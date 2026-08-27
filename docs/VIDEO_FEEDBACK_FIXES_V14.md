# V14 Video Feedback Fixes – Hardware Restore

## Feedback reviewed

The 20 August 14:15 recording demonstrated that temperature simulation worked and the incident recovered correctly, but the component could not be switched back to its physical DHT22 source. The recording also requested simpler wording for the device-registration action.

## Root cause

The Test Lab treated `source.mode == hardware` as both the selected operating mode and proof that physical hardware existed. After selecting simulation, the ESP32 correctly reported the source as simulated. The Test Lab then interpreted that packet as “hardware absent” and disabled the Real hardware button. This created a circular UI lock even though physical readings and ESP32 telemetry continued.

## Fix

- Every sensor now exposes two separate states:
  - `hardware_sensor_ids`: physical sensors available for restoration.
  - `active_hardware_sensor_ids`: sensors currently reading from hardware.
- Availability uses `hardware_available` from the firmware. For compatibility with older firmware, a valid physical pin also proves availability.
- Sensor errors remove that sensor from the available list.
- Changing a component to simulation does not remove its hardware capability.
- Added `Restore detected hardware` in the Test Lab. It restores every detected sensor and leaves unavailable components, including the unconnected door sensor, in simulation.
- A page reload preserves the actual active source instead of falsely displaying all capable sensors as active hardware.
- Updated all included ESP32 firmware variants to publish `hardware_available`.
- Simplified Dashboard → Devices from `Add ESP32 device` to `Add device`.

## Verification procedure

1. Start the stack and open http://localhost:5174.
2. Confirm the ESP32 is online.
3. Select Simulation for Temperature, set an alerting value, and choose Apply selected sources.
4. Confirm the alert/ticket flow operates and normalizes.
5. Select `Restore detected hardware`.
6. Confirm Temperature returns to Hardware and begins showing DHT22 readings.
7. Confirm Door remains Simulation because no reed switch is connected.
8. Open Dashboard → Devices and confirm the main action reads `Add device`.

## Automated verification

- Simulator/API tests: 14 passed.
- Main dashboard production build: passed.
- Test Lab production build: passed.
- Python source compilation: passed.
