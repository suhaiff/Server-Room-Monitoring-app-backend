# Placeholders and external configuration

No external credential is embedded. Configure these for production:

- Supabase or managed PostgreSQL connection URL and optional Supabase Auth/JWT integration.
- TimescaleDB availability/extension permissions.
- Redis credentials and TLS.
- MinIO or AWS S3 endpoint, access keys, bucket, encryption and lifecycle policy.
- SMTP/SendGrid, Teams webhook, Jira and ServiceNow URLs/credentials.
- Optional OpenAI/Azure OpenAI key for enhanced explanations (the local deterministic explanation works without it).
- MQTT per-device credentials, ACLs and TLS certificates.
- Production DNS, certificates, WAF/rate limiting, Sentry and backup destinations.
- Real Arduino firmware/calibration values and device credential provisioning.

The local defaults and simulator are intentionally non-production.

