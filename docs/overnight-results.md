# Overnight monitoring results: 30–31 October 2026

Recorded 31 October 2026. The owner supplied a Home Assistant activity export and a later sensor-card screenshot from the installed standalone integration, using their Hive-connected Alfen NG910. This is one real-device overnight observation. The separate Pyhive and Home Assistant Core drafts were not installed for this run.

## Activity export

All times below are Europe/London local time (UTC on these dates). The export covers 30 October 21:38:10 through 31 October 09:03:43.

| Date and time | Reported charging status |
|---|---|
| 30 October, 22:47:52 | Scheduled after reconnection |
| 30 October, 23:01:01 | Waiting to start |
| 30 October, 23:09:08 | Charging |
| 31 October, 00:10:35 | Completed |
| 31 October, 06:01:10 | Paused |

The sampled Charging interval is approximately 61 minutes 27 seconds; polling does not establish the exact physical start/stop times. The final recorded status remains Paused through the end of the export. The session-active flag remains On from 22:47, including after Completed and Paused: it must not be interpreted as measured power flow. The cause of the 06:01 transition is not established by the export.

There are 680 successful-refresh entries over approximately 11 hours 25 minutes, normally about one minute apart. The longest interval is 69.797 seconds. No Unknown or Unavailable entries appear for the three exported entities. This supports continuous overnight monitoring and continued authenticated cloud access during that window; it does not independently prove a particular token-refresh event, failure recovery, or restart recovery.

## Sensor screenshot

The later Home Assistant sensor card shows all three optional measurement sensors:

| Sensor | Displayed value | Interpretation |
|---|---|---|
| Session energy | 7,110 Wh (**7.11 kWh**) | Hive-reported energy for the session, not a lifetime total or an independently metered measurement |
| Session charging duration | 3,690 seconds (**61 minutes 30 seconds**) | Closely agrees with the sampled Charging interval |
| Charging power | **0 W** | A valid reported reading while the displayed status is Paused; it does not establish the power during active charging |

The same screenshot shows Paused and session active On. These measurements were absent from the initial idle discovery but are now visible in the installed integration. The activity CSV contains status, session activity and refresh entities only; it does not include the power, energy or duration histories. The screenshot has no capture timestamp, so its values must not be assigned an invented exact time.

## Conclusion and limits

Together the overnight status progression and reported 7.11 kWh support a successful scheduled charging session while the standalone monitoring integration ran. This validates visibility of the optional power, energy and duration sensors on this account. It is not an independent vehicle/meter comparison, proof of a nonzero instantaneous power reading, or evidence that the uninstalled upstream patches work on live hardware.

The run followed cable reconnection after the earlier supervised trials. It does not resolve persistent Finishing after Stop, prove same-plug restart after Stop, establish repeated-night reliability, or validate charging controls. Earlier control-trial readings of zero/absent power remain separate observations. No new charging commands or schedule changes were made for this documentation update.

Only bounded results are recorded here. The original CSV, screenshot, account identifiers and private research are not included in the public repository or release bundle. See [testing](testing.md) for the full record and [next steps](next-steps.md) for remaining work.
