# VTAB Sentinel — Third Video Review (V7)

This release implements the focused usability feedback recorded on 14 August 2026 at 09:03.

## Findings, root causes and completed updates

| # | Feedback | Root cause | Update |
|---|---|---|---|
| 1 | A single ticket was positioned on the left and did not use the available Overview space | Ticket cards always used a two-column grid | A single active ticket now expands across the full panel; the healthy empty state is centered and more informative |
| 2 | Overview needed a direct route to the complete incident page | The ticket panel exposed only its close action | Added **Open incident center** and **View incident history** actions |
| 3 | Tickets needed database-backed history to show when and how each action happened | `incident_details` recorded manual updates but not initial threshold creation or automatic normalization, and the API did not return the records | Threshold creation, automatic resolution and operator actions are stored in `incident_details`; `/incidents` now returns a chronological history displayed inside every ticket |
| 4 | Voice announcements stopped after one delivery | Event deduplication intentionally prevented the same incident from being queued twice | Active-ticket reminders now repeat every 10 seconds by default until the ticket is resolved or closed |
| 5 | Voice looping needed to be configurable | Voice behavior only had a global enable/mute flag | Added reminder options: off, 10, 30 or 60 seconds |
| 6 | Operators needed to choose what is visible on Overview and Reports | No application preference model existed | Added a dedicated **Settings** page with persistent Overview and Report section toggles |
| 7 | Test Lab pipeline indicators were misaligned and less readable than AI Operations | The process strip used decorative status dots attached to plain labels | Rebuilt it as four aligned pipeline cards with explicit states, animated connectors and clear completed/active/waiting/error presentation |

## Settings provided

- Voice reminder interval.
- Show/hide Overview ticket panel.
- Show/hide Overview temperature trend.
- Show/hide Overview alert feed.
- Show/hide Report severity chart.
- Show/hide Report service-health panel.
- Show/hide Report operational findings.

Preferences are stored in the browser and apply immediately.

## Verification

- Backend API and ticket-history acceptance tests: **10 passed**.
- Simulator and six scenario tests: **9 passed**.
- AI model tests: **5 passed**.
- Dashboard production build: **passed**.
- Test Lab production build: **passed**.
- Corrected Test Lab pipeline rendered without JavaScript errors and was visually inspected.

## Upgrade command

Preserve the current database and rebuild only changed services:

```powershell
docker compose up -d --build backend frontend simulator-ui
```

Then press `Ctrl+F5` at `http://localhost:5173` and `http://localhost:5174`.

