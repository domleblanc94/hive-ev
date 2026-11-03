# Experimental controls: supervised trial and recovery

The beta offers Charge now and End charging session. Both are disabled on a new installation until Configure enrollment confirms ownership and the single Alfen scope. Existing experimental options survive upgrades, so disable them before replacing files and inspect Configure afterwards.

## Before enabling

Back up the component and Home Assistant. Keep Hive available, check the saved schedule and current state, and make sure the car can accept charge. Choose a time when the current tariff cost is acceptable and the owner can supervise. Use no control automations in this beta.

Enable both options in Settings → Devices & services → Hive EV → Configure. The buttons appear on the charger device. Loading, polling and enrollment alone do not send commands.

## Charge Now

Press Charge now (experimental) once from a settled normal Custom/Tariff session reporting Scheduled, Paused or an eligible waiting state, active session, no override and 0 W. The integration performs fresh reads before sending one override request.

Watch Hive, Home Assistant and the car for Charging and positive power. An HTTP acknowledgement is not physical confirmation. If the result is uncertain, do not repeat, reload or send the opposite action blindly; inspect Hive/car. Controls turn off after uncertain delivery. Re-enabling cannot cancel an earlier request.

## End charging session

Only continue when the fresh state is Charging with positive power and an active Charge Now override. Wait at least 60 seconds after acknowledgement before pressing End charging session once. Missing/zero power or another state is refused; use Hive to manage the session if the guard refuses.

This is the native end/unlock action. It may produce Finishing, 0 W and an inactive session and may release the cable. It is not Pause and does not guarantee a same-plug restart. The beta does not expose general stopping for regular non-overridden scheduled charging.

Confirm the car has stopped, then follow Hive's unplug/reconnect instructions if required. Check saved charging times, no unwanted override, and connected scheduled readiness before leaving the charger unattended. The owner saw recovery after reconnection in the November trial; earlier automatic recovery was also observed.

## Attempt limits and disabling

Each integration runtime permits at most one attempt of each action, consumed before transport. A 60-second cooldown also applies. A deliberate new supervised trial requires checking Hive and disabling/re-enabling enrollment. Reload/restart resets runtime limits and is not backend deduplication or cancellation. These limits must not be bypassed to resend an uncertain request.

Disable commands in Configure after the trial. Home Assistant may retain unavailable registry entries; their active handlers are unloaded. Disabling controls or rolling back does not undo a request already delivered.

## Rollback

Resolve any pending override or session in Hive first. Disable commands, restore the backed-up monitoring or experimental component folder, and restart Home Assistant. Use the existing entry so stored identity and entity IDs are retained. Verify monitoring and Hive readiness afterwards. Keep backups outside custom_components so they are not treated as another integration.
