# Testing and validation record

This record separates local automated checks, human observations and remaining work. The corrected trial produced acknowledged commands and charging/end-session state changes. A later read-only observation of manual Hive app operation reproduced the same Finishing outcome. The later 30–31 October overnight run supports scheduled charging with Hive reporting 7.11 kWh; it does not retroactively verify the separate control trials or reliable recovery after Stop. See [overnight results](overnight-results.md).

| Area | Evidence | Limit |
|---|---|---|
| Modern cloud discovery | Human-ran authenticated local reads found exact charging-station and EVSE node types | One Hive account and Alfen NG910; no broad model validation |
| Reported status | Live read returned EVSE `displayState.reportedValue: AVAILABLE` and `transactionActive.reportedValue: false` | Available does not prove unplugged; session inactivity does not prove charger availability under every schedule |
| Hive interface | Human user reported Scheduled in the Hive app | This is a user observation, not an automated end-to-end test |
| Monitoring installation | User installed the integration and supplied a Home Assistant log showing roughly minute-by-minute refreshes, Scheduled → Charging → Ready status changes, and session activity switching on/off | This demonstrates loading and initial monitoring on the user's system, not every entity, restart path or renewal cycle |
| Integration logic | 20 offline integration checks passed | Home Assistant interfaces are stubbed; not a full Home Assistant runtime test |
| Trial logic and diagnostics | 23 offline checks passed for corrected trial v2, including an independently specified expected write host, read-only enforcement, HTTP rejection diagnostics, bounded SMS error-chain inspection and control guards | No live start/stop outcome established by those tests |
| First trial launch | User reported failure after the SMS code and before any action confirmation; a subsequent read-only diagnostic isolated the rejection to SMS verification (`signin_mfa`, `invalid_mfa`) | No charging commands were sent. The library groups multiple verification failures under this category, so the underlying rejection reason is not yet established |
| First live START attempt | User explicitly confirmed START; the request returned a non-success HTTP response. Follow-up reads remained Scheduled, 0 W, tariff mode and override false; compared tariff schedule values were unchanged. STOP was not sent | The original tool omitted the rejected HTTP status. No physical start/stop was confirmed, and overnight readiness still requires a separate check |
| Control-route investigation | Independent static review found that the trial incorrectly used the Beekeeper base URL; the actual EV UI route resolves to `https://api-prod.bgchprod.info` | This was an implementation and review error; it was corrected before the following v2 trial |
| Corrected v2 START | HTTP acknowledgement, override changed to true, and status advanced from Scheduled through a waiting state to Charging; the user also saw Charging in Hive | Reported power remained 0 W, so actual energy delivery was not established |
| Corrected v2 STOP | HTTP acknowledgement; status changed from Charging to Finishing and `transactionActive` became false. Compared tariff schedule fields remained unchanged | Override became absent, not confirmed false. This ended the session; it did not establish a pause/resume operation or overnight readiness |
| Manual Hive app operation under read-only observation | User-operated Charge Now changed Scheduled → Charging with override true. The user then pressed Stop in Hive: status became FINISHING and `transactionActive` was false, persisting throughout the 90-second observation; Hive also displayed Finishing. Compared saved tariff values were unchanged | This reproduces the corrected tool's end-session pattern. Power was reported as zero and later missing, so physical energy transfer was not proved. It does not establish a separate cancel-override command |
| Earlier automatic recovery reported by the user | The user supplied charger-history evidence of Finishing → Available → Preparing → SuspendedEVSE at 0 A and said they had not gone outside or unplugged | Automatic progression occurred in that earlier instance. Its cause and conditions remain unresolved; it does not establish readiness or restart behaviour after every Stop |
| Recovery after v2 STOP | User followed Hive's unplug instruction, disconnected both cable ends and reconnected; Hive returned to Scheduled | This verifies recovery after reconnection on one run, not a requirement to unplug after every Stop or proof of overnight charging. A later manual-app Stop also led to an unplug prompt |
| Overnight monitoring, 30–31 October 2026 | 680 refresh entries across approximately 11 hours 25 minutes; Scheduled → Waiting to start → Charging → Completed → Paused. Later screenshot shows 7,110 Wh, 3,690 seconds and 0 W while Paused; optional power, energy and duration sensors are now visible | One standalone installation; no active-charge power history or independent meter comparison. Continued authenticated access observed, but individual renewal events and restart recovery not exercised by this export. Upstream drafts were not installed |
| Home Assistant restart, reported 31 October 2026 | Owner reports that Home Assistant was restarted and updates resumed without another sign-in | User-reported outcome; no exact restart time, recovery logs or duplicate-entity/registry comparison supplied |

