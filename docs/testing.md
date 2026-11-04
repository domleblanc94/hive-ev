# Testing and validation record

Updated 3 November 2026. The 0.2.0b2 baseline is recorded below; the selectable-cost 0.2.0b3 validation is recorded in its own section. The public custom component contains optional experimental controls; the separate upstream library/Core drafts remain monitoring-only. Raw owner diagnostics, screenshots and CSVs are not included in fixtures or packages.

## Automated release-candidate checks

- **56 offline tests passed:** 20 original monitoring/auth/flow/entity checks, 16 control checks, nine diagnostic privacy/read-only checks and 11 energy-helper checks. Home Assistant interfaces are stubbed; the declared Pyhive dependency is installed. Fixtures and credentials are invented.
- **21 genuine Home Assistant tests passed in 20.99 seconds:** Linux Python 3.14.10 with released `pyhive-integration==1.0.10`, loading the public source in pytest's temporary configuration directory. HTTP transport and token metadata are synthetic; no real account, Cognito or charger calls occur. See `tests/runtime/README.md` for the separate framework reproduction setup.
- The real-framework cases cover default-off loading/polling, options confirmation/reload, fresh command guards, one PUT per attempt, HTTP/timeout error disablement, opt-out races, token updates preserving the client, separate End binding, diagnostic loader discovery/redaction/error handling and bounds. Reported status is not optimistically changed after a command.
- Packaging, documentation-link, source-hash and excluded-file checks are recorded in [release validation](release-validation.md). Automated checks cannot prove actual device actuation, model compatibility or provider stability.

## Owner observations

| Observation | Evidence | Limit |
|---|---|---|
| Initial setup and monitoring | Owner installed the custom component and observed status/session changes with roughly minute refreshes | One account and Alfen NG910; not every lifecycle path |
| Overnight 30–31 October | 680 refreshes across about 11 hours 25 minutes; Scheduled → Charging → Completed → Paused; history shows 6,973–7,108 W and energy rising to 7,110 Wh, then 0 W at Completed | Hive-reported measurements, no independent meter/car comparison; duration 3,690 s comes from screenshot |
| Home Assistant restart | Owner reports updates resuming without another sign-in | Exact timing, logs and duplicate-entity comparison not supplied |
| Private precursor Charge Now, 3 November | Button press at 21:19:21 followed by Charging and 5,825 W, session active, duration 25 s and energy 22 Wh in the supplied screenshot | One supervised run of dev1, not the exact public beta artifact; raw HTTP status and independent meter result not supplied |
| Private precursor End session | Owner reports Finishing, 0 W and inactive session; Hive instructed unplugging | End/unlock confirmed by reported states; no Pause or same-plug restart established |
| Recovery | Owner reports reconnecting and returning to Scheduled | Exact saved-time/override-clearance comparison not supplied; later readiness is not guaranteed automatically |
| Dev2 diagnostics | Owner supplied a successful bounded technical diagnostic | Empty capability metadata does not establish supported or unsupported commands |

The beta retains the predecessor's command semantics, with public naming/version/User-Agent metadata changes and release documentation. The exact beta artifact has not been installed on the owner's hardware at preparation time.

## Development failures and earlier evidence

An initial control trial used an incorrectly traced host and its request was rejected. Independent source review corrected the resolver before the later acknowledged trial. This demonstrates why synthetic payload tests cannot establish a provider endpoint or physical outcome; see [provenance](development-and-provenance.md).

Earlier manual app observation also ended in persistent Finishing, matching End semantics. Another earlier history showed automatic Finishing → Available/Ready → Preparing → Scheduled progression without going outside. Both observations are retained; neither a universal unplug requirement nor universal automatic recovery is claimed. Earlier trials with zero/absent reported power do not establish actual energy delivery on those earlier runs.

## Remaining validation

- Exact beta installation/upgrade on the owner's system with enrollment inspected, and explicit identity/duplicate checks.
- Further normal overnight runs and longer-term renewal/expiry/reauthentication recovery. Continuous overnight reads do not identify a specific token-refresh event.
- Optional duration history and independent vehicle/meter comparison.
- Broader accounts/models/firmware and repeated supervised control trials before widening compatibility or control scope.
- Schedule/readiness checks after every end-session action; saved fields being unchanged alone does not prove readiness.

