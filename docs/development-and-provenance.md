# Development and provenance

## AI disclosure

**This integration and its supporting documentation were developed using OpenAI Codex, with AI-generated implementation and tests.** Codex acted as project manager and delegated investigation, implementation and independent review to agents within the same development session. This disclosure does not imply endorsement by OpenAI, Hive, Centrica, Alfen or Home Assistant.

The human user supplied the problem, equipment details and constraints, ran local discovery tools using their own account, installed the monitoring integration and reported observed statuses. Their requirement was to retain the Hive app and existing charging schedule. Codex generated the investigative tooling, integration code, local tests and these documentation drafts. No human author name, maintainer identity or ownership claim is inferred from that collaboration.

If this work is proposed upstream, the pull request should disclose the same AI assistance, describe the human testing actually performed and preserve the limits in [testing.md](testing.md). The integration is not already accepted by Home Assistant or the existing Hive library. Any contributor must inspect the final diff and satisfy the destination project's current contribution and licensing requirements.

## Investigation method

1. Reviewed official Home Assistant Hive documentation and the existing Hive library. The legacy inventory did not expose the user's charger.
2. Examined public Alfen/OCPP alternatives. Replacing Hive's charger backend did not meet the user's requirement to retain Hive, so that route was not adopted.
3. Used Android USB debugging and ADB only to copy the installed official Hive Android application, version 15.07.1, for static inspection. USB debugging itself did not reveal an API. Its React Native/Hermes version 96 bytecode bundle was analysed using `hermes-dec`, alongside independent string inspection. This identified modern account-home/node discovery, versioned response formats and EVSE feature names. No intercepted password, private app database or MFA bypass was involved; this remains an undocumented app interface rather than an official developer API.
4. Built bounded local discovery tools. The human user authenticated locally and shared sanitized summaries, establishing that the account exposed a charging-station node and EVSE node, then confirming reported status and transaction activity through live API reads.
5. Implemented the monitoring integration and offline tests, reviewed failure handling and prepared manual installation instructions. The human user installed the integration. Detailed long-running validation remains outstanding.
6. Prepared a separately authorised, supervised control trial. Initial sign-in failures were isolated with read-only diagnostics. A later user-confirmed START request was not acknowledged; no charging change was observed and STOP was not sent.
7. Re-examined the exact UI and transport chain after that rejection. The agents identified an earlier resolver-tracing error: the trial used a Beekeeper host instead of the EV control host. The offline tests and initial AI review had not caught that error. The correction was independently checked against the source trace. The app's confirmation popup was also traced to its Charge Now handler rather than assumed to require a separate server confirmation.
8. The human user ran the corrected supervised trial: START and STOP were acknowledged, with reported Charging followed by Finishing and an inactive transaction. The compared saved tariff fields were unchanged. Reported power did not establish energy transfer. Following an unplug/reconnection instruction returned the charger to Scheduled in one instance.
9. Investigated the user's earlier expectation that manual app Stop returned to a ready/scheduled condition. Static review found no proved false-override cancellation command. A subsequent read-only watcher observed the user operate Hive: Scheduled → Charging with override true → FINISHING with transaction activity false, persisting for 90 seconds and matching Hive's display. This reproduced the corrected tool's end-session pattern. Earlier user-supplied charger history also showed automatic progression after Finishing without unplugging, while a later manual-app Stop prompted unplugging. The differing recovery conditions remain unresolved; neither universal reconnection nor universal automatic readiness is claimed.

Static analysis used public app code, not the user's private application database, saved login files or account traffic captures. A legacy inventory omission also does not establish that Hive lacks a charger API.

## Material for a public repository

The intended distribution is the custom integration source, synthetic tests and project documentation. **Do not include the original APK, split APKs, copyrighted app assets, extracted Hermes bundle or decompiled application files.** The static evidence supports implementation decisions; it is not a proposed redistribution of Hive's application.

Do not publish raw account replies, device/home identifiers, tokens, passwords, QR codes, authentication screenshots, private app data or local environment paths. Tests should use invented fixtures. Private account identifiers used internally for API requests and entity identity must not be copied into examples or logs.

The embedded application client key is shared application configuration, not a user's private token. Treat it separately from account credentials and document its purpose without representing it as an official developer API grant. Review redistribution and dependency licensing before a release; this draft does not establish legal clearance or choose a licence for other authors' code.

## Draft status

This standalone source repository was assembled locally at the user's request. It is not a published hosted repository, a submitted upstream pull request or confirmed public support. The testing record distinguishes observed command/state results from unverified energy transfer, sustained token renewal and overnight readiness. Update it as evidence changes; do not silently turn pending checks into verified claims.
