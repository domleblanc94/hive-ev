# Hive EV for Home Assistant

A monitoring-only custom integration for Hive-connected EV chargers, initially tested with an Alfen NG910. It uses the Hive cloud and keeps your existing Hive integration and charger setup in place. It contains no charger controls or schedule changes. It is unofficial and is not endorsed by Hive, Alfen or Home Assistant.

The human user installed this integration in Home Assistant. During the 30–31 October 2026 overnight run, monitoring continued through a scheduled charge; Hive reported **7.11 kWh** and **61 minutes 30 seconds** of session charging. The power, session energy and duration sensors are now visible; the later paused power reading is **0 W**, while active-charge wattage is not yet recorded. See [overnight results](docs/overnight-results.md) and [next steps](docs/next-steps.md). The owner also reports restarting Home Assistant and seeing updates resume without another sign-in. Registry/duplicate-entity checks, specific renewal events and longer-term reliability remain to be checked. This uses an undocumented app API, so Hive service changes may affect it.

**Developed with OpenAI Codex:** the implementation, tests and documentation were AI-generated with multi-agent investigation and review; the human user ran local discovery and hardware trials. See [development and provenance](docs/development-and-provenance.md) for the process, attribution and limits.

## How the API was identified

USB debugging was used only to copy the installed official Android APK through ADB. Codex inspected its React Native/Hermes version 96 bundle using strings and `hermes-dec`, then traced Cognito sign-in/MFA, account homes, version 6.6 node metadata and version 6.5 reported features. The human user ran normal authentication locally and shared sanitized results confirming the charger data. No private app data or intercepted passwords were used, and MFA was not bypassed. This is an undocumented app interface, not an official developer API.

Separate control research traced the app's confirmation popup and session handlers. The first control-host trace was wrong and the request was rejected; independent review corrected the resolver. Local tests had not proved that the provider endpoint was correct. Later app and trial observations both showed Charging → Finishing after Stop, which establishes an end-session pattern rather than reliable pause/resume. Controls are excluded here. APKs, decompiled code and app assets are not distributed. See [the full provenance record](docs/development-and-provenance.md).

## What appears in Home Assistant

- **Charging status:** Hive's reported display state, such as Available or Charging. Available does not establish whether a cable is plugged in.
- **Charging session active:** Hive's reported transaction flag. An active session does not always mean the car is drawing power.
- **Last successful refresh:** when Home Assistant last received a successful cloud update, rather than when the charger itself last reported.
- **Charging power**, **Session energy** and **Session charging duration:** added when Hive first supplies these readings. The idle discovery did not include these measurements; all three sensors were visible after the overnight charge. Missing readings stay unknown; they are not replaced with zero.

Session energy and duration can reset with a new session. They are not lifetime energy totals and are not intended as an Energy dashboard consumption source. Connection or authentication failures make entities unavailable instead of presenting old readings as current.

## Install

1. Make a Home Assistant backup.
2. Download or copy this repository and locate `custom_components/hive_ev`. Alternatively, extract a monitoring ZIP built from this source.
3. Using your usual File editor, Studio Code Server or Samba access to Home Assistant, copy that folder into your Home Assistant configuration folder. The result must be `/config/custom_components/hive_ev/manifest.json`. Avoid an extra nested `hive_ev` folder.
4. Restart Home Assistant.
5. Open **Settings → Devices & services → Add integration**, search for **Hive EV**, and follow the sign-in prompts. Use your Hive account-owner login with two-factor authentication enabled, and enter the SMS code when requested. If Hive requires a new trusted sign-in device, a separate step offers an initially unchecked **Register Home Assistant Hive EV as a trusted sign-in device** checkbox. Selecting it registers Home Assistant's sign-in with Hive to support unattended token renewal. It does not associate or reconfigure your charger.
6. Open the new Hive EV integration's device to see its monitoring entities. Keep the existing **Hive** integration installed for heating and other devices.

There is no GitHub or HACS repository configured for this package. Installing it does not require changing the charger's OCPP destination, local network settings or Hive schedules.

## Account and privacy

Enter credentials only in Home Assistant's sign-in form; do not share them in chat. The integration stores ID and refresh tokens, expiry, user ID and, when needed, a trusted-device key in Home Assistant's normal `.storage` configuration so it can reconnect. Treat Home Assistant backups as private because they may include tokens. It retains neither your account password nor a device password.

If Hive expires or rejects the login, Home Assistant should request reauthentication. Open the integration or the related repair prompt and sign in again. An SMS may be required. Removing the integration deletes its local configuration entry; it does not remove the charger from Hive or automatically revoke a trusted sign-in device registered with your Hive account.

## First trial

After installing, compare the displayed status and session activity with the Hive app. Check again during your next normal charging session, then confirm updates continue after a Home Assistant restart. Leave the integration running long enough to check token renewal. Continue using the Hive app for charging controls.

If it fails to load, use **Settings → System → Logs** to find the integration's error. Do not share full configuration files, tokens or raw cloud replies. Review any diagnostic material before sharing it; this package does not provide a dedicated diagnostics exporter. This integration polls the cloud every 60 seconds, so updates are not instantaneous.

## Development verification

API, authentication, configuration-flow, coordinator and entity checks cover data handling and setup behaviour. Home Assistant interfaces are stubbed in local tests. The implementation was reviewed against Home Assistant 2026.10.4 APIs; the human's successful installation and overnight monitoring are separate evidence from these tests. Full lifecycle validation and sustained token renewal remain part of the trial.

For setup, source structure, local tests and ZIP packaging, see [CONTRIBUTING.md](CONTRIBUTING.md). [Architecture](docs/architecture.md) explains authentication and reported data; [testing](docs/testing.md) records what has and has not been verified. Controls investigated in separate supervised trials are not distributed in this monitoring repository. Stopping a charging session is not established as a pause/resume action, and automatic recovery to readiness remains condition-dependent and unresolved.

## Scope

This project provides EV monitoring only. Solar, battery and other additional device support, historical-data retrieval and charger controls are not implemented.

To review publication requirements, including the unresolved legal/permission questions, see [PUBLISHING.md](PUBLISHING.md). No legal clearance or Hive permission is claimed. The [upstream contribution plan](docs/upstream-contribution-plan.md) covers the separate Hive library and Home Assistant Core work.

Entity behaviour follows the official Home Assistant documentation for [coordinator updates](https://developers.home-assistant.io/docs/integration_fetching_data/), [sensors](https://developers.home-assistant.io/docs/core/entity/sensor/) and [binary sensors](https://developers.home-assistant.io/docs/core/entity/binary-sensor/).
