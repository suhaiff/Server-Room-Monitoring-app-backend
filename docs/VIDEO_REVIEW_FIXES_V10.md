# Sixth Recorded Review: Findings, Root Causes and V10 Corrections

## Accepted in the recording

- Centered no-ticket dashboard state
- Settings CSV export
- Unified Hardware and Software simulator tabs
- Separate named AI model failure tests
- Model-specific fault visibility in AI Operations

## Remaining findings

| Finding | Root cause | V10 correction |
|---|---|---|
| Explanation stage remained healthy when Risk stage failed | V9 overlaid only the directly selected fault and treated all other AI nodes independently | AI status now applies the declared linear stage order and marks every dependent downstream stage `blocked` |
| Pipeline did not explain why a downstream node stopped | The UI supported only healthy and error visual states | Added a distinct amber **HELD** state, pause icon, stopped connector and “Blocked by [model]” explanation |
| Node count incorrectly treated blocked nodes as operational | The count excluded only `error` | Operational count now includes only `ready` and `healthy` states |
| Event stream omitted dependency holds | Only the directly failed model produced an error event | Every held downstream stage produces a structured `pipeline_blocked` warning with its upstream blocker |
| Internal scrollbars used the browser default appearance | Scrollable panels had overflow rules but no application scrollbar theme | Added thin cyan/dark scrollbars to event streams, tables, pipeline panels, code evidence and simulator content |

## Declared AI dependency order

`Baseline → Anomaly Detection → Trend Forecast → Risk Engine → Explanation Engine`

The failure rule is deterministic: the selected stage becomes **ERROR** and all
stages after the earliest failed stage become **HELD**. Earlier stages retain
their actual runtime status. Recovery removes both the direct error and its
derived downstream holds on the next 2.5-second AI Operations refresh.

## Acceptance example: Risk Engine

1. Open `http://localhost:5174`.
2. Select **Software / AI Lab → AI risk engine → Simulate failure**.
3. Open `http://localhost:5173` and select **AI Operations**.
4. Confirm stages 1–3 are healthy, stage 4 is red/error and stage 5 is amber/held.
5. Confirm stage 5 says **Blocked by Risk engine**.
6. Confirm the event stream contains both `simulated_model_failure` and `pipeline_blocked`.
7. Simulate recovery and confirm all nodes return to operational status while the ticket remains available for operator closure.
