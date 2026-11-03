# Energy dashboard and EV charging spend

## Native Energy dashboard helper (0.2.0b2)

Hive EV supplies an optional sensor named **Energy dashboard helper**. It is a cumulative **kWh estimate** derived from reported charging power, with energy/total-increasing statistics metadata so Home Assistant can offer it directly in the Energy dashboard. It is independent of electricity supplier and price sensors.

The helper is disabled by default. Open Settings → Devices & services → Hive EV → the charger device, show disabled entities, open Energy dashboard helper and enable it. Alternatively find the disabled entity under Settings → Devices & services → Entities, filtered to Hive EV. Wait for successful power updates/statistics before selecting it.

| Add a device field | Select |
|---|---|
| Device energy consumption | Hive EV Energy dashboard helper (kWh) |
| Device power consumption | Hive EV Charging power (W) |
| Display name | EV charger, or your preferred name |
| Upstream device | Leave empty unless a real parent device/circuit meter already includes this EV usage |

Do not select the heated airer as upstream merely because it shares the garage location. The upstream field describes a metering hierarchy.

## What the helper measures

It estimates energy from valid power samples at the normal cloud polling interval. Its total persists across charging-session resets and restores after a Home Assistant restart. It does not replay unobserved offline time. Invalid/missing power, failures, removed nodes, reversed time and long observation gaps cannot create invented consumption. Tracking starts when enabled, and lost observations are not reconstructed from the session counter.

The helper is not the charger's lifetime/billing meter. Sampling, cloud delays, skipped gaps and outages affect accuracy; compare it with Session energy after a normal charge. Session energy is still the provider's per-session Wh counter and intentionally is not offered directly as a cumulative statistics source. Do not change its state class to force it into the dropdown.

Disable/re-enable and restart preserve the helper total when its valid stored state is available. Changing entity identity, deleting stored data or restoring an older HA backup can affect the total. Do not expect automatic backfill of the previously observed 7.11 kWh or charging while HA was offline.

## Older versions / alternative manual helper

On builds before 0.2.0b2, create an Integral (Riemann sum) helper from Charging power in Settings → Devices & services → Helpers. Use Left method, kilo prefix, hours, precision 3 and a one-minute max sub-interval. That also estimates cumulative kWh. Prefer the native helper on the new beta; do not add both totals as separate EV devices, which would duplicate the same usage.

Home Assistant documents the power-to-energy approach at https://www.home-assistant.io/docs/energy/individual-devices/ and https://www.home-assistant.io/integrations/integration/ .

## Optional provider-neutral GBP cost package

Energy and power are selected in the individual-device form; it has no unit-price/cost selector. The [optional cost package](../examples/energy_cost.yaml) is a separate manual HA configuration, not an option in Hive EV Configure. It has placeholders and no supplier-specific entity or meter identifiers. No cost helper is installed automatically.

1. Replace sensor.your_ev_charger_power with your own Hive EV Charging power entity.
2. Replace every sensor.your_current_electricity_price with your current unit-price entity. Recognised units are GBP/kWh, £/kWh, p/kWh, pence/kWh, GBp/kWh and GBP/MWh. Other units leave the cost rate unavailable. This is a GBP example, not a universal-currency configuration.
3. Place the configured file under /config/packages/ and enable that directory in the EXISTING homeassistant packages configuration. Merge settings rather than duplicating homeassistant/packages sections; check configuration before restarting.
4. Verify the generated EV charging cost rate entity ID. If an existing name causes a suffix, update the cost integration source to the actual ID. Do not install both a tailored private copy and this example.

This package creates a GBP/hour cost rate and cumulative GBP cost from sampled power at the contemporaneous unit price. The native energy helper supplies cumulative kWh separately. Add EV charging cost as a dashboard tile; no daily/monthly resets or historic billing import are automatic. Supported negative prices represent credits; standing charges and other fees are excluded. Estimates are not an invoice.

Do not multiply all accumulated energy by today's current rate across changing tariffs, or add EV energy as a second grid import beside a whole-house import. Keep configured packages and personal meter IDs outside the public repository/web uploads. There is no built-in price picker in this beta.
