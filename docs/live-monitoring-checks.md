# Live monitoring checks in Home Assistant OS

These checks use the installed monitoring component. They do not install the separate upstream drafts or change the Hive schedule. Record results only after observing them; do not treat this checklist as completed validation.

## 1. Export the existing overnight measurement history

The completed 30–31 October charge may already have the missing power history. Check that before waiting for another charge.

1. Open **History** in Home Assistant.
2. Select these six charger entities by their display names: **Charging status**, **Charging session active**, **Last successful refresh**, **Charging power**, **Session energy** and **Session charging duration**. Entity IDs can vary; use the entities on this integration's charger device.
3. Set the interval to **30 October 2026, 22:45 through 31 October 2026, 01:00**, in Europe/London local time. This brackets Scheduled, Charging and Completed from the existing export.
4. Use the History export/download option to save CSV. If the interface only exports one entity at a time, export the three measurement histories separately for the same interval. Activity data alone may omit numeric sensor history; confirm that the power, energy and duration entities actually appear in the file.
5. Check for a nonzero charging-power sample, the session energy rising to approximately **7,110 Wh**, and duration rising to approximately **3,690 seconds**. Preserve units and timestamps; a display set to kWh may show **7.11 kWh** instead of Wh. Do not add repeated session-energy values together.

If no earlier numeric history exists, use the next normal scheduled charging session. Missing history is not proof that the charger delivered no energy. Entities may first have appeared later, or Recorder settings may exclude them. Do not change schedules, force a daytime charge or query the database to fill the gap.

Compare with the Hive app's same-session energy and duration where available. A car or meter reading is a useful separate check, but its measurement boundary and losses may differ. The existing screenshot proves visible sensors and a paused reading of 0 W; it does not yet prove recorded active-charge wattage.

Home Assistant's [History documentation](https://www.home-assistant.io/integrations/history/) describes CSV export and its dependency on Recorder.

## 2. Check Home Assistant restart recovery

If a restart has already happened, first record whether updates resumed. Otherwise do this at a convenient idle time, when briefly interrupting Home Assistant will not disrupt another household task. A Home Assistant restart temporarily interrupts all integrations and automations, not just Hive EV.

1. Note the six current entities, their entity IDs and the last-refresh timestamp. A private screenshot is sufficient; no account credentials are needed.
2. In **Settings → System**, select the top-right power icon and **Restart Home Assistant**. Use the application restart rather than a host reboot, shutdown or safe-mode restart.
3. Once Home Assistant returns, allow approximately two polling cycles. Confirm the existing charger and entity IDs remain, there are no duplicate devices, and Last successful refresh advances again.
4. Record whether another sign-in/SMS was requested. If it was, follow the normal integration reauthentication flow; do not remove/re-add the integration merely to make the test pass.
5. Check that the Hive app still shows the expected schedule and charger state. Report the restart time, whether the same entities recovered, any sign-in request and whether an error appeared. Review any log excerpt before sharing; never share `.storage`, tokens or full configuration files.

See Home Assistant's [restart instructions](https://www.home-assistant.io/common-tasks/general/restarting/).

## 3. Continue normal scheduled use

Leave the installed monitor running for further scheduled sessions and note any unavailable periods, repeated sign-in requests, duplicate entities or inconsistent measurements. The first overnight run has already succeeded; this step assesses repeatability. A specific token renewal event cannot be inferred solely from the refresh timestamp.

Charging controls remain excluded. No Start, Stop, cable release, forced charge, OCPP change or unplug/replug trial is required by this checklist.
