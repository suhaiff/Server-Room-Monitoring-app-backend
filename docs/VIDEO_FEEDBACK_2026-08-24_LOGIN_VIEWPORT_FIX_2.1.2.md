# Login Viewport Bug Resolution — Version 2.1.2

Date: 24 August 2026
Video reviewed: `20260824-1156-27.2600868.mp4`

## Reported behavior

The login logo was abnormally large, branding escaped the login card, the form moved below the visible screen, and the user could not scroll to reach Sign in.

## Root cause

1. The SVG logo had no login-specific width or height, so the browser used its large intrinsic dimensions.
2. The login page inherited the global dashboard `main` overflow rule.
3. A later full-application viewport rule disabled document scrolling, but the login screen did not provide its own scroll container.
4. The original login form used a fixed 390 px width, which could overflow narrow browser windows.

## Implemented correction

- Added a dedicated `login-card` rather than depending on global form styling.
- Added a contained 52 × 52 px login logo, reduced to 43–46 px on short/mobile screens.
- Made the card `width: 100%` with a 420 px desktop maximum.
- Made the login screen a dedicated `100dvh` vertical scroll container.
- Used automatic vertical margins so the card is centered when space exists and remains reachable from the top when the viewport is short.
- Added compact-height rules for displays below 660 px.
- Added mobile spacing rules below 460 px.
- Preserved the current credentials, login endpoint and authentication flow.
- Added username/current-password autocomplete semantics and an accessible login error region.

## Verification

- Login viewport regression tests cover logo containment, responsive width, short-screen scrolling and field accessibility.
- All frontend tests pass.
- Frontend production compilation passes.
- Backend and simulator test suites remain part of the release verification.

## User test

After extracting the new archive, rebuild the frontend so Docker does not reuse the previous CSS image:

```powershell
docker compose down
docker compose build --no-cache frontend
docker compose up -d
```

Then open `http://localhost:5173` and perform a hard refresh with `Ctrl+F5`.