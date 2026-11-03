# Develop and verify locally

This beta provides reported monitoring and explicitly enabled experimental manual controls. Keep supported behaviour, synthetic tests and owner observations distinct. The implementation/tests/docs were generated with OpenAI Codex; contributors must review and understand submitted changes themselves.

## Offline checks

Use Python 3.14 for the recorded environment and create a virtual environment:

```text
python -m venv .venv
python -m pip install -r requirements-test.txt
python -m unittest discover -s tests -v
python tools/build_integration_package.py
python tools/check_package.py
```

Activate `.venv` before running the remaining commands (`.venv\Scripts\Activate.ps1` on Windows, `source .venv/bin/activate` on Linux/macOS). These 70 checks use Home Assistant stubs and invented data. They must not sign in, request SMS or contact a real account/charger.

The separate actual Home Assistant pytest harness lives in `tests/runtime/`, outside offline discovery. Its README explains copying the test into a suitable Core framework checkout and using HIVE_EV_SOURCE_DIR. It requires the real Home Assistant test environment and the component's declared released Pyhive 1.0.10 dependency. Do not install the unpublished upstream-library draft as a substitute.

The packaging script whitelists component files, public docs and licence notices into `dist/hive-ev-<version>.zip`. Private research, downloaded diagnostic files, account responses, runtime environments, APKs/decompiled code and experimental source backups must remain excluded. Runtime reproduction files belong in a source archive, not the install ZIP.

## Source map

| Area | Responsibility |
|---|---|
| config_flow.py / auth.py | Owner sign-in, SMS, trusted-device consent, options and normal renewal |
| api.py / coordinator.py | Authenticated monitoring, reported parsing and unavailable/reauth state |
| sensor.py / binary_sensor.py | Stable monitoring entities and late optional telemetry |
| energy_helper.py | Default-disabled cumulative kWh estimate, restore and observation-gap handling |
| cost_helper.py / cost_math.py | User-selected local rates, explicit units/currencies, signed cost totals and tariff-event boundaries |
| controls.py / button.py | Fresh guarded manual writes, attempt limits, uncertain-delivery opt-out |
| diagnostics.py / diagnostic_shapes.py | Explicit bounded technical diagnostics and redaction |
| tests/ | Synthetic offline suite; tests/runtime/ is the separate real-framework harness |

## Behaviour and privacy

Never log account credentials, raw HTTP bodies, IDs/names or user-specific URLs. Dependency exception strings may contain private data. Maintain fixed safe errors and invented fixtures. An embedded shared app-client identifier is not a user's credential or an official API permission grant.

Reported values remain authoritative. Missing power is not zero, active session is not measured power, session energy is not lifetime consumption, and acknowledgement is not completed physical action. Optional sensors must appear when data becomes available without resetting existing identities.

Do not remove enrollment/fresh-state gates, retry writes automatically, label End as Pause, or silently widen support to other modes/devices. Options changes/unload must invalidate queued old controllers; token-save updates must not reload them. Diagnostics must never invoke controls or retrieve installer credentials. Add meaningful tests when those boundaries change.

## Releases and upstream

Follow PUBLISHING.md and [release validation](docs/release-validation.md). Publishing is a reviewed owner action; no workflow should silently release on a push. Preserve required notices and Codex provenance.

The separate built-in Hive contribution uses a public Python client boundary and remains monitoring-only. Do not copy this standalone component wholesale into Core. Follow the destination project's instructions and complete human-review declarations truthfully.

## Hosted checks

The prepared GitHub Actions workflow runs the offline suite, builds the whitelisted install ZIP, verifies its file scope/source/privacy markers and retains a review artifact. It uses read-only repository permissions and does not publish releases or contact a Hive account. Action revisions are pinned to commits verified against their official release tags. The real-framework suite remains a separate supported-environment check. No hosted run is claimed before this repository is published and GitHub executes it.

Cost-helper changes must test tariff boundaries, same-timestamp observations, currency isolation, signed credits and independent power freshness across rate events. Preserve unrelated options and experimental-control opt-out behavior. Do not add supplier-specific entity IDs, silently guess units or recover missing cost by multiplying historical energy by a current rate.
