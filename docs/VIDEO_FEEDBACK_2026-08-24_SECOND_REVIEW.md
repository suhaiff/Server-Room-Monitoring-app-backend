# VTAB Sentinel 2.0.3 — Second Video Feedback Resolution

Date: 24 August 2026

This release resolves every actionable item identified in the second 24 August video review. It preserves the multi-device registry, unified Test Lab, incident lifecycle, voice recovery, software remediation and evidence-linked AI operations from earlier versions.

## Feedback, root cause and resolution

| Feedback | Root cause | Resolution |
|---|---|---|
| AI Operations page displayed an error | `IntelligenceGovernance` rendered `ShieldCheck` without importing it | Imported the icon and added a React server-render regression test that executes the component |
| Overview showed a fixed humidity limit and remained alarming during a stable higher operating pattern | Dashboard and alert engine read only the configured threshold | Added an adaptive operating threshold based on the median of up to 60 recent valid readings; it activates after 8 samples |
| Dynamic adjustment could hide a real danger | A purely adaptive limit has no absolute safety guard | Added immutable hard safety ceilings: 40°C temperature and 90% humidity. Reaching a ceiling always creates a critical alert |
| Prediction model detail looked absent | The AI Operations crash hid the panels; prediction cards also exposed too little evidence | Restored the page and added current value, forecast, adaptive limit, baseline, configured base, safety ceiling, sample count, trust and anomaly score |
| Theme switch was text-heavy | The original control used only text | Replaced it with sun/moon icons, persistent selection and accessible labels |
| Light theme was incomplete | Several newer Version 2 panels had no light-theme overrides | Added full white/ice surfaces for navigation, cards, settings, diagnostics, lifecycle, pipeline, tables, device panels and forms |
| 3D Room was a flat illustration | The previous scene used perspective styling but no rotatable 3D world | Rebuilt it as a CSS 3D room with walls, floor, ceiling, three-dimensional racks, drag rotation, arrow controls and reset |
| Room danger state was too subtle | Only the affected rack border changed | Added room-wide red emergency lighting, beacon animation, warning banner and affected-rack highlighting |
| Floating AI icon looked static | It used a generic Bot icon with minimal feedback | Uses the centered VTAB logo, animated signal rings, live indicator and an AI COPILOT label |
| Copilot purpose was unclear | Drawer had limited context and no evidence-policy explanation | Added evidence-status chips, richer quick prompts and clearer evidence-aware language |
| Logo looked misaligned with a quirky right arrow | The prior SVG shield path was asymmetric and included an external arrow | Replaced it with a centered symmetrical shield/neural-circuit mark |

## Adaptive safety policy

Manual mode is the default and uses the exact operator-entered value. The adaptive calculation below applies only when Auto mode is explicitly selected for a temperature or humidity rule.

1. The user selects Manual or Auto in Settings and saves the sensor rule.
2. In Manual mode, the configured value is the active threshold and no baseline adjustment occurs.
3. In Auto mode, the configured value remains the minimum/fallback policy.
4. The platform collects up to 60 recent valid readings.
5. Before 8 readings, Auto remains in learning state and uses the configured fallback unchanged.
6. At 8 or more readings, the median becomes the normal operating baseline.
7. Effective temperature limit = maximum of configured base and baseline + 3°C, capped at 40°C.
8. Effective humidity limit = maximum of configured base and baseline + 5%, capped at 90%.
9. A reading at or above the hard ceiling is always critical.
10. Settings displays configured base, effective limit, median baseline, sample count and hard ceiling separately.

The median reduces the influence of one anomalous reading. This logic is transparent and deterministic; it is not a replacement for a professionally commissioned HVAC/BMS safety policy.

## Verification performed

- Backend API and domain suite: 29 passed.
- Independent simulator suite: 14 passed.
- Frontend runtime suite: 4 passed.
- Main dashboard optimized production build: passed.
- Simulator UI optimized production build: passed.
- Python compilation for backend, AI service and simulator: passed.
- The AI Operations regression test renders the actual governance component and fails if a referenced UI symbol is undefined.
- The adaptive threshold test verifies learning at 77% RH, an 82% effective limit and a critical alert at the 90% hard ceiling.

## Operator validation after startup

1. Clear prior test data from Administration.
2. Open Settings and observe the humidity policy as LEARNING / FIXED.
3. Publish 8–10 stable humidity readings from Test Lab.
4. Confirm the policy changes to ADAPTIVE and shows baseline/effective/ceiling evidence.
5. Open AI Operations and confirm diagnostics, predictive intelligence and governed actions render.
6. Open 3D Room and drag horizontally through a full rotation.
7. Trigger water, smoke or a hard-ceiling environmental value and confirm the whole room enters red emergency mode.
8. Toggle sun/moon mode and verify the selection survives refresh.
9. Open the AI COPILOT and ask “What needs attention?” to confirm live evidence is returned.