## Automated coverage

The integration checks exercise API response handling, reported-only parsing, missing/invalid telemetry, authentication and renewal decisions, SMS/setup flow, explicit trusted-device consent, coordinator failure handling and entities. Entity tests cover unknown readings, unavailable state after failures or node removal, stable identities, session resets and optional telemetry appearing after an idle installation.

The supervised-trial checks use synthetic responses to exercise command gating and bounded command construction. They cannot show that the charger obeys a request, that the car draws power, or that an HTTP success represents completed physical action.

The local test environment uses minimal Home Assistant stubs. The implementation was reviewed against Home Assistant 2026.10.4 interfaces; no claim is made that these tests load the integration inside that full runtime. Test counts are the recorded development-stage results, not a promise that every future checkout has the same tests.

## Additional upstream checks, 31 October 2026

Additional local validation on 31 October 2026: targeted Hive hassfest completed all 24 plugin checks with zero invalid integrations. A separate real-framework compatibility test passed using an actual locally built, unpublished Pyhive 2.0.0b4 wheel: real Hive construction/startSession, legacy discovery, EV requests/parser/model, and Core setup/entity updates/unload were exercised with synthetic HTTP responses only. No Hive implementation classes or methods were mocked. It checked reported-only readings, optional measurements appearing later, EV failure availability and GET-only device requests. This is one additional contract check, separate from the existing 30 Core tests; it made no account calls, did not change the manifest pin and does not establish live deployment of the upstream draft.

## Remaining validation

Separate upstream drafts have also been validated: the full Pyhive suite passed 1,124 tests with 100% coverage, and all 30 Core Hive tests passed on Linux Python 3.14.10 using genuine Home Assistant fixtures. These are separate from the standalone integration's 20 offline tests. The new library and Core drafts have not been live-tested on the owner's account. Core's full development bootstrap and repository-wide checks remain incomplete, and a published compatible library release/dependency upgrade is still required. See [the contribution plan](upstream-contribution-plan.md).

- Detailed restart/lifecycle checks, including entity identity and duplicates. The owner now reports a Home Assistant restart with updates resuming without another sign-in; exact recovery time and logs were not supplied.
- Unattended token renewal over a sustained run, expiry/rejection recovery and interactive reauthentication when required.
- Active-charge power, energy and duration histories and comparison with Hive/car readings. All three optional sensors are now visible; the later screenshot reports 7.11 kWh, 3,690 seconds and paused power 0 W. Nonzero active power has not yet been recorded in supplied evidence.
- Comparison of reported status with Hive/car observations across scheduled, charging, paused, completed and offline states.
- Physical charging confirmation during a supervised session, plus a final check that the charger is ready for the next scheduled session; command acknowledgements and reported state transitions have been observed.
- Further overnight scheduled runs for repeatability; one overnight run is now documented. Restart-after-stop without unplugging remains unresolved and separate from monitoring validation.
- Additional account/device variants and response changes before any wider compatibility claim.

For an almost-full battery, failure to draw power may reflect the vehicle declining charge. An active transaction is insufficient evidence of successful physical charging. Report accepted request, reported state change and observed power delivery as separate outcomes.

The expectation that Stop always returns Ready or Scheduled without reconnection is unverified. Earlier automatic progression and later persistent Finishing are both part of the record. Static review has not proved a `transactionOverridden: false` cancellation command, and the monitoring integration continues to expose no controls.

See [next steps](next-steps.md) for the ordered monitoring and contribution work.

## Reproducibility and privacy

Run tests with synthetic fixtures only. Keep account authentication local, suppress raw responses and share only bounded technical summaries. Do not put live device IDs, home IDs, tokens, passwords or authentication screenshots into fixtures, issue reports or CI logs. Do not upload the inspected APK or decompiled app to CI.

Before updating this record, retain the distinction between a successful cloud read, a successful Home Assistant installation and a verified physical charging action. Record failures and unresolved results explicitly.

## Final focused checks, 31 October 2026

The final post-annotation rerun passed all 30 Core Hive tests in 19.62 seconds and the separate actual-library contract test in 1.90 seconds. Scoped mypy passed all 13 Hive source files using `--follow-imports=silent`; this is not a repository-wide typing pass. Required `typing.override` decorators were added to five new overridden methods, without changing runtime behaviour. Hive hassfest was rerun with all 24 plugin checks passing and zero invalid integrations. The local unpublished wheel was built with Python 3.14; the manifest dependency remains unchanged. Authentication in the contract check starts from invented unexpired metadata; no Cognito login or renewal is exercised.
