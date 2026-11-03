# Diagnostic download

Open Settings → Devices & services → Hive EV, then the integration entry's three-dot menu → Download diagnostics. This explicitly requests technical data using the integration's normal session. Authentication may renew normally; a diagnostic does not start an interactive SMS flow or activate controls.

The component reads the established 6.5 node endpoint for monitored homes and returns bounded EV technical shapes. Known technical field names are preserved, unknown names are hashed, and only strict read/write metadata and the shared app capability vocabulary DSR/FREE_CHARGE/SECURE_CHARGE may pass through. These fields do not prove support for a command.

Account/device identifiers, names, credentials, raw readings, URL values, schedule contents and arbitrary nested values are excluded from the component result. Errors return fixed safe categories. Home Assistant adds its own standard envelope and filename outside this sanitizer, so review the downloaded JSON before sharing; the component result is in its data section.

There are no installer-settings requests, new background polls or charging writes in this diagnostic path. The owner's 3 November download succeeded. Its empty capability metadata is not a complete command catalogue and does not establish absence of server support. This release provides no Pause action or additional device/history features.

Do not submit tokens, `.storage`, full configuration files or unreviewed raw API replies as troubleshooting material. Use invented payloads in tests.
