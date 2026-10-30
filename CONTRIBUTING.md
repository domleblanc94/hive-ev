# Develop and verify locally

This is a monitoring-only custom integration. Keep charging commands and experimental trial tools out of the package. Authentication calls are required for sign-in and renewal; charger data access is read-only.

## Setup and tests

Use Python 3.13 or newer for these offline tests. Home Assistant 2026.10.4 itself requires its own supported Python/runtime environment; the stub suite does not replace a real installation test.

```text
python -m venv .venv
```

Activate the environment using `.venv\Scripts\Activate.ps1` on Windows PowerShell, or `source .venv/bin/activate` on macOS/Linux. Then run from the repository root:

```text
python -m pip install -r requirements-test.txt
python -m unittest discover -s tests -v
python tools/build_integration_package.py
```

The ZIP is written to `dist/` with `custom_components/hive_ev/` at the correct installation path. It contains only explicitly allowed integration files, the install README and licence notices. Test fixtures use invented identifiers and tokens. Tests must not sign in or contact the account API.

## Source map

| File | Responsibility |
|---|---|
| `custom_components/hive_ev/config_flow.py` | Owner sign-in, SMS, explicit trusted-device consent and reauthentication |
| `custom_components/hive_ev/auth.py` | Pinned Pyhive SRP/MFA adaptation and Cognito token renewal |
| `custom_components/hive_ev/api.py` | Authenticated cloud reads and reported-value parsing |
| `custom_components/hive_ev/coordinator.py` | Shared polling and unavailable/auth-failure handling |
| `custom_components/hive_ev/sensor.py` | Status, refresh timestamp and optional measurement entities |
| `custom_components/hive_ev/binary_sensor.py` | Reported charging-session activity |
| `tests/` | Offline synthetic protocol, flow, coordinator and entity checks |

Do not log account credentials, raw HTTP bodies, home/device identifiers or user-specific URLs. An exception string from a dependency can contain private data. Keep user-facing errors bounded and sanitized.

Maintain the distinction between reported and requested values. Missing power must not become zero, a transaction flag must not be described as measured power, and session energy must not become a lifetime consumption total.

## Reviews and upstream contributions

Disclose AI assistance. OpenAI Codex generated this implementation and tests; agent review is not a claim that a human has read and understood every line. Anyone submitting a contribution must personally review it, validate it and satisfy the target project's current policies. Leave any human-review or hardware-validation declarations unconfirmed until actually completed.

Home Assistant Core contributions require a separate review of library boundaries, tests and contribution requirements; copying this custom integration into Core is not a ready submission. See [provenance](docs/development-and-provenance.md) and [testing](docs/testing.md).
