# Fourth Video Review Resolution — Version 2.1.1

Date: 24 August 2026

This release addresses every item demonstrated in `20260824-1111-54.5302473.mp4`. Existing working voice intelligence, pagination, reports, device handling, and Manual/Auto threshold behavior were preserved.

## Feedback-to-fix record

| Video feedback | Root cause | Implemented correction | Verification |
|---|---|---|---|
| 3D room was still dark and visually incomplete | Low scene exposure and a display-style shell did not read as a complete room | Rebuilt the WebGL room with full floor, ceiling, back/side walls, front glass, physical materials, contact shadows, four working luminaires, stronger ambient/directional lighting, ACES tone mapping, and emergency lighting | Production build and source acceptance test |
| Door appeared on the front and not in a proper wall | Door and wall geometry were not coordinated | Door now starts on the right side wall inside a complete doorway opening; access camera preset points to it | Source acceptance test |
| Room layout could not be customized | All asset positions were fixed in code | Added **Edit room layout**. Select any rack, door, light, HVAC or sensor; adjust left/right, front/back and rotation; configuration auto-saves in the browser; Reset restores the reference layout | Source acceptance test |
| Copilot was too large and duplicated its identity | Separate label, floating control, and drawer avatar repeated the same bot | Reduced the control to 46 px, removed the external label and drawer avatar, and integrated the close indicator into the same bot control | Source acceptance test |
| Overview climate block was unclear | It showed status without explaining operating policy or headroom | Replaced it with live temperature/humidity, Manual/Auto mode, active limit, remaining safety margin, and direct Settings guidance | Source acceptance test |
| Predictive model information was too small | Compact card typography was designed for dense display | Enlarged cards, values, supporting evidence and governed-action text; cards reflow for smaller displays | Source acceptance test |
| Five AI models were hidden in a separate tab | Model pipeline was implemented as a selectable view | The full five-stage pipeline is now always visible at the top of AI Operations; remaining tabs are System health, Predictive intelligence and Execution evidence | Source acceptance test |
| Sidebar health panel covered Administration | Sidebar mixed a grid layout, status tile and navigation in the same constrained region | Removed the redundant health tile, introduced an independently scrolling navigation region, and kept Sign out fixed below it | Source acceptance test |

## Using the room layout editor

1. Open **Devices**, then open the server-room 3D digital twin.
2. Select **Edit room layout**.
3. Click an asset in the 3D room or choose it from **Selected asset**.
4. Adjust **Left / right**, **Front / back**, and **Rotation**.
5. Select **Finish**. The layout is already saved in this browser.
6. Use **Reset room** to return to the default enclosed side-door design.

The saved layout uses browser local storage (`vtab.room-layout.v2`). This deliberately avoids changing the organization-wide database while the editor is being evaluated. A future release can promote approved layouts to PostgreSQL for shared multi-user room plans.

## Validation completed

- Frontend production compilation
- Frontend regression and video-acceptance tests
- Backend API regression tests
- Simulator API regression tests
- Simulator frontend production compilation
- Packaged-archive content and forbidden-file verification

Docker runtime validation must still be executed on a machine with Docker Desktop or Docker Engine available; the automated execution environment used for this release does not expose Docker.