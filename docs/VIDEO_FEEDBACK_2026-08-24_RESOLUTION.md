# Version 2.0.1 Video Feedback Resolution

## Feedback extracted from the 24 August recording

| Reported gap | Root cause | Resolution |
|---|---|---|
| Temperature/humidity repeatedly creates tickets without controlling the environment | Alert recovery existed, but no climate-control action was attached to an environmental incident | A breach now starts one deduplicated L1 control runbook per incident, targets 22°C/50% RH, monitors three safe readings and records verified completion |
| AI Manager should be a right-side chatbot | Version 2.0 implemented it as a navigation page | Replaced with a global floating AI button and right-side evidence-backed drawer available on every screen |
| Predictive values were not visibly connected to real thresholds | Forecast cards omitted the configured rule | Live predictive cards now display current value, forecast, the exact Settings limit, sensor trust and an early-warning state |
| Governed Actions was empty and unclear | Only manually proposed actions populated it | Environmental and software actions now create real lifecycle records automatically; the UI explains standby when none are needed |
| Digital Twin was not a useful 3D view | Initial twin was a hierarchy list | Added a dedicated live 3D server-room equipment view driven by registered devices, components and telemetry state |
| New logo/theme was absent | SVG was packaged but not wired into the application | New VTAB Sentinel logo is used in login/sidebar; premium dark and operational light themes are selectable globally and persisted |
| The update felt incomplete | Phase features were separated from existing operational screens | Climate control appears on Overview; prediction/governance appear inside AI Operations; AI Manager is global; 3D Room has its own operational view |

## Important hardware boundary

The local system uses a **simulated HVAC actuator**. It records and demonstrates the complete AI control lifecycle but cannot physically cool or dehumidify a room until an HVAC relay/controller or building-management integration is installed and configured. The UI states this explicitly. Sensor safety thresholds are not silently changed by prediction: if measured humidity is 77% while the configured limit is 70%, it remains a legitimate breach. Operators may change the approved threshold in Settings, but the AI does not hide unsafe readings by learning a higher baseline.

## Verification

- Backend: 28 passed
- Simulator API: 14 passed
- Main React production build: passed
- Independent Test Lab production build: passed
- New regression coverage: environmental-control deduplication, live threshold forecast evidence, recovery verification and actuator standby transition
