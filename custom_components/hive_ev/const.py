"""Constants for the read-only Hive EV integration."""
DOMAIN = "hive_ev"
NAME = "Hive EV"
POLL_SECONDS = 60
BASE_URL = "https://hive.bgchprod.info/"
NODE_ACCEPT = "application/vnd.alertme.zoo-6.5.0+json"
APP_KEY = "7Y1kj281ay64CAik9YTcnaFNqdiSPksW5XP2GZ4T"
COGNITO_POOL_ID = "eu-west-1_SamNfoWtf"
COGNITO_CLIENT_ID = "3rl4i0ajrmtdm8sbre54p9dvd9"
EVSE_TYPE = "http://alertme.com/schema/json/node.class.evse.json#"
CHARGER_TYPE = "http://alertme.com/schema/json/node.class.ev.charger.json#"
STATUSES = frozenset((
    "OFFLINE AVAILABLE CHARGING FINISHING FAULTED UNKNOWN UNAVAILABLE READY "
    "COMPLETE COMPLETED PAUSED SCHEDULED WAITING_TO_START WAITING_TO_RESUME "
    "WAITING_FOR_VEHICLE WAITING_FOR_VEHICLE_NOT_CHARGING UNRECOGNIZED"
).split())

CONF_COST_RATE = "electricity_rate_sensor"
CONF_COST_CURRENCY = "cost_currency"
COST_OPTIONS = (CONF_COST_RATE, CONF_COST_CURRENCY)
