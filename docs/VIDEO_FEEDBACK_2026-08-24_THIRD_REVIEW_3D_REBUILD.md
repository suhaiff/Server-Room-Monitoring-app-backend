# Third Video Review — WebGL 3D and Workspace UX Rebuild

Release: **VTAB Sentinel 2.1.0**  
Review date: 24 August 2026

## Acceptance findings captured from the recording

| Finding | Root cause | Version 2.1.0 correction |
|---|---|---|
| Telemetry history made pages grow indefinitely | Every database row was rendered into one table | Tables now show 15 rows per page with Previous/Next and numbered navigation |
| Alerts and incidents produced very long pages | Lifecycle cards were not bounded | Alerts show 5 per page and full incident history shows 6 per page |
| Sign out moved far below the visible screen | Sidebar and content shared document height | Desktop navigation and main content now use independent full-height scrolling; Sign out remains at the bottom |
| Existing room was not a real 3D environment | It used CSS transforms and flat HTML panels | Replaced completely with a Three.js/React Three Fiber WebGL room |
| Room could not be inspected naturally | Previous interaction only changed a CSS rotation number | Added orbit, wheel zoom, right-drag pan, damping, reset, fullscreen and five camera presets |
| Server-room equipment was incomplete | Scene only showed simplified rack blocks | Added four detailed racks, server units and LEDs, precision HVAC, ceiling lights, DHT22, MQ-2, floor leak probe, physical door and magnetic contact |
| 3D room did not communicate operational state | It did not use alert/ticket state and had limited sensor mapping | Live telemetry, effective thresholds, alerts and incidents now control door position, leak pool, smoke plume, rack LEDs and emergency lighting |
| AI Operations was congested and difficult to read | All diagnostics, predictions, models and logs were on one long page | Split into System health, Predictive intelligence, Model pipeline and Execution evidence views |
| “LIVE 2.5 SEC” looked like an internal implementation detail | Refresh interval was used as the primary status label | Replaced with Live monitoring and a human-readable last-update time |
| Copilot icon looked static and old | It reused the shield brand image | Added an animated bot with antenna, scan line, status signal and floating motion |
| Copilot had a horizontal scrollbar | Prompt chips forced a single non-wrapping row | Prompts use a responsive grid and all drawer regions prevent horizontal overflow |
| Light mode looked flat and less polished | Several dark-first surfaces had weak light overrides | Added stronger contrast, panel separation, shadows, readable controls and a complete light Copilot treatment |
| Manual/Auto thresholds must remain unchanged | This feature passed acceptance | Preserved the verified 2.0.4 contract and used each rule’s effective threshold in the 3D room |

## 3D operation

Open **3D Room** from the main dashboard.

- Left-drag: orbit around the room.
- Mouse wheel: zoom.
- Right-drag: pan.
- Camera buttons: Overview, Racks, Top, Door and Leak.
- Select a rack, sensor, HVAC unit or door to view its evidence.
- Fullscreen expands the WebGL room.
- A live unsafe condition changes affected equipment and activates emergency lighting.

The scene is procedurally modelled in code, so no external model download, account or asset licence is required. The 3D dependency chunk is loaded only when this page is opened.

## Developer verification

From the frontend directory, run **pnpm test** and **pnpm run build**.

For full system checks, run **python start_vtab.py**, then verify **docker compose ps**.

Test normal, high temperature, high humidity, water leak, smoke and open-door scenarios from the independent Test Lab at http://localhost:5174. Confirm that http://localhost:5173 updates both the ticket lifecycle and 3D room.

## Browser compatibility

WebGL2 is recommended. Current Chrome, Edge and Firefox releases are supported. Hardware acceleration should be enabled for the smoothest orbit and emergency animation.
