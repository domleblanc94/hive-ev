# Actual Home Assistant runtime checks

These 21 pytest cases use the real Home Assistant framework with only HTTP transport mocked. They are separate from the repository's default offline unittest suite, which uses minimal framework stubs. Do not mix the two suites in one Python process.

The cases cover an explicitly enabled Energy Dashboard helper with ENERGY/kWh/TOTAL_INCREASING metadata, power accumulation across session resets, HA restore storage without downtime backfill, unavailable/failure/gap handling and discovery without duplicates. They also cover default-off controls, explicit owner/Alfen enrollment, options reload and opt-out, shared client/token behavior, fresh guards, single-attempt command handling, error/timeout disablement, suspended opt-out/re-enable races, distinct End-session binding without optimistic state changes, and bounded/redacted diagnostics discovered through Home Assistant's normal platform loader. All accounts, tokens, devices and replies are invented. Unregistered HTTP requests fail. The tests do not validate real charging, account sign-in, token renewal, all charger models or Pause.

## Run in a supported Core test environment

Use a Home Assistant Core checkout with its real pytest helpers, the supported Python version and the integration's declared `pyhive-integration==1.0.10` dependency. The recorded run uses Core development base `3f8efe14b2bec286e44f0bf7769567844ad806c4`, Linux Python 3.14.10. Other Core versions may require fixture adaptations.

1. Complete the Core test setup required by that repository. Generate English translations for `homeassistant`, `sensor`, `binary_sensor` and `button` if missing.
2. Copy this `test_home_assistant.py` temporarily into that checkout as `tests/components/hive/test_hive_ev_release_validation.py`. Keep this temporary file out of a Core contribution.
3. Set `HIVE_EV_SOURCE_DIR` to the absolute path of this standalone repository. The harness copies its component into pytest's temporary configuration directory; it does not install into a running Home Assistant system.
4. From the Core checkout, run:

```sh
HIVE_EV_SOURCE_DIR="/absolute/path/to/hive-ev" python -m pytest tests/components/hive/test_hive_ev_release_validation.py -q --disable-warnings --tb=short
```

Never substitute real credentials or account replies for the invented fixtures. This suite can run without access to a Hive account. Its safe behavior depends on retaining the supplied mocked HTTP fixtures.
