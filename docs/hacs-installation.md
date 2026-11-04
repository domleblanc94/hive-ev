# Install Hive EV with HACS

Hive EV is available through a **HACS custom repository**. It has not been submitted to or accepted into the default HACS catalog. The integration remains unofficial; a normal GitHub release is not approval or endorsement by Hive, OpenAI or Home Assistant.

## Before you start

Use Home Assistant Core 2026.10.4 or newer. This is a conservative declared minimum matching the owner's existing monitoring installation; it is not a claim that every later version/hardware model has been tested. Back up Home Assistant. When upgrading, disable experimental charging controls in Hive EV Configure and keep your existing entry.

If HACS is not installed, use its official [Home Assistant OS/Supervised download instructions](https://www.hacs.dev/docs/use/download/download/). They provide the Get HACS add-on/repository link. Install/start that add-on, follow its logs, restart HA and complete HACS setup/authorization. This installs HACS itself; it is separate from adding Hive EV below. Do not enter Hive credentials into GitHub or HACS.

## Add and download this integration

1. Open **HACS** from the sidebar.
2. Select the top-right **three dots → Custom repositories**.
3. Repository: `https://github.com/domleblanc94/hive-ev`.
4. Type/category: **Integration**. Select **Add**.
5. Search for **Hive EV (unofficial)** and open it. Clear restrictive Downloaded-only filters if it is not shown.
6. Select **Download** and choose **0.2.0**, the normal release. If this repository is already downloaded, open its three-dot menu and select **Redownload** instead. Button labels can vary slightly with HACS version.
7. Restart Home Assistant after downloading.
8. First install: **Settings → Devices & services → Add integration → Hive EV**. Sign in with the Hive account owner and complete SMS verification. If trusted-device registration is offered, read the consent text before selecting it.
9. Upgrade: reuse the existing Hive EV entry. Monitoring should resume without re-adding it. Check retained options and leave experimental controls off unless deliberately performing a supervised test.

HACS reads the release's `custom_components/hive_ev/` files. You do not upload a ZIP, edit configuration.yaml or add this GitHub URL to the HA add-on store to install Hive EV itself. The manual release ZIP remains available as an alternative.

## Existing manual installation

Back up `/config/custom_components/hive_ev`, add the repository and download through HACS. It manages that same domain/folder; retain the existing integration entry. Restart and check status/power against Hive. Do not create a second Hive EV configuration solely to move to HACS. Price-source selection and the disabled-by-default kWh helper remain independent options; see [Energy dashboard and daily cost](energy-dashboard.md).

## Updates and older betas

Use HACS to download later published releases, then restart HA. Back up before changing versions and inspect experimental-control enrollment after upgrades. Download 0.2.0 for this release; older 0.2.0b1–b3 pre-releases do not include the HACS metadata added here and are not the supported HACS installation target. If intentionally testing a future beta, enable the repository's **Pre-release / Show beta versions** setting when offered, then choose the exact beta in Download/Redownload. A beta may be hidden by default. Do not select the development branch as a substitute for a published release.

## Troubleshooting

- Repository not found: use the full URL above and category Integration. This custom repository is not automatically in HACS search until added.
- No compatible version: check HA Core is at least 2026.10.4, refresh HACS repository information and choose 0.2.0. Keep the beta switch off for the normal release.
- Hive EV missing from Add integration: restart HA after the download, refresh the browser and check HA logs for a reviewed error summary. The expected manifest path is `/config/custom_components/hive_ev/manifest.json`.
- Existing entry/sensors already present: keep them; downloading through HACS does not require deleting the configuration.
- No cost sensor: choose a supported current-rate sensor in Hive EV Configure. No price entity is hardwired in. The Energy dashboard helper must be enabled separately on the charger device.
- End session leaves Finishing: that is the documented experimental end/unlock action, not a HACS install problem. Follow Hive guidance and verify scheduled readiness after reconnecting if needed.

Sources: [HACS custom repositories](https://www.hacs.dev/docs/faq/custom_repositories/), [integration requirements](https://www.hacs.dev/docs/publish/integration/), [hacs.json reference](https://contributors.home-assistant.io/marketplace/reference/hacs-json/).
