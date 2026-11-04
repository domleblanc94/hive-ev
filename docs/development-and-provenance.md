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
5. Implemented the monitoring integration and offline tests, reviewed failure handling and prepared manual installation instructions. The human user installed the integration. The owner subsequently supplied an overnight export and sensor screenshot; the results and remaining limits are recorded below.
6. Prepared a separately authorised, supervised control trial. Initial sign-in failures were isolated with read-only diagnostics. A later user-confirmed START request was not acknowledged; no charging change was observed and STOP was not sent.
7. Re-examined the exact UI and transport chain after that rejection. The agents identified an earlier resolver-tracing error: the trial used a Beekeeper host instead of the EV control host. The offline tests and initial AI review had not caught that error. The correction was independently checked against the source trace. The app's confirmation popup was also traced to its Charge Now handler rather than assumed to require a separate server confirmation.
8. The human user ran the corrected supervised trial: START and STOP were acknowledged, with reported Charging followed by Finishing and an inactive transaction. The compared saved tariff fields were unchanged. Reported power did not establish energy transfer. Following an unplug/reconnection instruction returned the charger to Scheduled in one instance.
9. Investigated the user's earlier expectation that manual app Stop returned to a ready/scheduled condition. Static review found no proved false-override cancellation command. A subsequent read-only watcher observed the user operate Hive: Scheduled → Charging with override true → FINISHING with transaction activity false, persisting for 90 seconds and matching Hive's display. This reproduced the corrected tool's end-session pattern. Earlier user-supplied charger history also showed automatic progression after Finishing without unplugging, while a later manual-app Stop prompted unplugging. The differing recovery conditions remain unresolved; neither universal reconnection nor universal automatic readiness is claimed.

10. Reviewed the owner-supplied overnight activity export and later sensor card on 31 October 2026. The standalone integration continued monitoring through Scheduled → Charging → Completed, with 680 successful-refresh entries and reported session energy 7.11 kWh, duration 3,690 seconds, and power 0 W while Paused. The measurements are Hive reports, not an independent meter verification; later History exports additionally confirmed 60 positive power readings at 6,973–7,108 W, energy rising to 7,110 Wh, and 0 W at the Completed timestamp. Independent meter comparison and detailed restart checks remain outstanding. The owner subsequently reported restarting Home Assistant and updates resuming without another sign-in; exact timing and registry checks were not supplied. See [overnight results](overnight-results.md).

Static analysis used public app code, not the user's private application database, saved login files or account traffic captures. A legacy inventory omission also does not establish that Hive lacks a charger API.

## Beta control promotion, 3 November 2026

The owner installed private precursor dev1 and supervised Charge Now (reported 5,825 W), End (Finishing/0 W/inactive), and reconnection to Scheduled. The owner also supplied a dev2 diagnostic. At the owner's request, the tested monitoring, optional controls and diagnostic modules were promoted into public beta candidate 0.2.0b1. Pause work was deferred; no Pause action or detailed speculative feature research was promoted. The beta control scope stays deliberately narrow and disabled on a new installation. Existing private options survive upgrades.

The public source passed 45 offline checks and 16 tests inside the real Home Assistant framework with synthetic transport. Neither those checks nor the predecessor's owner observations establish broad compatibility or unattended control. The exact public artifact is a release candidate, not a reported live installation. See [release validation](release-validation.md).

## Material for a public repository

The intended distribution is the custom integration source, synthetic tests and project documentation. **Do not include the original APK, split APKs, copyrighted app assets, extracted Hermes bundle or decompiled application files.** The static evidence supports implementation decisions; it is not a proposed redistribution of Hive's application.

Do not publish raw account replies, device/home identifiers, tokens, passwords, QR codes, authentication screenshots, private app data or local environment paths. Tests should use invented fixtures. Private account identifiers used internally for API requests and entity identity must not be copied into examples or logs.

The embedded application client key is shared application configuration, not a user's private token. Treat it separately from account credentials and document its purpose without representing it as an official developer API grant. Review redistribution and dependency licensing before a release; this draft does not establish legal clearance or choose a licence for other authors' code.

## Draft status

This standalone beta source repository was assembled locally at the user's request. It is not a published hosted repository, a submitted upstream pull request or confirmed public support. The testing record distinguishes earlier command/state results from the later overnight charging evidence, including Hive-reported session energy. Specific token renewal events, detailed restart/registry checks and reliable readiness after Stop remain unverified; basic restart recovery is now user-reported. Update it as evidence changes; do not silently turn pending checks into verified claims.

## Project artwork

At the owner's request, the built-in image generator produced an original orange-and-white UNOFFICIAL HIVE EV project mark. The final PNG is copied unchanged into the custom component's native brand directory and used in the README. It is not the official Hive artwork or an endorsement. Native Home Assistant delivery was checked separately without contacting Hive. The original generation prompt and design output remain in the local design workspace.

## Native energy helper

For 0.2.0b2 the owner requested a sensor supplied by Hive EV for the Energy dashboard, explicitly identified as a helper. Codex agents implemented and independently framework-tested a default-disabled, persistent kWh estimate from reported power. It uses no private EDF entity, price dependency or additional charger command. Supplier-specific optional cost configuration stays ignored locally; the public cost example uses generic placeholders.

## Selectable cost helper

For 0.2.0b3 the owner requested provider-neutral native cost tracking from a selected electricity-rate sensor and daily spend views. Codex agents implemented the optional configuration and independently tested it against synthetic Home Assistant entities. Public code contains no owner EDF entity. Daily/calendar views use standard HA statistics over the monetary total rather than resetting it. Detailed evidence and limits are recorded in testing and release validation.

## Verified Codex commit attribution

On 4 November 2026 the owner asked for GitHub contributor credit. The [Codex profile](https://github.com/codex) identifies OpenAI and links its product page. OpenAI's [published attribution implementation](https://github.com/openai/codex/blob/e4a3612f11ba68ac82111ea986801a3337554083/codex-rs/core/src/commit_attribution.rs) specifies `Codex <noreply@openai.com>`. GitHub API commit-author lookup links that email to @codex. The new HACS/docs commit uses that verified author identity and the owner's normal committer identity; existing published commits and releases are retained. This credits agent-authored work without granting a GitHub collaborator access or implying OpenAI endorses/maintains Hive EV. Sidebar contributor indexing may take time.
