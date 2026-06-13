"""
Position Sizer — four-clamp Kelly formula (cheatsheet §7.5).

Every clamp's binding/non-binding status is logged — this gives the ML layer
visibility into when sizing was constrained by something other than edge.
"""
from __future__ import annotations

from deep_claw.core.types import SizingResult
from deep_claw.cognition.risk.notional_router import get_position_size


def compute_size(
    symbol: str,
    sl_distance: float,          # in price units
    confidence: float,           # 0-100, from ConfidenceResult
    equity: float,               # current account equity in USD
    risk_per_trade_usd: float,   # base risk amount
    max_equity_pct: float = 0.02,
    daily_loss_budget_remaining: float | None = None,
    margin_headroom_usd: float | None = None,
    use_kelly: bool = True,
) -> SizingResult:
    """
    Computes final position size applying four clamps in order.
    Returns SizingResult with each clamp's value and which one was binding.

    Kelly fraction: f = (confidence/100) * max_kelly_cap
    where max_kelly_cap = 0.25 (never more than 25% Kelly even at 100% confidence).
    """
    # Kelly fraction from confidence
    max_kelly_cap = 0.25
    kelly_fraction = (confidence / 100.0) * max_kelly_cap if use_kelly else 1.0
    kelly_size_usd = kelly_fraction * equity

    # Base size from risk model (sl-based)
    base_size = get_position_size(symbol, sl_distance, risk_per_trade_usd)

    # Clamp 1: Kelly-implied USD risk ceiling
    kelly_implied_risk = kelly_size_usd  # dollar risk, not units

    # Clamp 2: Hard 1-2% equity ceiling
    pct_cap_usd = max_equity_pct * equity

    # Clamp 3: Daily loss budget (funded accounts / MT5)
    daily_cap_usd = daily_loss_budget_remaining if daily_loss_budget_remaining is not None else float("inf")

    # Clamp 4: Margin headroom
    margin_cap_usd = margin_headroom_usd if margin_headroom_usd is not None else float("inf")

    # Apply clamps to USD risk amount
    effective_risk_usd = min(
        risk_per_trade_usd,
        kelly_implied_risk,
        pct_cap_usd,
        daily_cap_usd,
        margin_cap_usd,
    )

    # Convert back to position size units
    from deep_claw.cognition.risk.notional_router import get_contract_notional
    notional = get_contract_notional(symbol)
    if sl_distance > 0 and notional > 0:
        final_size = round(effective_risk_usd / (sl_distance * notional), 4)
    else:
        final_size = 0.0

    # Determine binding clamp
    candidates = {
        "kelly": kelly_implied_risk,
        "pct": pct_cap_usd,
        "daily_loss": daily_cap_usd if daily_loss_budget_remaining is not None else float("inf"),
        "margin": margin_cap_usd if margin_headroom_usd is not None else float("inf"),
    }
    binding = min(candidates, key=lambda k: candidates[k])
    if candidates[binding] >= risk_per_trade_usd:
        binding = "none"

    return SizingResult(
        final_size=final_size,
        kelly_size=round(kelly_implied_risk / (sl_distance * notional), 4) if sl_distance > 0 and notional > 0 else 0.0,
        pct_equity_cap=round(pct_cap_usd / (sl_distance * notional), 4) if sl_distance > 0 and notional > 0 else 0.0,
        daily_loss_cap=round(daily_cap_usd / (sl_distance * notional), 4) if daily_loss_budget_remaining is not None and sl_distance > 0 and notional > 0 else None,
        margin_cap=round(margin_cap_usd / (sl_distance * notional), 4) if margin_headroom_usd is not None and sl_distance > 0 and notional > 0 else None,
        binding_clamp=binding,
        kelly_fraction=kelly_fraction,
        equity=equity,
    )
