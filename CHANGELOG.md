# Changelog

## 0.2.0 — community release, 4 November 2026

- Publish as a normal GitHub release, retaining unofficial project status and experimental charging-control labels.
- Add HACS custom-repository metadata, a conservative HA Core 2026.10.4 minimum and clear first-install/manual-upgrade instructions.
- Credit the verified OpenAI Codex GitHub identity for this agent-authored HACS/documentation update. Published history is not rewritten.
- Retain the monitoring, optional energy helper and selectable-rate cost helper from 0.2.0b3. Charging/helper behavior and saved Hive schedules are unchanged.

## 0.2.0b3 — selectable electricity-rate cost helper

Prepared locally, not published.

- Add optional charging cost estimation from a user-selected local electricity-rate sensor, independent of supplier.
- Use current rates over observed charging intervals, preserve currency-specific totals and support negative-rate credits.
- Document daily, weekly and monthly cost using calendar-change Statistic cards.
- Keep charging commands and saved Hive schedules unchanged.

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
