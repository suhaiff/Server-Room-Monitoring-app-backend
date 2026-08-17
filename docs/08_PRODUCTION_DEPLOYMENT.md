# Production deployment checklist

- Replace all local passwords and JWT secret through a secrets manager.
- Enable HTTPS, MQTT TLS/mTLS, broker ACLs and firewall rules; disable anonymous MQTT.
- Deploy managed PostgreSQL/TimescaleDB or Supabase with PITR, replicas and tested restore procedures.
- Enable Supabase RLS if PostgREST is exposed; verify organization isolation.
- Use managed Redis with authentication/TLS and S3 with encryption, retention and lifecycle policies.
- Configure Jira, ServiceNow, Teams and SMTP credentials; use retry queues and idempotency keys.
- Pin container image digests, scan dependencies/images and run migrations as a controlled job.
- Configure centralized logs, Prometheus/Grafana alerts, Sentry, uptime probes and on-call escalation.
- Complete performance, security, UAT, backup/restore and rollback tests before blue/green or rolling deployment.

