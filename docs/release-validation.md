# Release candidate validation: 0.2.0b2

Prepared 3 November 2026. The public beta source includes monitoring, two default-off experimental manual controls and explicit diagnostics. No release has been published and no GitHub destination is configured yet.

## Automated checks

- Public source promotion: 56 offline tests passed, including 20 original monitoring checks, 16 control checks, nine diagnostic privacy/read-only checks and 11 energy-helper checks. These use Home Assistant stubs and invented fixtures.
- The public beta passed **21 genuine Home Assistant runtime cases in 20.99 seconds** on Linux Python 3.14.10 with the declared Pyhive 1.0.10 dependency. The normal loader and component hooks are real; HTTP responses and existing token metadata are synthetic. No real account, Cognito or charger calls were made. `tests/runtime/` contains reproduction instructions and the harness.
- The 37-file installation package passed independent whitelist, source-byte, private-key/JWT-marker and ZIP-integrity checks. Relative Markdown links passed across 18 public documents. The final archive is rebuilt after documentation freeze.
- Candidate public files were reviewed for excluded private research/data, and the frozen component/runtime-harness hashes match the actual-framework run. No original app material, owner CSV/JSON/screenshots or private research is included.
- The prepared GitHub Actions YAML parsed with the expected events and read-only permissions. It runs offline checks/build/package validation and retains a review artifact; no hosted execution or automatic release is claimed.

See testing.md for the distinction between synthetic framework checks, owner-reported hardware evidence and remaining requirements. The separate Core/library contribution tests do not validate this custom component by themselves.

## Publication status

The owner confirmed that the GitHub repository has not been created. The current manifest's documentation link remains the real built-in Hive page as a documented temporary fallback; it does not document this beta. Replace it with the actual project URL, add an actual issue URL if wanted, and verify the links before publishing. No HACS availability, hosted CI result, public release, maintainer acceptance or human code-review declaration is asserted.

The exact beta candidate has not been installed on the owner's live system. Its predecessor's reported hardware results and the synthetic public-code tests are different evidence. The separate Core/library contribution remains monitoring-only and has additional dependency/repository gates.

## Logo and energy-guide addition

The original generated orange/white logo is bundled unchanged as brand/icon.png and referenced by the README. One additional narrow test of the real Home Assistant Brands HTTP API passed in 1.47 seconds: icon, logo, dark and high-resolution fallbacks returned the exact original PNG locally. No manifest flag, resize, CDN request or Hive request was needed. This proves native delivery, not the owner's rendered/cache state. Charging command semantics did not change; the new sensor is covered separately by energy-helper and actual-framework checks.

The Energy dashboard guide maps Charging power and the native optional cumulative Energy dashboard helper to the device form, with an explicit warning against using the resetting Session energy counter directly. No owner's rate entity ID, helper configuration or meter identifiers are included in the public source/package.

## Native helper beta validation

The final 0.2.0b2 framework run passed 21 cases (the prior 16 plus five energy-helper cases) in 20.99 seconds. Actual entity-registry default disablement, enabling, energy/kWh/total-increasing metadata, accumulation independent of session resets, save/load through HA restore storage across a 600-second gap, invalid/failure/long-gap handling and duplicate prevention passed. Native branding separately passed one HTTP case in 1.36 seconds. These use synthetic telemetry, not real charger commands. Rendered Energy dashboard selection and Recorder statistics end-to-end have not been exercised; owner installation and comparison during a normal charge remain next steps.
