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

## Optional native charging cost helper (0.2.0b3)

Open Settings → Devices & services → Hive EV → Configure. Choose **Electricity rate sensor (optional)** and save. Experimental charging controls can stay off. Leaving the rate selector unset creates no cost sensor. To disable cost tracking later, check **Remove cost helper and its selected rate sensor**, then save; historical registry/statistics records may remain. Use a current unit price in the sensor's numeric state, not a price stored only in an attribute, a whole-home cost total or standing charge. The source integration must update that state when the applicable tariff changes. One selected rate applies to every monitored charger in that integration entry; different per-charger tariffs are not configurable in this beta. No supplier or personal meter ID is built in. This reads the selected local HA sensor and does not call an electricity supplier or alter Hive's schedule.

Supported units use an explicit supported ISO currency code followed by /kWh or /MWh, such as GBP/kWh, USD/kWh, EUR/kWh or GBP/MWh. Aliases £ and € represent GBP/EUR; p, pence and GBp represent GBP pence. kWh/MWh case matters. Ambiguous $ or cents and unrelated/missing units are rejected rather than guessed. The selected source must have a finite numeric price when enrolling; an existing enrolled source can recover after temporary unavailability without signing in again.

Totals are kept separately by currency. Changing the selected source within the same currency continues that currency's total. A source that changes currency will not silently mix money units; reconfigure explicitly. Selecting another currency creates a separate currency-specific entity; reselect its card and avoid combining old/new currency totals.

The cost helper estimates cumulative charging spend from observed power and the applicable selected rate. It follows rate changes rather than multiplying all historical energy by today's rate. Negative rates can reduce the total as credits. Standing charges, losses outside charger-reported power and other fees are excluded. Missing prices/power, outages and skipped gaps cannot be recovered; an unavailable price transition may also discard the preceding partial interval conservatively; tracking starts when configured, with no import of previous sessions or bills.

The monetary sensor belongs on a normal dashboard card. It is separate from the Energy dashboard's individual-device consumption chart; that chart has no price selector. Keep the kWh Energy dashboard helper selected for consumption.

## Today's, weekly and monthly charging cost

The cost sensor keeps a cumulative total. Home Assistant's Statistic card can show the **change** during a calendar day, week or month. Its daily view follows Home Assistant's configured local timezone and does not reset the source sensor. Recorder must include the cost entity; statistics update periodically and initially may have insufficient data. The first day starts when tracking was enabled, not at midnight retrospectively.

On your normal dashboard choose Edit → Add card → Statistic, select the native Charging cost helper, choose Change and the calendar Day period. Check its actual entity ID in the charger device; generated IDs can differ. This YAML example uses a placeholder to replace with that ID:

```yaml
type: statistic
entity: sensor.your_charging_cost_helper
name: Today's EV charging cost
stat_type: change
period:
  calendar:
    period: day
```

For this week's/month's cost change day to week/month. A Tile card shows the running total instead. See [Home Assistant's Statistic card documentation](https://www.home-assistant.io/dashboards/statistic/).

## Older manual GBP cost package

The [optional YAML package](../examples/energy_cost.yaml) remains as a manual GBP-only alternative for older versions. It uses generic power and rate placeholders, with explicit GBP/pence conversions. It is not installed automatically. Prefer the native selectable cost helper in 0.2.0b3; do not install both and mistake their totals for separate charges. Previously configured personal packages stay outside this public repository.

If retaining the old package, replace both placeholders, merge its package-directory settings into your existing HA configuration, check configuration before restart and verify the generated cost-rate entity ID matches the Integral source. Unsupported units make the cost rate unavailable; supported negative prices represent credits. There is no automatic migration/backfill from that manual package to the native helper.
