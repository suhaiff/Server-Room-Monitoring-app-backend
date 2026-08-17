CREATE EXTENSION IF NOT EXISTS timescaledb;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
-- Application tables are created by SQLAlchemy from the exact 37-table model.
-- On backend startup telemetry_details is converted to a TimescaleDB hypertable.
