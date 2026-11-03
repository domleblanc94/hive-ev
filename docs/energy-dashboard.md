# Energy dashboard and EV charging spend

## Map the Add a device fields

| Home Assistant field | Select |
|---|---|
| Device energy consumption | A cumulative kWh Integral helper created from Charging power, as below |
| Device power consumption | Hive EV Charging power, normally sensor.ev_charger_charging_power |
| Display name | EV charger, or a name of your choice |
| Upstream device | Leave empty unless an actual parent circuit/device meter already includes this EV consumption |

Do not select the heated airer as upstream just because both devices are in the garage. This field represents a metering hierarchy, not a location.

The integration's Session energy counter resets for a new session and intentionally has no long-term state class. It is not suitable for direct selection in the cumulative energy field. Do not change its state class to force it into the dropdown.

## Create the cumulative energy helper

In Settings → Devices & services → Helpers → Create helper, choose Integral (Riemann sum).

- Name: EV charging energy.
- Input sensor: Hive EV Charging power.
- Integral method: Left.
- Metric prefix: k (kilo).
- Integration time: h (hours).
- Precision: 3.
- Max sub-interval: 00:01:00 (one minute), if offered.

Power is supplied in W; the k prefix and hours produce kWh. The helper retains its accumulated value across Home Assistant restarts. After it has a valid reading, choose that helper in Device energy consumption and Charging power in Device power consumption.

This is an estimate from sampled power, not the charger's original Wh counter. A one-minute cloud poll, outages, missed transitions and Home Assistant downtime can affect accuracy. It begins when configured; it does not automatically import earlier Hive energy or the already-observed 7.11 kWh. Keep Session energy available for comparison after a normal session. Statistics/dashboard display can take time to appear after the first valid samples.

Home Assistant documents this power-to-energy approach at https://www.home-assistant.io/docs/energy/individual-devices/ and https://www.home-assistant.io/integrations/integration/ .

## EV-only spend

The individual-device form shown here has energy and power fields, not a unit-price input. Track energy there first. EV-only cost needs consumption allocated at the price applicable when the energy was used, using the owner's existing tariff/price sensors and their actual units. Current £/kWh, p/kWh, or per-MWh prices require different conversions; a household daily cost sensor is not a unit price.

Do not multiply all accumulated EV energy by today's current rate when day/night or dynamic prices differ. Do not add EV consumption as another grid import on top of an existing whole-house import just to obtain a cost display, because that counts the same electricity twice. Any later EV cost helper should be configured separately with known price sensor IDs/units and tariff timing.

The project does not yet create an energy/cost accumulator automatically. No guessed tariff, helper, sensor or automation has been installed on the owner's Home Assistant by this guide.
