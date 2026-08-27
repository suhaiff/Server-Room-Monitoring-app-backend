# Version 2.4.0 — Closed-loop AI cooling simulation

- Added a per-device HVAC thermal model to the independent Test Lab.
- Added Off, Manual and AI Auto cooling modes with ambient and server heat-load inputs.
- Routed every modeled temperature through MQTT, database ingestion, thresholds, alerts and AI.
- Added excessive-cooling warnings, a 15°C critical floor and `reduce_cooling_output` actions.
- Added adaptive lower temperature limits, cold forecasts and safe-band rendering throughout the dashboard.
- Added deterministic model, MQTT provenance, alert lifecycle and recovery tests.
# Version 2.3.1 — Residual sign-off corrections

- Replaced duplicate Overview temperature with incident closure rate.
- Fixed Copilot's six-section grid so evidence chips no longer stretch into large oval columns.
- Equalized Reports severity and backend-service panel heights.
- Corrected the light theme to target the themed shell's actual main canvas and header.
- Added dimensional light rendering for AI pipeline, tabs, diagnostics, Settings and Copilot.
- Added focused residual acceptance coverage.
# Version 2.3.0 — Final video sign-off

- Restored the requested Overview information order and added compact latest-alert/today-ticket insights after the live trend.
- Added a 12-option persistent Overview layout composer with automatic responsive alignment.
- Added seven-day ticket-handling and AI-performance trend reporting.
- Expanded and reorganized operator settings and report composition controls.
- Replaced the square Copilot construction with a fully circular, centered animated control.
- Added a working New chat action and corrected Copilot/drawer lower-right alignment.
- Removed the prior light block and rebuilt a dimensional, information-complete light theme.
- Added final sign-off acceptance tests.
# Version 2.2.0 — Complete acceptance redesign and white-theme rebuild

- Rebuilt Overview into a concise cross-system command summary.
- Added daily/open/closed/critical incident counters and unmistakable green closure states.
- Modernized the operational shell, header controls, Reports and organized Settings.
- Made Copilot prompts visibly execute and added evidence-linked workflow navigation actions.
- Strengthened red emergency and green healthy 3D lighting while reducing render cost.
- Added integrated theme-aware scrollbars.
- Removed the fragmented legacy white theme and rebuilt all light-mode component coverage.
- Added focused acceptance tests and verified backend, frontend and simulator suites.
# Version 2.1.2 — Login viewport correction

- Constrained the login logo and branding inside the card.
- Replaced the fixed form width with a responsive width and desktop maximum.
- Restored login scrolling for short and mobile viewports.
- Added compact-height and mobile layout rules plus regression tests.

# Version 2.1.1 — Fourth video-review correction

- Rebuilt the WebGL room lighting and complete room enclosure.
- Moved the access door into a coordinated side-wall opening.
- Added persistent, browser-saved placement editing for racks, lights, door, HVAC and sensors.
- Reduced and unified the Copilot control.
- Replaced the unclear Overview climate block with operating limits and safety margins.
- Kept the five-stage AI pipeline permanently visible and enlarged predictive evidence.
- Removed the sidebar overlay and made navigation independently scrollable.
## 2.1.0 — 2026-08-24

- Completely removed the CSS pseudo-3D scene and introduced a genuine WebGL server-room digital twin.
- Added real orbit, zoom, pan, fullscreen, reset and five camera viewpoints.
- Added detailed racks, server units, HVAC, lights, DHT22, MQ-2, leak probe, door and magnetic contact assets.
- Connected live telemetry, effective thresholds, active alerts and tickets to room animations and emergency state.
- Added pagination to telemetry, alerts and incidents, plus a fixed-height desktop workspace and persistent Sign out.
- Reorganized AI Operations into four readable views and replaced the interval label with human-readable live status.
- Replaced the static Copilot shield with an animated bot and removed all horizontal drawer overflow.
- Upgraded light mode contrast and component coverage.
- Added 3D, pagination, AI layout and Copilot regression tests.

## 2.0.4 — 2026-08-24

- Corrected environmental thresholds to explicit Manual and Auto modes.
- Manual is the default and always uses the operator-entered value.
- Auto learning begins only after the mode is selected and saved.
- Auto state, normal baseline and calculated active threshold are visible throughout the application.
- Persisted mode selection through the existing system configuration store, avoiding a database schema migration.
- Added backend and frontend regression coverage for the mode contract.
## 2.0.3 — 2026-08-24

- Fixed AI Operations runtime crash caused by a missing ShieldCheck import.
- Added auditable adaptive temperature/humidity limits with hard safety ceilings.
- Restored a true drag-to-rotate 360° server-room digital twin and room-wide warning state.
- Completed light theme coverage and changed theme control to sun/moon icons.
- Replaced the asymmetric logo and upgraded the floating Operations Copilot.
- Added predictive evidence details and regression coverage.
- Verified: backend 29, simulator 14, frontend 4 tests; both UI production builds pass.
# VTAB Sentinel 2.0 Release Notes

- Retained the VTAB Sentinel name and introduced the Sense · Reason · Resolve identity.
- Added AI Manager with database-evidence citations and conversational continuity.
- Added governed remediation records, L1 automatic completion and L2/L3 approval decisions.
- Added trend forecast, anomaly scoring, sample confidence and sensor trust indicators.
- Added organization/site/room/device/component digital-twin API and UI.
- Added versioned knowledge/runbook endpoints.
- Preserved Add Device, Add Component, simulation-only defaults and verified-hardware switching.
- Added four Version 2.0 API tests; the complete backend suite now has 27 tests.

External LLM and premium neural TTS providers remain optional adapters requiring separate credentials and governance review. Local operation does not depend on either.

## Version 2.0.1 — video feedback completion

- Added deduplicated environmental-control runbooks with 22°C/50% RH balance targets and three-reading recovery verification.
- Moved AI Manager into a floating right-side assistant available across the application.
- Connected predictions to the current Settings thresholds and added explicit early warnings.
- Populated governed actions automatically from climate and software recovery activity.
- Restored a dedicated live 3D server-room equipment view.
- Applied the VTAB Sentinel logo and persistent premium light/dark themes.
- Added full feedback resolution documentation and expanded backend coverage to 28 tests.

## Version 2.0.2 — dashboard startup hotfix

- Fixed the `theme is not defined` runtime failure by initializing persisted theme state inside the main React application.
- Removed the unused legacy AgentCenter import.
- Added and passed a frontend regression test verifying theme initialization occurs before dashboard rendering.


