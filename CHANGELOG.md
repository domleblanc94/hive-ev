# Changelog

## 0.2.0b2 — Energy dashboard helper, prepared 3 November 2026

Not yet published.

- Add an optional, disabled-by-default Energy dashboard helper with energy/total-increasing metadata in kWh, estimated from reported charging power.
- Restore its cumulative total across restarts, independently of session counters; skip missing observations and long gaps instead of backfilling.
- Supply a provider-neutral optional GBP cost-package example. No electricity supplier or personal price entity is configured in the component.
- Keep Charge Now and End session semantics unchanged.

## 0.2.0b1 — release candidate prepared 3 November 2026

Not yet published. This is a beta with optional supervised controls.

- Bundle the orange/white unofficial project icon through Home Assistant local branding and document Energy dashboard helper setup.
- Retain reported status, session activity, optional power/session measurements, and 60-second monitoring.
- Add default-off experimental Charge Now and End charging session buttons, explicitly limited to a single owner-confirmed Alfen and normal Custom/Tariff sessions.
- Check fresh state, serialize commands, limit attempts, avoid write retries, and disable controls after uncertain delivery.
- Add an explicit redacted diagnostic download using existing authenticated node reads.
- Document overnight energy/power evidence, owner-operated control trials, upgrade/rollback, limitations and Codex attribution.
- Include no Pause/Resume, schedule editing, extra device categories, historical-data retrieval, or automatic control automations.

## 0.1.0 — local monitoring prototype

Prepared locally in October 2026; no public release is asserted. Introduced read-only Hive EV discovery, normal owner sign-in/MFA, token renewal, and reported monitoring entities.
