# ESP32 Editable Trigger Parameters

Use `firmware/esp32_vtab_sentinel/VTAB_Sentinel_ESP32_Parameterized_Complete.ino`.

Edit only the clearly labelled `TRIGGER PARAMETERS` block when calibrating local hardware alarms:

- `TEMP_YELLOW_THRESHOLD` and `TEMP_RED_THRESHOLD` in °C
- `HUMIDITY_YELLOW_THRESHOLD` and `HUMIDITY_RED_THRESHOLD` in % RH
- `WATER_RED_THRESHOLD` as the water sensor raw ADC value
- `MQ2_YELLOW_THRESHOLD` and `MQ2_RED_THRESHOLD` as raw ADC values
- `DOOR_OPEN_WARNING` to include/exclude the simulated door in the local yellow alarm

Timing controls are directly below it. `PUBLISH_INTERVAL=3000` means one VTAB packet every three seconds.

The ESP32 values control local LEDs/buzzer and conversion of raw ADC readings. Configure matching server-side alert values under VTAB Dashboard → Settings so the physical indication and application policy agree.

Never commit the configured Wi-Fi password. The delivered file deliberately contains placeholders.
## Version 4.3 continuous alarm correction

The local ESP32 alarm loop is now independent from the three-second MQTT publish interval.

- Water normal state is raw ADC `0`; a raw reading `> WATER_RED_THRESHOLD` triggers red.
- Default `WATER_RED_THRESHOLD` is `0`, matching the requested module behaviour.
- Water and MQ-2 are sampled continuously.
- DHT22 is sampled every two seconds to respect its sensor timing.
- LED blinking and 150 ms buzzer pulses run on every loop iteration and continue until the condition is normal.
- The Serial packet prints the current water/MQ-2 raw value every three seconds, allowing the falling value to be observed until zero.
- Wi-Fi/MQTT reconnection is non-blocking, so a network outage cannot stop the physical alarm.

## Version 4.4 compact Serial diagnosis

Every telemetry interval, Serial Monitor prints a five-row table containing sensor name, current reading, hardware/simulation source and SAFE/YELLOW/RED status. It also prints the overall state, exact trigger list, buzzer state and MQTT delivery state. The full JSON payload is still transmitted but is no longer printed, keeping the monitor compact.

Example:

```
SENSOR       VALUE          SOURCE       STATUS
Temperature    29.2 C       hardware     SAFE
Humidity       75.9 %       hardware     YELLOW
Water        raw 0          hardware     SAFE
Door         CLOSED         simulated    SAFE
MQ-2         raw 385        hardware     SAFE
OVERALL      : YELLOW WARNING
TRIGGERED BY : HUMIDITY(YELLOW)
BUZZER       : BEEPING - 150 ms every 1 second
MQTT         : PACKET SENT TO VTAB
```
