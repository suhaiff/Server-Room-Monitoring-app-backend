# VTAB Sentinel 2.2.0 — Video Acceptance Redesign

Date: 2026-08-24

## Scope reviewed

This release implements the complete feedback from the 12:15 screen recording and the additional instruction to discard and rebuild the white theme. Existing working capabilities—Devices, Telemetry, Alerts, Incidents, AI Operations, ESP32/Test Lab ingestion, adaptive thresholds, governed recovery, voice preferences and the editable 3D room—remain available.

## Acceptance checklist and completed corrections

| # | Feedback / required outcome | Root cause | Implemented correction |
|---|---|---|---|
| 1 | Header controls must look aligned and professional | Theme, voice and refresh controls used unrelated dimensions | Applied one compact control height, spacing, border and icon system |
| 2 | Overall dashboard needed a more modern operational presentation | Pages had accumulated unrelated card patterns | Added shared raised panels, hierarchy, spacing and status treatments |
| 3 | Overview must summarize the whole system instead of repeating a long alert list | Overview reused alert-page content | Rebuilt it as a cross-system command summary with fleet, ticket, AI and latest-event modules |
| 4 | Closed incidents must be obviously successful | Closed records looked similar to active tickets | Added full green completion treatment, CLOSED chip and lifecycle verification footer |
| 5 | Incident counts must show useful daily and overall context | Only a single undifferentiated count was visible | Added Open now, Opened today, Closed today, Closed overall and Critical open counters |
| 6 | Existing AI Operations, Devices, Telemetry and Alerts functions must remain | Redesign risked removing established workflows | Navigation and functional components were preserved and regression-tested |
| 7 | 3D emergency mode should visibly illuminate the room red; healthy mode should be green | Scene lighting did not communicate state strongly enough | Added state-aware ceiling emissive materials and central red/green operational lighting |
| 8 | 3D room must be darker, more immersive and smoother | High pixel ratio, repeated contact-shadow rendering and oversized shadows increased work | Darkened environment and fog; reduced DPR/shadow resolution; cached contact shadows |
| 9 | Reports needed a denser, superior executive and engineering view | Report cards lacked a decision hierarchy | Added evidence overview band, closure rate, severity workspace, live service health and findings |
| 10 | Settings needed clear organization | Threshold, voice, display, recovery and export controls were mixed | Reorganized into Monitoring rules, Operator experience, Automation policy and Data/logs |
| 11 | Copilot floating control and drawer alignment needed correction | Drawer content and button treatments were inconsistent | Unified the floating control, guided strip, content spacing and responsive positioning |
| 12 | Copilot suggestions must visibly run and lead to useful workflows | Prompt buttons provided weak feedback and assistant responses were text-only | Added working state, auto-scroll, evidence confidence and action buttons that open the correct page |
| 13 | Scrollbars should fit both themes | Native scrollbars visually clashed with the dashboard | Added compact theme-aware application scrollbars |
| 14 | Existing white theme was ineffective and must be replaced | Legacy light overrides were fragmented across the stylesheet | Removed all legacy light overrides and rebuilt one complete light palette with readable text, panels, tables, forms, alerts, 3D controls, Copilot and status colors |

## Copilot behavior

The backend assistant now routes questions by intent: forecast, recovery workflow, incident priority, system health and sensor/climate. Responses remain database-evidence-backed and return suggested dashboard actions. The frontend shows those actions as buttons and navigates within the application without a reload.

## Verification performed

- Backend integration tests: 29 passed.
- Main frontend tests: 22 passed.
- Simulator tests: 14 passed.
- Main React production build: passed.
- Simulator React production build: passed.
- New acceptance checks cover Overview, ticket counters and closure presentation, Reports, Settings, Copilot actions, 3D performance/state lighting and the rebuilt light palette.

## Developer startup after replacing the project

From the repository root:

```powershell
python start_vtab.py
```

Or rebuild Docker explicitly:

```powershell
docker compose down
docker compose build --no-cache frontend backend simulator-ui
docker compose up -d
```

Then open:

- Main application: http://localhost:5173
- ESP32 Test Lab: http://localhost:5174
- Backend API: http://localhost:8000/docs

Use Ctrl+F5 once after the rebuild so the browser does not reuse an older JavaScript or CSS bundle.