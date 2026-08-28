# Production URL configuration

The dashboard and simulator browser endpoints are configured once in the project-root `.env` file. Application source code does not contain localhost fallbacks for these endpoints.

Set these values before building the production images:

```dotenv
# Main dashboard -> backend API
VITE_API_URL=https://api.example.com/api/v1

# Main dashboard -> simulator application link
VITE_SIMULATOR_URL=https://simulator.example.com

# Simulator application -> simulator API
VITE_SIMULATOR_API_URL=https://simulator-api.example.com

# Browser origins allowed to call each API (comma-separated when needed)
CORS_ORIGINS=https://monitor.example.com
SIMULATOR_CORS_ORIGINS=https://simulator.example.com
```

Then rebuild the browser applications so Vite compiles the new public URLs into the static assets:

```text
docker compose build frontend simulator-ui
docker compose up -d
```

Changing an existing production `.env` without rebuilding these two images does not change an already-compiled browser bundle.
