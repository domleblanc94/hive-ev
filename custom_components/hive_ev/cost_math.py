"""Provider-neutral currency normalization and observed-interval cost math."""
from __future__ import annotations

from datetime import datetime, timedelta
import math

MAX_INTERVAL_SECONDS = 180
# ISO 4217 currency codes, excluding funds, precious metals and no-currency codes.
CURRENCIES = frozenset("""AED AFN ALL AMD ANG AOA ARS AUD AWG AZN BAM BBD BDT BGN BHD BIF BMD BND BOB BRL BSD BTN BWP BYN BZD CAD CDF CHF CLP CNY COP CRC CUP CVE CZK DJF DKK DOP DZD EGP ERN ETB EUR FJD FKP GBP GEL GHS GIP GMD GNF GTQ GYD HKD HNL HTG HUF IDR ILS INR IQD IRR ISK JMD JOD JPY KES KGS KHR KMF KPW KRW KWD KYD KZT LAK LBP LKR LRD LSL LYD MAD MDL MGA MKD MMK MNT MOP MRU MUR MVR MWK MXN MYR MZN NAD NGN NIO NOK NPR NZD OMR PAB PEN PGK PHP PKR PLN PYG QAR RON RSD RUB RWF SAR SBD SCR SDG SEK SGD SHP SLE SOS SRD SSP STN SVC SYP SZL THB TJS TMT TND TOP TRY TTD TWD TZS UAH UGX USD UYU UZS VES VND VUV WST XAF XCD XCG XOF XPF YER ZAR ZMW ZWG""".split())
ALIASES = {"£": ("GBP", 1), "€": ("EUR", 1), "p": ("GBP", .01),
           "pence": ("GBP", .01), "GBp": ("GBP", .01)}


def finite_number(value):
    """Allow signed finite tariffs/totals, never Boolean or nonnumeric states."""
    if value is None or isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (ValueError, TypeError, OverflowError):
        return None
    return result if math.isfinite(result) else None


def normalize_rate(value, unit):
    """Return explicit currency and price per kWh; ambiguous symbols are refused."""
    number = finite_number(value)
    if number is None or not isinstance(unit, str):
        return None
    parts = unit.replace(" ", "").split("/")
    if len(parts) != 2 or parts[1] not in ("kWh", "MWh"):
        return None
    currency, factor = ALIASES.get(parts[0], (parts[0], 1))
    if currency not in CURRENCIES:
        return None
    rate = number * factor / (1000 if parts[1] == "MWh" else 1)
    return (currency, rate) if math.isfinite(rate) else None


def utc_timestamp(value):
    return isinstance(value, datetime) and value.utcoffset() == timedelta(0)


class CostEstimate:
    """Cumulative signed cost; observations never reconstruct unobserved time."""

    def __init__(self):
        self.total = 0.0
        self._baseline = None

    def restore(self, value, unit, currency):
        total = finite_number(value)
        if unit == currency and total is not None:
            self.total = total
        self._baseline = None

    def observe(self, power, rate, received, available=True):
        watts, price = finite_number(power), finite_number(rate)
        if not available or watts is None or watts < 0 or price is None or not utc_timestamp(received):
            self._baseline = None
            return
        if self._baseline is not None:
            previous_time, previous_power, previous_price = self._baseline
            seconds = (received - previous_time).total_seconds()
            if seconds < 0:
                return
            if seconds == 0:
                self._baseline = (received, watts, price)
                return
            if seconds <= MAX_INTERVAL_SECONDS:
                total = self.total + previous_power * previous_price * seconds / 3_600_000
                if math.isfinite(total):
                    self.total = total
        self._baseline = (received, watts, price)