Do not add Pause or unattended automations to this beta on the basis of reported state names. Do not copy the private research, proprietary app, real account identifiers or raw responses into public tests.

## Separate upstream contribution

The Pyhive draft passed 1,124 tests with 100% coverage. The Core draft passed 30 real Hive tests, one separate actual-local-library contract test, scoped typing and 24 targeted integration checks. Those are separate records, not validation of this custom component. The upstream feature is still dormant with Core's released dependency pin until a compatible library release and reviewed dependency update exist; full bootstrap/repository checks remain outstanding. See [the contribution plan](upstream-contribution-plan.md).

## Native helper beta validation

The final 0.2.0b2 framework run passed 21 cases (the prior 16 plus five energy-helper cases) in 20.99 seconds. Actual entity-registry default disablement, enabling, energy/kWh/total-increasing metadata, accumulation independent of session resets, save/load through HA restore storage across a 600-second gap, invalid/failure/long-gap handling and duplicate prevention passed. Native branding separately passed one HTTP case in 1.36 seconds. These use synthetic telemetry, not real charger commands. Rendered Energy dashboard selection and Recorder statistics end-to-end have not been exercised; owner installation and comparison during a normal charge remain next steps.

## Current 0.2.0b3 selectable-cost validation

- **70 offline checks pass** (the prior 56 plus 14 cost/math/entity/options checks). Fixtures are invented and HA interfaces are stubbed.
- **35 actual Home Assistant runtime cases pass in 35.85 seconds** (the prior 21 plus 14 cost cases), using synthetic local price states and mocked Hive transport with declared Pyhive 1.0.10. No account, supplier or charger commands are sent to a real service.
- Cost coverage includes native options selector enrollment/removal, preserving unrelated and experimental options, currency/unit scaling and rejection, event-split intervals, negative credits, restore storage without downtime credit, unavailable-price recovery, currency separation and power freshness independent of rate events. The actual Recorder case verifies signed five-minute state/sum, hourly rollup and a daily query returning the expected net cost including negative-rate credits. This goes beyond sensor metadata; it does not exercise rendered cards or compare a supplier bill.
- The current install ZIP contains 39 whitelisted files, including 19 component files, with source-byte/privacy-marker/ZIP integrity checks. The prior native-brand test remains applicable because the PNG and delivery path are unchanged.
- No exact b3 owner installation or rendered daily-cost card is claimed. Compare estimates during a normal charge and tariff boundary before relying on them; unavailable observations can undercount. Daily views require Recorder and sufficient recorded statistics.

The native rate selector stores only a user-chosen local entity reference and currency in options. It contains no owner's EDF identifier and does not change saved Hive schedules or experimental command semantics. The standalone source/install/review artifacts are prepared locally; publication is still pending an actual project URL and owner review.

## Normal 0.2.0 release / HACS metadata

Prepared 4 November 2026 at the owner's request as a normal GitHub release. The project remains unofficial and charging controls retain their experimental labels and existing limits. Functional monitoring, cost/energy algorithms and command behavior are unchanged from the 0.2.0b3 implementation freeze; only version/User-Agent metadata, manifest codeowners, HACS metadata and documentation change. The prior 35 real-framework cases therefore remain evidence for that functional implementation, not a new owner's live installation. The 70 offline checks are rerun for this release.

HACS metadata and the integration manifest pass the actual HACS validation schemas (`HACS_MANIFEST_JSON_SCHEMA` and `INTEGRATION_MANIFEST_JSON_SCHEMA`) from official hacs/integration commit a15e87ec0d1c82e58f1ddbaf17669d3eaa261eb8. Source-folder layout checks pass: one custom_components/hive_ev integration, an actual owner, supported stable version, local brand and source downloads without ZIP-release mode. The conservative declared HA Core minimum is 2026.10.4. Root hacs.json is included in the source/release tag; HACS installs the integration subfolder. No default-catalog inclusion, upstream brand submission or end-to-end owner HACS installation is claimed.

The README and dedicated HACS guide explain adding the custom repository as Integration, choosing normal 0.2.0, restarting HA, reusing existing entries and moving from manual installation. The guide distinguishes optional future betas and keeps manual ZIP installation available. The new commit uses verified Codex author identity for agent-authored work, without rewriting published commits or giving the account collaborator access.
