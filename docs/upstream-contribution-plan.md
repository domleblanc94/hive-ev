# Upstream contribution plan

Research checked **30 October 2026**; live validation updated **31 October 2026**. The user confirmed the existing Hive integration in [`home-assistant/core`](https://github.com/home-assistant/core/tree/dev/homeassistant/components/hive) as the upstream target. Prepare monitoring support first; keep charging controls separate until their behaviour has been verified. This plan does not create a pull request, certify submission readiness, or imply maintainer approval.

The standalone custom integration and an upstream Hive contribution are different deliverables. The former contains protocol and authentication code that cannot simply be copied into Core. Local library, Core, and documentation drafts have now been prepared; nothing has been submitted upstream.

## Local implementation status

- The Pyhive branch adds optional asynchronous `hive.ev.get_devices()` and a reported-value charger model. The full library suite passed 1,124 tests with 100% coverage, and the package build passed. Source mypy and the tracked-file Linux-platform type check passed; native Windows all-file mypy encounters existing Unix-only script APIs.
- The Core branch adds an optional EV coordinator and monitoring entities to the existing Hive integration. All 30 Hive tests, including seven new lifecycle tests, passed using the real Home Assistant framework on Linux Python 3.14.10. Scoped Ruff checks passed. Full development bootstrap and repository-wide checks remain incomplete.
- The companion website change adds the monitoring reference under the Hive integration on the `next` branch. Targeted Markdown and prose lint checks passed.
- The Core manifest still pins 1.0.10, so EV support stays inactive with the currently pinned client. A compatible published library release and a reviewed dependency upgrade are still required. No version, release, public PR URL, or maintainer acceptance has been invented.

These are review drafts, not a claim that the new upstream implementations were installed on the device owner's Home Assistant. The owner's live evidence comes from the standalone monitoring integration and diagnostic tools. Existing initialized Hive hub accounts are the first upstream scope; EV-only setup is not implemented.

## Current upstream architecture

- [Core's Hive manifest](https://github.com/home-assistant/core/blob/dev/homeassistant/components/hive/manifest.json) currently pins `pyhive-integration==1.0.10`; its code owners are `@Rendili` and `@KJonline`.
- [Core setup](https://github.com/home-assistant/core/blob/dev/homeassistant/components/hive/__init__.py) creates `apyhiveapi.Hive` and calls `session.startSession`. Its existing [sensor platform](https://github.com/home-assistant/core/blob/dev/homeassistant/components/hive/sensor.py) consumes the library's discovered devices and reported state.
- [Pyhive's development package](https://github.com/Pyhass/Pyhive/blob/dev/pyproject.toml) currently identifies itself as `2.0.0.B4`. Its development layout has [`src/session`](https://github.com/Pyhass/Pyhive/tree/dev/src/session) and [`src/devices`](https://github.com/Pyhass/Pyhive/tree/dev/src/devices), with compatibility aliases for older callers. That differs from the installed 1.0.10 used by the standalone prototype. Choose the appropriate release/backport strategy with maintainers; do not assume a beta dependency upgrade is acceptable.
- Core currently accesses `devices["parent"][0]` during setup. Any proposed EV-only account support needs deliberate handling of accounts without a heating hub. If that is outside the first contribution's scope, state the limitation and preserve existing-account behaviour.

## Suggested contribution sequence

1. **Library monitoring support.** Add the authenticated home/node reads, EVSE discovery and reported-value model to Pyhive. Reuse its session/authentication interfaces instead of shipping private auth overrides in Core. Keep EV and existing heating/light discovery distinct internally; do not make an unavailable EV service silently invalidate otherwise usable heating data.
2. **Library tests and release.** Cover the broker-only node representation versus the detailed feature representation, absent optional measurements, reported versus target values, token expiry, refresh failure, and redacted errors. Use invented/anonymised fixtures, not raw account payloads. Obtain an appropriate published library version before a Core dependency bump can be merged.
3. **Existing Core Hive entities.** Add monitoring entities under the `hive` domain using that library API, preserving existing config entries and device/entity identities. Use normal Home Assistant translations, registry conventions and failure handling. Keep “session active” distinct from actual charging; an active transaction alone does not prove power flow. Missing power/energy readings remain unknown.
4. **Real Core tests and documentation.** Add tests in `tests/components/hive` using Home Assistant's fixtures and mocked library. The standalone Windows tests with framework stubs are useful development checks, but are not Core runtime tests. Update the [Hive integration documentation](https://github.com/home-assistant/home-assistant.io/blob/next/source/_integrations/hive.markdown) in a companion documentation pull request.
5. **Controls separately.** Monitoring can be reviewed without experimental controls. Any later control contribution should document the exact meaning of Charge Now and end-session/cable unlock, their observed behaviour, and schedule interaction. Do not present these as generic pause/resume or claim overnight readiness from schedule equality alone.

Core's [development checklist](https://contributors.home-assistant.io/core/development/checklist/) requires device/service communication in a public, appropriately licensed Python library published on PyPI. It also calls for tests, formatting and user-facing documentation. The [pull request template](https://github.com/home-assistant/core/blob/dev/.github/PULL_REQUEST_TEMPLATE.md) includes `hassfest`, generated dependency requirements, dependency changes and linked documentation where applicable. Follow the current [testing instructions](https://contributors.home-assistant.io/core/development/testing/) and repository instructions when an actual checkout is prepared.

[Pyhive's contributing guide](https://github.com/Pyhass/Pyhive/blob/dev/CONTRIBUTING.md) targets `dev`, not `master`. Its [repository guidance](https://github.com/Pyhass/Pyhive/blob/dev/CLAUDE.md) requires editing async `src` rather than generated sync files, preserving compatibility aliases, anonymising fixtures, and running the full tests and pre-commit checks. Its current coverage threshold is 99%.

## AI provenance and human responsibility

The [Open Home Foundation AI policy](https://contributors.home-assistant.io/start/ai-policy/) permits AI-assisted code and documentation, but requires the human contributor to review, understand and be able to explain every submitted change. It prohibits autonomous contributions and expects the contributor to answer maintainers substantively themselves. AI can help with grammar; it must not supply unreviewed answers on the contributor's behalf. Preparing local code and drafts does not establish that the human-review requirement has been met.

Retain the original [Core template](https://github.com/home-assistant/core/blob/dev/.github/PULL_REQUEST_TEMPLATE.md) when preparing the eventual PR. Do not complete its human-review declarations on the user's behalf. This separate planning checklist remains **unchecked**:

- [ ] Contributor can explain the complete implementation.
- [ ] Contributor has personally assessed generated changes against project requirements.
- [ ] Real local execution has verified the proposed behaviour.
- [ ] Required automated checks have succeeded.

Do not have an agent open or post an upstream pull request, issue or review comment autonomously. The user intends to review and publish the work themselves. A truthful standalone provenance document should distinguish AI implementation/review from the user's requirements, hardware observations and any review they personally perform; it must not invent human code review. If quoting an AI interaction upstream, label it as such in a short quote block and add the contributor's own explanation of its relevance.

Core contributions also require the contributor to complete the normal [licensing/CLA process](https://contributors.home-assistant.io/start/licensing/). Pyhive is [MIT licensed](https://github.com/Pyhass/Pyhive/blob/dev/LICENSE); retain required notices for copied or substantially adapted portions. Do not include proprietary app packages, decompiled bundles, local account data, tokens or device identifiers in the public repository or contribution fixtures.

## Readiness record

The monitoring API path has been demonstrated against the user's account. The standalone overnight run now shows continuous monitoring and Hive-reported 7.11 kWh, 3,690 seconds, and paused power 0 W; see [overnight results](overnight-results.md) and [next steps](next-steps.md). This is not live validation of the separate upstream patches. This plan makes no broader hardware-compatibility claim and does not certify sustained token renewal, all charging measurements, or control/schedule behaviour. Record actual validation separately with dates and limitations.

- [x] User confirmed the built-in Hive integration in home-assistant/core as the upstream target; monitoring is the first planned contribution.
- [x] Local library patch follows the development branch and proposed additive public API.
- [x] Recorded library tests, build and qualified static checks passed.
- [ ] A compatible library release is published.
- [x] Local Core implementation and genuine Hive integration tests pass.
- [ ] Dependency generation, linting, translations and companion documentation are complete as applicable.
- [ ] Human contributor reviews and understands the complete proposed change.
- [ ] Human contributor prepares/submits the upstream pull request using its original template.

Until those steps are complete, describe this as a **contribution plan and prototype**, not a merge-ready Core pull request.
