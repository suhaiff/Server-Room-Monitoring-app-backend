# Database model

The planner defines 37 logical tables with UUID primary keys and only 1:1 or 1:N relationships. Its centralized header/detail slide names 32 tables, while the multilayer slide calls for additional operational/configuration tables and labels the total as 37. `backend/app/models.py` reconciles both views and implements exactly 37:

- 12 dimensions: organization, site, room, device, sensor, user, role, event type, source system, status, severity and time.
- 1 central `core_events` single source of truth.
- 2 raw data, 2 telemetry, 5 AI/ML, 2 alert, 2 incident, 2 notification, 2 integration and 2 audit tables.
- 5 multilayer operational/configuration tables: device credentials, sensor calibrations, device health, threshold rules and system configurations.

Every functional module uses a header-to-details relationship. Core event boolean fields are indicators, not foreign-key relationships. Timestamps are UTC and foreign keys are indexed. `telemetry_details` becomes a TimescaleDB hypertable automatically on PostgreSQL startup.

Supabase can use the same PostgreSQL schema. A reference RLS policy is provided; production teams must expand it to all tenant-owned tables and match JWT claims from their chosen Supabase Auth flow.
