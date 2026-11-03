# Testing and validation record

Updated 3 November 2026 for beta candidate 0.2.0b2. The public custom component contains optional experimental controls; the separate upstream library/Core drafts remain monitoring-only. Raw owner diagnostics, screenshots and CSVs are not included in fixtures or packages.

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
