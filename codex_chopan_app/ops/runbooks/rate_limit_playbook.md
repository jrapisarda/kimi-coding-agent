# Rate Limit Playbook

- Monitor `429` responses emitted by the API gateway.
- Increase bucket size in Redis or adjust configuration in `config/celery.toml` when necessary.
- Notify partner services of temporary degradation.
- Capture metrics snapshots before and after tuning for audit trails.
