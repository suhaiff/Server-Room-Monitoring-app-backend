# VTAB Sentinel 2.3.0 — Final Video Sign-off Release

Date: 2026-08-24

## Final feedback checklist

| # | Video feedback | Final implementation |
|---|---|---|
| 1 | Overview redesign did not match the preferred earlier flow | Restored the operational order: current temperature, active alerts, open tickets, device/telemetry context, live temperature trend, then compact latest-alert and today's-ticket insights |
| 2 | Latest alert and tickets opened today should appear as small cards after the live trend | Added a compact responsive two-card insight row containing the latest alert lifecycle and today's opened/closed/critical ticket counts |
| 3 | Reports did not provide superior management information | Added a seven-day opened-versus-closed ticket trend, closure rate, AI analysis trend, completion rate, anomalies, high-risk results and processing backlog |
| 4 | Settings felt limited and needed a better design | Rebuilt Operator Experience around a dashboard composer, report composition, voice preferences and clear automatic-layout behavior |
| 5 | Overview modules should be individually selectable | Added 12 checkbox cards. Every choice persists locally and the Overview uses auto-fit grids to re-space selected content immediately |
| 6 | AI bot still looked like a double square and needed a rounded structure | Replaced both outer and inner geometry with centered concentric circles, orbit rings, a circular status light and an optically centered bot icon |
| 7 | Copilot needed a reset/new workflow option | Added New chat, which clears the conversation ID, messages, draft and active workflow while keeping the drawer open |
| 8 | Floating Copilot control was not centered/aligned correctly | Unified the lower-right inset, centered all bot layers using flex/grid alignment, and aligned the drawer to the same right edge |
| 9 | White theme was flat, static and missing the depth of dark mode | Removed the previous light block and rebuilt light mode with layered gradients, highlighted card surfaces, readable operational colors, shadows, state-aware panels, dimensional controls, charts, tables, tickets, Settings, Reports and Copilot coverage |

## Overview composition choices

Operators can show or hide:

- Climate safety banner
- Current temperature card
- Active-alert card
- Open-ticket card
- Device card
- Telemetry card
- Live temperature trend
- Latest alert insight
- Today's ticket activity
- Expanded hardware detail
- Expanded ticket posture
- AI pipeline summary

Hidden modules continue collecting data; presentation choices do not change ingestion, AI analysis or alert processing.

## Report evidence

The Reports page now includes both management and engineering evidence:

- Seven-day ticket opening and verified-closure trend
- Ticket closure rate
- AI run volume trend
- AI completion rate
- Detected anomalies
- High-risk analysis count
- AI processing backlog
- Alert severity distribution
- Live dependency health
- Decision-ready findings

## Verification

- Frontend acceptance tests include exact layout order, module toggles, report trends, circular Copilot geometry, New chat and dimensional light-theme checks.
- Backend, simulator and production-build results are recorded in the release handoff.

## Upgrade and run

```powershell
docker compose down
docker compose build --no-cache frontend backend simulator-ui
docker compose up -d
```

Open http://localhost:5173 and press Ctrl+F5 once to discard the previous cached bundle.