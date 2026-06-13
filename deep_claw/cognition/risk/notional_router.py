"""
Asset Notional Router — critical bug-fixed logic from cheatsheet §2.5.
Port EXACTLY. This is the one piece of v6.1/v7 that was unambiguously correct.

The instrument registry is the single source of truth — never hardcode
forex/crypto/futures assumptions outside this module.
"""
from __future__ import annotations

import yaml
from functools import lru_cache
from pathlib import Path

from deep_claw.core.types import AssetClass, Instrument, Venue


_REGISTRY_PATH = Path(__file__).parent.parent.parent / "config" / "instrument_registry.yaml"


@lru_cache(maxsize=1)
def _load_registry() -> dict[str, Instrument]:
    with open(_REGISTRY_PATH) as f:
        data = yaml.safe_load(f)
    registry: dict[str, Instrument] = {}
    for item in data["instruments"]:
        inst = Instrument(
            symbol=item["symbol"],
            deriv_code=item.get("deriv_code"),
            bybit_symbol=item.get("bybit_symbol"),
            mt5_symbol=item.get("mt5_symbol"),
            asset_class=AssetClass(item["asset_class"]),
            pip_size=item["pip_size"],
            contract_notional=item["contract_notional"],
            min_unit=item["min_unit"],
            session_profile=item["session_profile"],
            preferred_venue=Venue(item["preferred_venue"]),
            point_value=item.get("point_value"),
        )
        registry[inst.symbol] = inst
    return registry


def get_instrument(symbol: str) -> Instrument:
    registry = _load_registry()
    if symbol not in registry:
        raise KeyError(f"Symbol '{symbol}' not found in instrument registry. Add it to instrument_registry.yaml.")
    return registry[symbol]


def get_contract_notional(symbol: str) -> float:
    """
    Returns notional value per base unit for position sizing.
    Exact port of Pine's _get_contract_notional (cheatsheet §2.5).

    forex:    100,000 (standard lot)
    crypto:   1.0 (qty in base asset)
    futures:  point_value (or 1.0 fallback — logged as a warning)
    synthetic: 1.0 (Deriv synthetics behave like crypto-notional)
    """
    inst = get_instrument(symbol)
    return inst.contract_notional


def get_pip_size(symbol: str) -> float:
    return get_instrument(symbol).pip_size


def get_position_size(
    symbol: str,
    sl_distance: float,
    risk_per_trade_usd: float,
) -> float:
    """
    Exact port of Pine's _get_position_size (cheatsheet §2.5):
    size = risk_per_trade / (sl_distance * contract_notional)
    Rounded to 4 decimal places.

    sl_distance is in price units (not pips).
    """
    notional = get_contract_notional(symbol)
    if sl_distance <= 0 or notional <= 0:
        return 0.0
    size = risk_per_trade_usd / (sl_distance * notional)
    return round(size, 4)


def get_live_pnl(
    symbol: str,
    entry: float,
    current: float,
    direction: int,   # 1 = long, -1 = short
    pos_size: float,
) -> float:
    """
    Exact port of Pine's live_pnl formula (cheatsheet §2.5).
    pnl = (current - entry) * direction * pos_size * notional
    """
    notional = get_contract_notional(symbol)
    diff = (current - entry) * direction
    return diff * pos_size * notional


def pips_to_price(symbol: str, pips: float) -> float:
    return pips * get_pip_size(symbol)


def price_to_pips(symbol: str, price_distance: float) -> float:
    pip_size = get_pip_size(symbol)
    if pip_size == 0:
        return 0.0
    return price_distance / pip_size
