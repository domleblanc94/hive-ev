# Release candidate validation

Prepared 3 November 2026. The 0.2.0b2 baseline is retained below; 0.2.0b3 cost-helper checks are recorded separately. The public beta source includes monitoring, two default-off experimental manual controls and explicit diagnostics. Publication target configured on 4 November 2026: https://github.com/domleblanc94/hive-ev.

## Automated checks

- Public source promotion: 56 offline tests passed, including 20 original monitoring checks, 16 control checks, nine diagnostic privacy/read-only checks and 11 energy-helper checks. These use Home Assistant stubs and invented fixtures.
- The public beta passed **21 genuine Home Assistant runtime cases in 20.99 seconds** on Linux Python 3.14.10 with the declared Pyhive 1.0.10 dependency. The normal loader and component hooks are real; HTTP responses and existing token metadata are synthetic. No real account, Cognito or charger calls were made. `tests/runtime/` contains reproduction instructions and the harness.
- The 37-file installation package passed independent whitelist, source-byte, private-key/JWT-marker and ZIP-integrity checks. Relative Markdown links passed across 18 public documents. The final archive is rebuilt after documentation freeze.
- Candidate public files were reviewed for excluded private research/data, and the frozen component/runtime-harness hashes match the actual-framework run. No original app material, owner CSV/JSON/screenshots or private research is included.
- The prepared GitHub Actions YAML parsed with the expected events and read-only permissions. It runs offline checks/build/package validation and retains a review artifact; no hosted execution or automatic release is claimed.

See testing.md for the distinction between synthetic framework checks, owner-reported hardware evidence and remaining requirements. The separate Core/library contribution tests do not validate this custom component by themselves.

## Publication status

On 4 November 2026 the owner created the public domleblanc94/hive-ev repository and authorized publication. Manifest documentation and issue links now point there. Prior local runtime records describe pre-publication source; the publication change updates manifest URLs and documentation, without changing charging or helper behavior. Hosted CI is reported separately from those local checks. No HACS support, maintainer acceptance or human code-review declaration is asserted.

The exact beta candidate has not been installed on the owner's live system. Its predecessor's reported hardware results and the synthetic public-code tests are different evidence. The separate Core/library contribution remains monitoring-only and has additional dependency/repository gates.

## Logo and energy-guide addition

The original generated orange/white logo is bundled unchanged as brand/icon.png and referenced by the README. One additional narrow test of the real Home Assistant Brands HTTP API passed in 1.47 seconds: icon, logo, dark and high-resolution fallbacks returned the exact original PNG locally. No manifest flag, resize, CDN request or Hive request was needed. This proves native delivery, not the owner's rendered/cache state. Charging command semantics did not change; the new sensor is covered separately by energy-helper and actual-framework checks.

The Energy dashboard guide maps Charging power and the native optional cumulative Energy dashboard helper to the device form, with an explicit warning against using the resetting Session energy counter directly. No owner's rate entity ID, helper configuration or meter identifiers are included in the public source/package.

## Native helper beta validation

The final 0.2.0b2 framework run passed 21 cases (the prior 16 plus five energy-helper cases) in 20.99 seconds. Actual entity-registry default disablement, enabling, energy/kWh/total-increasing metadata, accumulation independent of session resets, save/load through HA restore storage across a 600-second gap, invalid/failure/long-gap handling and duplicate prevention passed. Native branding separately passed one HTTP case in 1.36 seconds. These use synthetic telemetry, not real charger commands. Rendered Energy dashboard selection and Recorder statistics end-to-end have not been exercised; owner installation and comparison during a normal charge remain next steps.

## Current 0.2.0b3 selectable-cost validation

- **70 offline checks pass** (the prior 56 plus 14 cost/math/entity/options checks). Fixtures are invented and HA interfaces are stubbed.
- **35 actual Home Assistant runtime cases pass in 35.85 seconds** (the prior 21 plus 14 cost cases), using synthetic local price states and mocked Hive transport with declared Pyhive 1.0.10. No account, supplier or charger commands are sent to a real service.
- Cost coverage includes native options selector enrollment/removal, preserving unrelated and experimental options, currency/unit scaling and rejection, event-split intervals, negative credits, restore storage without downtime credit, unavailable-price recovery, currency separation and power freshness independent of rate events. The actual Recorder case verifies signed five-minute state/sum, hourly rollup and a daily query returning the expected net cost including negative-rate credits. This goes beyond sensor metadata; it does not exercise rendered cards or compare a supplier bill.
- The current install ZIP contains 39 whitelisted files, including 19 component files, with source-byte/privacy-marker/ZIP integrity checks. The prior native-brand test remains applicable because the PNG and delivery path are unchanged.
- No exact b3 owner installation or rendered daily-cost card is claimed. Compare estimates during a normal charge and tariff boundary before relying on them; unavailable observations can undercount. Daily views require Recorder and sufficient recorded statistics.

The native rate selector stores only a user-chosen local entity reference and currency in options. It contains no owner's EDF identifier and does not change saved Hive schedules or experimental command semantics. The standalone source/install/review artifacts are prepared locally; publication uses the owner-authorized repository; beta review and hardware validation limitations remain.

## Normal 0.2.0 release / HACS metadata

Prepared 4 November 2026 at the owner's request as a normal GitHub release. The project remains unofficial and charging controls retain their experimental labels and existing limits. Functional monitoring, cost/energy algorithms and command behavior are unchanged from the 0.2.0b3 implementation freeze; only version/User-Agent metadata, manifest codeowners, HACS metadata and documentation change. The prior 35 real-framework cases therefore remain evidence for that functional implementation, not a new owner's live installation. The 70 offline checks are rerun for this release.

HACS metadata and the integration manifest pass the actual HACS validation schemas (`HACS_MANIFEST_JSON_SCHEMA` and `INTEGRATION_MANIFEST_JSON_SCHEMA`) from official hacs/integration commit a15e87ec0d1c82e58f1ddbaf17669d3eaa261eb8. Source-folder layout checks pass: one custom_components/hive_ev integration, an actual owner, supported stable version, local brand and source downloads without ZIP-release mode. The conservative declared HA Core minimum is 2026.10.4. Root hacs.json is included in the source/release tag; HACS installs the integration subfolder. No default-catalog inclusion, upstream brand submission or end-to-end owner HACS installation is claimed.

The README and dedicated HACS guide explain adding the custom repository as Integration, choosing normal 0.2.0, restarting HA, reusing existing entries and moving from manual installation. The guide distinguishes optional future betas and keeps manual ZIP installation available. The new commit uses verified Codex author identity for agent-authored work, without rewriting published commits or giving the account collaborator access.
