//+------------------------------------------------------------------+
//| DeepClawAgent.mq5                                                |
//| Deep Claw — Unified MQL5 Expert Advisor v1.0                     |
//|                                                                  |
//| Signal chain:                                                    |
//|   ATM Bot trail-flip (exec TF)                                   |
//|   → MTF Liquidity Trail gate (M5 / M15 / H1)                    |
//|   → 5-factor Confidence score ≥ threshold                       |
//|   → Position Manager (TP1 → TP2 → TP3 / Holder)                |
//|                                                                  |
//| Source systems: Claw Protocol + ADSA v7                          |
//| Broker target: Deriv MT5 (standard CTrade API)                  |
//+------------------------------------------------------------------+
#property copyright "Deep Claw"
#property version   "1.00"
#property description "Deep Claw Agent — ATM Bot + MTF Liquidity Trail + ADSA v7 Management"

#include <Trade\Trade.mqh>
#include <Trade\PositionInfo.mqh>

//=== INPUT PARAMETERS ================================================

input group "=== ATM BOT (exec TF trail-flip) ==="
input int    Inp_ATR_Period    = 1;       // ATR period (Key Factor original)
input double Inp_ATR_Mult      = 1.618;   // ATR multiplier

input group "=== MTF LIQUIDITY TRAIL GATE (M5 / M15 / H1) ==="
input bool   Inp_Use_MTF       = true;    // Enable MTF trail gate
input int    Inp_Liq_ATR_Len   = 10;      // Trail ATR period (MTF)
input double Inp_Liq_ATR_Mult  = 1.618;   // Trail ATR multiplier (MTF)
input int    Inp_MTF_Min_Align = 2;       // Min TFs aligned out of 3 to pass gate

input group "=== CONFIDENCE ENGINE ==="
input double Inp_Conf_Thresh   = 60.0;    // Min confidence % to take trade
input double Inp_W_Trail       = 1.5;     // Weight: MTF trail alignment
input double Inp_W_RSI         = 1.0;     // Weight: RSI regime
input double Inp_W_VWAP        = 1.0;     // Weight: VWAP alignment
input double Inp_W_Fib         = 0.5;     // Weight: Fibonacci/trend proxy
input double Inp_W_SMC         = 1.0;     // Weight: SMC structure
input int    Inp_RSI_Period    = 14;      // RSI period
input int    Inp_RSI_Bull_Min  = 55;      // RSI threshold for bullish regime
input int    Inp_RSI_Bear_Max  = 45;      // RSI threshold for bearish regime

input group "=== RISK MODEL ==="
input double Inp_Risk_Pct      = 1.0;     // Risk per trade (% balance)
input double Inp_SL_ATR_Mult   = 1.5;     // SL distance = ATR x this multiplier
input double Inp_TP1_R         = 1.0;     // TP1 R-multiple
input double Inp_TP2_R         = 2.0;     // TP2 R-multiple
input double Inp_TP3_R         = 3.0;     // TP3 R-multiple
input double Inp_TP1_Frac      = 0.34;    // Fraction to close at TP1
input double Inp_TP2_Frac      = 0.33;    // Fraction of original lots at TP2
input bool   Inp_BE_on_TP2     = true;    // Move SL to breakeven on TP2 hit
input int    Inp_Slippage      = 10;      // Max slippage in points
input ulong  Inp_Magic         = 202401;  // EA magic number

input group "=== JOURNAL ==="
input bool   Inp_Journal       = true;    // Write trade journal CSV

//=== CONSTANTS =======================================================

#define TRAIL_LOOKBACK  300   // bars to replay for trail state
#define JOURNAL_PREFIX  "DeepClaw_"

//=== TYPES ===========================================================

enum ENUM_PHASE {
    PHASE_NONE   = 0,
    PHASE_TP1    = 1,    // waiting for TP1
    PHASE_TP2    = 2,    // TP1 hit, waiting for TP2
    PHASE_HOLDER = 3,    // TP2 hit, trailing with exec trail (holder mode)
};

//=== GLOBAL STATE ====================================================

// Exec TF trail
double  g_exec_trail      = 0.0;
int     g_exec_trend      = 0;      // 1=bull, -1=bear, 0=uninit
int     g_prev_exec_trend = 0;

// MTF trail cache (updated per-TF bar close)
int     g_m5_trend    = 0;
int     g_m15_trend   = 0;
int     g_h1_trend    = 0;
datetime g_last_m5    = 0;
datetime g_last_m15   = 0;
datetime g_last_h1    = 0;

// Market state (refreshed each exec bar)
double  g_rsi         = 50.0;
bool    g_rsi_bull    = false;
bool    g_rsi_bear    = false;
double  g_vwap        = 0.0;
int     g_vwap_swing  = 0;    // 1=price above VWAP, -1=below
int     g_smc_bias    = 0;    // 1=bullish structure, -1=bearish, 0=neutral
double  g_atr         = 0.0;
double  g_conf_bull   = 0.0;
double  g_conf_bear   = 0.0;

// Open trade state (Position Manager owns this exclusively)
int           g_posState  = 0;        // 1=long, -1=short, 0=flat
ENUM_PHASE    g_phase     = PHASE_NONE;
ulong         g_ticket    = 0;
double        g_entry     = 0.0;
double        g_sl        = 0.0;
double        g_tp1       = 0.0;
double        g_tp2       = 0.0;
double        g_tp3       = 0.0;
double        g_init_lots = 0.0;
double        g_sl_dist   = 0.0;      // initial SL distance in price units

// New-bar tracking
datetime      g_last_bar  = 0;

// Indicator handles
int  g_h_rsi = INVALID_HANDLE;
int  g_h_atr = INVALID_HANDLE;

// Journal
int  g_jfile = INVALID_HANDLE;

CTrade g_trade;

//=== LIQUIDITY TRAIL =================================================

//+------------------------------------------------------------------+
//| Ratcheting ATR trail — ported from Python perception/            |
//| liquidity_trail.py (itself from Claw Protocol calcLiqTrail)      |
//| Input arrays must be in chronological order (oldest → newest).   |
//| Returns trend (1/-1) and current trail value.                    |
//+------------------------------------------------------------------+
void CalcLiqTrail(
    const double &C[], const double &H[], const double &L[],
    int atr_len, double atr_mult,
    int &out_trend, double &out_trail
)
{
    int n = ArraySize(C);
    if(n < atr_len + 2)
    {
        out_trend = 1;
        out_trail = (n > 0) ? C[n-1] : 0.0;
        return;
    }

    int    trend = 1;
    double trail = C[0];

    for(int i = 1; i < n; i++)
    {
        // Compute true range average over atr_len bars ending at i
        double atr_sum = 0.0;
        int    atr_cnt = 0;
        for(int j = i; j > MathMax(0, i - atr_len); j--)
        {
            double tr = MathMax(H[j] - L[j],
                        MathMax(MathAbs(H[j] - C[j-1]),
                                MathAbs(L[j] - C[j-1])));
            atr_sum += tr;
            atr_cnt++;
        }
        double local_band = (atr_cnt > 0) ? (atr_mult * atr_sum / atr_cnt) : 0.0;

        if(trend == 1)
        {
            double cand = MathMax(trail, C[i] - local_band);
            if(C[i] < cand) { trend = -1; trail = C[i] + local_band; }
            else             { trail = cand; }
        }
        else
        {
            double cand = MathMin(trail, C[i] + local_band);
            if(C[i] > cand) { trend = 1;  trail = C[i] - local_band; }
            else             { trail = cand; }
        }
    }

    out_trend = trend;
    out_trail = trail;
}

//+------------------------------------------------------------------+
//| Get trail trend for a given timeframe (replay over lookback)     |
//+------------------------------------------------------------------+
int GetTFTrailTrend(ENUM_TIMEFRAMES tf, int atr_len, double atr_mult)
{
    MqlRates rates[];
    ArraySetAsSeries(rates, false);   // oldest → newest
    int copied = CopyRates(_Symbol, tf, 0, TRAIL_LOOKBACK, rates);
    if(copied < atr_len + 2) return 0;

    double C[], H[], L[];
    ArrayResize(C, copied);
    ArrayResize(H, copied);
    ArrayResize(L, copied);
    for(int i = 0; i < copied; i++)
    {
        C[i] = rates[i].close;
        H[i] = rates[i].high;
        L[i] = rates[i].low;
    }

    int trend; double trail;
    CalcLiqTrail(C, H, L, atr_len, atr_mult, trend, trail);
    return trend;
}

//+------------------------------------------------------------------+
//| Update exec TF trail from the most recent confirmed bar          |
//+------------------------------------------------------------------+
void UpdateExecTrail()
{
    MqlRates rates[];
    ArraySetAsSeries(rates, false);
    int copied = CopyRates(_Symbol, PERIOD_CURRENT, 0, TRAIL_LOOKBACK, rates);
    if(copied < Inp_ATR_Period + 2) return;

    double C[], H[], L[];
    ArrayResize(C, copied);
    ArrayResize(H, copied);
    ArrayResize(L, copied);
    for(int i = 0; i < copied; i++)
    {
        C[i] = rates[i].close;
        H[i] = rates[i].high;
        L[i] = rates[i].low;
    }

    g_prev_exec_trend = g_exec_trend;
    CalcLiqTrail(C, H, L, Inp_ATR_Period, Inp_ATR_Mult, g_exec_trend, g_exec_trail);
}

//+------------------------------------------------------------------+
//| Update MTF trails — only recomputes when the TF bar has closed   |
//+------------------------------------------------------------------+
void UpdateMTFTrails()
{
    datetime t[1];
    if(CopyTime(_Symbol, PERIOD_M5, 0, 1, t) == 1 && t[0] != g_last_m5)
    {
        g_m5_trend = GetTFTrailTrend(PERIOD_M5, Inp_Liq_ATR_Len, Inp_Liq_ATR_Mult);
        g_last_m5  = t[0];
    }
    if(CopyTime(_Symbol, PERIOD_M15, 0, 1, t) == 1 && t[0] != g_last_m15)
    {
        g_m15_trend = GetTFTrailTrend(PERIOD_M15, Inp_Liq_ATR_Len, Inp_Liq_ATR_Mult);
        g_last_m15  = t[0];
    }
    if(CopyTime(_Symbol, PERIOD_H1, 0, 1, t) == 1 && t[0] != g_last_h1)
    {
        g_h1_trend = GetTFTrailTrend(PERIOD_H1, Inp_Liq_ATR_Len, Inp_Liq_ATR_Mult);
        g_last_h1  = t[0];
    }
}

//=== MARKET INTELLIGENCE =============================================

void UpdateRSI()
{
    double buf[1];
    if(CopyBuffer(g_h_rsi, 0, 1, 1, buf) == 1)
    {
        g_rsi      = buf[0];
        g_rsi_bull = (g_rsi >= Inp_RSI_Bull_Min);
        g_rsi_bear = (g_rsi <= Inp_RSI_Bear_Max);
    }
}

void UpdateATR()
{
    double buf[1];
    if(CopyBuffer(g_h_atr, 0, 1, 1, buf) == 1)
        g_atr = buf[0];
}

void UpdateVWAP()
{
    // Session VWAP anchored to today's day open
    datetime day_open = iTime(_Symbol, PERIOD_D1, 0);
    int bars = Bars(_Symbol, PERIOD_CURRENT, day_open, TimeCurrent());
    if(bars < 1) bars = 1;

    MqlRates rates[];
    ArraySetAsSeries(rates, true);
    int copied = CopyRates(_Symbol, PERIOD_CURRENT, 0, bars, rates);
    if(copied < 1) { g_vwap = 0; g_vwap_swing = 0; return; }

    double cum_tpv = 0, cum_vol = 0;
    for(int i = 0; i < copied; i++)
    {
        double tp  = (rates[i].high + rates[i].low + rates[i].close) / 3.0;
        double vol = (double)rates[i].tick_volume;
        cum_tpv += tp * vol;
        cum_vol += vol;
    }
    if(cum_vol > 0) g_vwap = cum_tpv / cum_vol;
    else            g_vwap = iClose(_Symbol, PERIOD_CURRENT, 1);

    double close     = iClose(_Symbol, PERIOD_CURRENT, 1);
    g_vwap_swing = (close > g_vwap) ? 1 : -1;
}

void UpdateSMC()
{
    // Simplified structure bias: recent 25-bar trend vs prior 25-bar trend
    MqlRates rates[];
    ArraySetAsSeries(rates, true);
    int copied = CopyRates(_Symbol, PERIOD_CURRENT, 1, 50, rates);
    if(copied < 30) { g_smc_bias = 0; return; }

    double recent_open  = rates[24].close;
    double recent_close = rates[0].close;

    // Directional bias from close trajectory
    double move = recent_close - recent_open;
    double threshold = g_atr * 0.5;

    if(move >  threshold)  g_smc_bias =  1;
    else if(move < -threshold) g_smc_bias = -1;
    else                   g_smc_bias =  0;
}

//=== CONFIDENCE ENGINE ===============================================

//+------------------------------------------------------------------+
//| 5-factor weighted confidence score (0-100) for given direction   |
//| Mirrors cognition/confidence_v1.py                               |
//+------------------------------------------------------------------+
double ComputeConfidence(int direction)
{
    double total_w = Inp_W_Trail + Inp_W_RSI + Inp_W_VWAP + Inp_W_Fib + Inp_W_SMC;

    // 1. MTF trail alignment
    double trail_f = (g_exec_trend == direction) ? 1.0 : 0.0;
    if(trail_f > 0.0)
    {
        if(g_m5_trend  == direction) trail_f = MathMin(1.0, trail_f + 0.3);
        if(g_m15_trend == direction) trail_f = MathMin(1.0, trail_f + 0.3);
        if(g_h1_trend  == direction) trail_f = MathMin(1.0, trail_f + 0.2);
    }

    // 2. RSI regime
    double rsi_f;
    if(direction ==  1) rsi_f = g_rsi_bull ? 1.0 : (g_rsi < 35 ? 0.5 : 0.0);
    else                rsi_f = g_rsi_bear ? 1.0 : (g_rsi > 65 ? 0.5 : 0.0);

    // 3. VWAP
    double vwap_f = (g_vwap_swing == direction) ? 1.0 : 0.0;

    // 4. Fibonacci proxy (using VWAP alignment + SMC agreement)
    double fib_f = (vwap_f > 0 && g_smc_bias == direction) ? 1.0 :
                   (vwap_f > 0 || g_smc_bias == direction) ? 0.5 : 0.0;

    // 5. SMC structure
    double smc_f;
    if(g_smc_bias == direction)  smc_f = 0.8;
    else if(g_smc_bias == 0)     smc_f = 0.3;
    else                          smc_f = 0.0;

    double raw = (trail_f * Inp_W_Trail +
                  rsi_f   * Inp_W_RSI   +
                  vwap_f  * Inp_W_VWAP  +
                  fib_f   * Inp_W_Fib   +
                  smc_f   * Inp_W_SMC);

    return (total_w > 0.0) ? (raw / total_w) * 100.0 : 0.0;
}

//=== SIGNAL GENERATOR ================================================

//+------------------------------------------------------------------+
//| ATM Bot: detects exec trail flip on the confirmed bar close      |
//| Returns 1=buy, -1=sell, 0=no signal                             |
//+------------------------------------------------------------------+
int GetATMBotSignal()
{
    // Need a valid previous trend to compare against
    if(g_prev_exec_trend == 0 || g_exec_trend == 0) return 0;

    // Flip must have just happened
    if(g_exec_trend == g_prev_exec_trend) return 0;

    // Confirm: confirmed bar close is on the correct side of the trail
    double close = iClose(_Symbol, PERIOD_CURRENT, 1);
    if(g_exec_trend ==  1 && close <= g_exec_trail) return 0;
    if(g_exec_trend == -1 && close >= g_exec_trail) return 0;

    return g_exec_trend;
}

//=== RISK MODEL ======================================================

double ComputeLots(double sl_dist)
{
    if(sl_dist <= 0) return 0.0;

    double balance   = AccountInfoDouble(ACCOUNT_BALANCE);
    double risk_usd  = balance * (Inp_Risk_Pct / 100.0);
    double tick_sz   = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
    double tick_val  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
    double min_lot   = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
    double max_lot   = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
    double lot_step  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);

    if(tick_sz <= 0 || tick_val <= 0) return min_lot;

    double ticks_risk = sl_dist / tick_sz;
    double usd_per_lot = ticks_risk * tick_val;
    if(usd_per_lot <= 0) return min_lot;

    double lots = risk_usd / usd_per_lot;
    lots = MathFloor(lots / lot_step) * lot_step;
    return MathMax(min_lot, MathMin(max_lot, lots));
}

//=== TRADE EXECUTION =================================================

void OpenTrade(int direction)
{
    if(g_atr <= 0) return;

    double sl_dist = g_atr * Inp_SL_ATR_Mult;

    // Minimum stop distance check
    double min_stop = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL)
                      * SymbolInfoDouble(_Symbol, SYMBOL_POINT);
    if(sl_dist < min_stop * 1.1) sl_dist = min_stop * 1.1;

    double lots = ComputeLots(sl_dist);
    if(lots <= 0) { Print("OpenTrade: invalid lot size"); return; }

    double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
    double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
    int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);

    double entry, sl, tp1, tp2, tp3;
    if(direction == 1)
    {
        entry = ask;
        sl    = NormalizeDouble(entry - sl_dist,             digits);
        tp1   = NormalizeDouble(entry + sl_dist * Inp_TP1_R, digits);
        tp2   = NormalizeDouble(entry + sl_dist * Inp_TP2_R, digits);
        tp3   = NormalizeDouble(entry + sl_dist * Inp_TP3_R, digits);
    }
    else
    {
        entry = bid;
        sl    = NormalizeDouble(entry + sl_dist,             digits);
        tp1   = NormalizeDouble(entry - sl_dist * Inp_TP1_R, digits);
        tp2   = NormalizeDouble(entry - sl_dist * Inp_TP2_R, digits);
        tp3   = NormalizeDouble(entry - sl_dist * Inp_TP3_R, digits);
    }

    bool ok;
    if(direction == 1)
        ok = g_trade.Buy(lots, _Symbol, 0, sl, tp3, "DeepClaw");
    else
        ok = g_trade.Sell(lots, _Symbol, 0, sl, tp3, "DeepClaw");

    if(!ok)
    {
        Print("OpenTrade FAILED: ", g_trade.ResultRetcodeDescription(),
              " (", g_trade.ResultRetcode(), ")");
        return;
    }

    // ResultPosition() returns the position ticket (hedge mode safe, build 1085+)
    g_ticket    = g_trade.ResultPosition();
    if(g_ticket == 0) g_ticket = g_trade.ResultOrder();  // fallback for netting
    g_posState  = direction;
    g_phase     = PHASE_TP1;
    g_entry     = g_trade.ResultPrice();
    g_sl        = sl;
    g_tp1       = tp1;
    g_tp2       = tp2;
    g_tp3       = tp3;
    g_init_lots = lots;
    g_sl_dist   = sl_dist;

    PrintFormat("TRADE OPEN [%s] Entry=%.5f SL=%.5f TP1=%.5f TP2=%.5f TP3=%.5f Lots=%.2f Conf=%.1f%%",
        (direction == 1 ? "LONG" : "SHORT"),
        g_entry, g_sl, g_tp1, g_tp2, g_tp3, g_init_lots,
        (direction == 1 ? g_conf_bull : g_conf_bear));
}

bool DoPartialClose(double frac_of_current)
{
    if(!PositionSelectByTicket(g_ticket)) return false;
    double lots     = PositionGetDouble(POSITION_VOLUME);
    double lot_step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
    double min_lot  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
    double close_v  = MathFloor(lots * frac_of_current / lot_step) * lot_step;
    close_v = MathMax(min_lot, close_v);
    if(close_v >= lots) close_v = lots;
    return g_trade.PositionClosePartial(g_ticket, close_v, Inp_Slippage);
}

bool DoModifySL(double new_sl)
{
    if(!PositionSelectByTicket(g_ticket)) return false;
    double tp = PositionGetDouble(POSITION_TP);
    return g_trade.PositionModify(g_ticket, new_sl, tp);
}

bool IsPositionAlive()
{
    return (g_ticket > 0 && PositionSelectByTicket(g_ticket));
}

//=== POSITION MANAGER ================================================

//+------------------------------------------------------------------+
//| Runs on every tick while g_posState != 0                        |
//| Single owner of g_posState / g_phase / g_sl transitions         |
//+------------------------------------------------------------------+
void RunPositionManager()
{
    if(!IsPositionAlive())
    {
        // Position was closed by broker (SL or TP3 hit or manual)
        double exit_px = iClose(_Symbol, PERIOD_CURRENT, 1);
        double r = (g_posState == 1)
                   ? (exit_px - g_entry) / g_sl_dist
                   : (g_entry - exit_px) / g_sl_dist;

        // Determine exit reason from exit price proximity to known levels
        string reason;
        double tol = g_atr * 0.3;   // within 0.3 ATR = level hit
        bool at_tp3 = (g_posState ==  1) ? (exit_px >= g_tp3 - tol) : (exit_px <= g_tp3 + tol);
        bool at_sl  = (g_posState ==  1) ? (exit_px <= g_sl  + tol) : (exit_px >= g_sl  - tol);

        if(g_phase == PHASE_TP1)
            reason = at_tp3 ? "TP3" : "SL";
        else if(g_phase == PHASE_TP2)
            reason = at_tp3 ? "TP3" : "TP1_THEN_SL";
        else   // HOLDER
            reason = at_tp3 ? "TP3" : "TP2_THEN_HOLDER_EXIT";
        WriteJournal(reason, exit_px, r);
        PrintFormat("TRADE CLOSED [%s] Phase=%d Exit=%.5f R=%.2f",
            (g_posState == 1 ? "LONG" : "SHORT"), (int)g_phase, exit_px, r);

        g_posState = 0;
        g_phase    = PHASE_NONE;
        g_ticket   = 0;
        return;
    }

    double bid     = SymbolInfoDouble(_Symbol, SYMBOL_BID);
    double ask     = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
    double cur_px  = (g_posState == 1) ? bid : ask;
    int digits     = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);

    if(g_phase == PHASE_TP1)
    {
        bool hit = (g_posState == 1) ? (cur_px >= g_tp1) : (cur_px <= g_tp1);
        if(hit)
        {
            if(DoPartialClose(Inp_TP1_Frac))
            {
                g_phase = PHASE_TP2;
                Print("TP1 HIT — partial close ", (Inp_TP1_Frac * 100), "%  Phase→TP2");
            }
        }
    }
    else if(g_phase == PHASE_TP2)
    {
        bool hit = (g_posState == 1) ? (cur_px >= g_tp2) : (cur_px <= g_tp2);
        if(hit)
        {
            // Close Inp_TP2_Frac of ORIGINAL lots = (Inp_TP2_Frac / (1 - Inp_TP1_Frac)) of current lots
            double frac_of_remaining = Inp_TP2_Frac / MathMax(0.01, 1.0 - Inp_TP1_Frac);
            DoPartialClose(frac_of_remaining);

            if(Inp_BE_on_TP2)
            {
                // Breakeven + 0.1 ATR buffer (ensures we lock a few pips)
                double be = (g_posState == 1)
                            ? NormalizeDouble(g_entry + g_atr * 0.1, digits)
                            : NormalizeDouble(g_entry - g_atr * 0.1, digits);
                if(DoModifySL(be)) g_sl = be;
            }

            g_phase = PHASE_HOLDER;
            Print("TP2 HIT — SL → breakeven  Phase→HOLDER");
        }
    }
    else if(g_phase == PHASE_HOLDER)
    {
        // Holder mode: trail SL with exec trail to protect remaining profit
        // TP3 is set on broker order as hard limit; we also trail upward
        double holder_sl;
        if(g_posState == 1)
            holder_sl = NormalizeDouble(MathMax(g_sl, g_exec_trail), digits);
        else
            holder_sl = NormalizeDouble(MathMin(g_sl, g_exec_trail), digits);

        if(holder_sl != g_sl)
        {
            if(DoModifySL(holder_sl)) g_sl = holder_sl;
        }
    }
}

//=== JOURNAL =========================================================

void WriteJournal(string exit_reason, double exit_px, double r)
{
    if(!Inp_Journal || g_jfile == INVALID_HANDLE) return;
    string line = StringFormat(
        "%s,%s,%s,%s,%.5f,%.5f,%.5f,%.5f,%.5f,%.5f,%.2f,%.4f,%.2f\n",
        TimeToString(TimeCurrent(), TIME_DATE|TIME_MINUTES),
        _Symbol,
        (g_posState == 1 ? "LONG" : "SHORT"),
        exit_reason,
        g_entry, g_sl, g_tp1, g_tp2, g_tp3,
        exit_px,
        g_init_lots,
        g_sl_dist,
        r
    );
    FileWriteString(g_jfile, line);
    FileFlush(g_jfile);
}

//=== DASHBOARD =======================================================

void RenderDashboard()
{
    string state_s  = (g_posState ==  1) ? "LONG"  :
                      (g_posState == -1) ? "SHORT" : "FLAT";
    string phase_s  = (g_phase == PHASE_TP1)    ? "TP1 PENDING" :
                      (g_phase == PHASE_TP2)    ? "TP2 PENDING" :
                      (g_phase == PHASE_HOLDER) ? "HOLDER MODE" : "WAITING";
    string m5_s     = (g_m5_trend  ==  1) ? "↑" : (g_m5_trend  == -1) ? "↓" : "?";
    string m15_s    = (g_m15_trend ==  1) ? "↑" : (g_m15_trend == -1) ? "↓" : "?";
    string h1_s     = (g_h1_trend  ==  1) ? "↑" : (g_h1_trend  == -1) ? "↓" : "?";
    string exec_s   = (g_exec_trend == 1) ? "↑ BULL" : "↓ BEAR";

    Comment(StringFormat(
        "━━━ DEEP CLAW AGENT ━━━━━━━━━━━━━━━\n"
        "  STATE:  %-8s  PHASE: %s\n"
        "━━━ LIQUIDITY TRAIL ━━━━━━━━━━━━━━━\n"
        "  EXEC:   %-8s  trail=%.5f\n"
        "  M5:     %s   M15: %s   H1: %s\n"
        "━━━ MARKET STATE ━━━━━━━━━━━━━━━━━━\n"
        "  RSI:    %.1f  (%s)\n"
        "  VWAP:   %.5f  price %s\n"
        "  SMC:    %s\n"
        "  CONF:   ▲%.0f%%  ▼%.0f%%  threshold=%.0f%%\n"
        "━━━ OPEN TRADE ━━━━━━━━━━━━━━━━━━━━\n"
        "  Entry:  %.5f   SL: %.5f\n"
        "  TP1:    %.5f  TP2: %.5f\n"
        "  TP3:    %.5f  Lots: %.2f\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        state_s, phase_s,
        exec_s, g_exec_trail,
        m5_s, m15_s, h1_s,
        g_rsi, (g_rsi_bull ? "BULL" : (g_rsi_bear ? "BEAR" : "NEUT")),
        g_vwap, (g_vwap_swing ==  1 ? "ABOVE" : "BELOW"),
        (g_smc_bias ==  1 ? "BULLISH" : (g_smc_bias == -1 ? "BEARISH" : "NEUTRAL")),
        g_conf_bull, g_conf_bear, Inp_Conf_Thresh,
        g_entry, g_sl, g_tp1, g_tp2, g_tp3, g_init_lots
    ));
}

//=== EA LIFECYCLE ====================================================

int OnInit()
{
    g_trade.SetExpertMagicNumber(Inp_Magic);
    g_trade.SetDeviationInPoints(Inp_Slippage);
    g_trade.SetTypeFilling(ORDER_FILLING_RETURN);

    g_h_rsi = iRSI(_Symbol, PERIOD_CURRENT, Inp_RSI_Period, PRICE_CLOSE);
    g_h_atr = iATR(_Symbol, PERIOD_CURRENT, Inp_ATR_Period);

    if(g_h_rsi == INVALID_HANDLE || g_h_atr == INVALID_HANDLE)
    {
        Print("ERROR: indicator handle creation failed");
        return INIT_FAILED;
    }

    // Journal file
    if(Inp_Journal)
    {
        string fname = JOURNAL_PREFIX + _Symbol + "_journal.csv";
        g_jfile = FileOpen(fname, FILE_WRITE|FILE_SHARE_READ|FILE_CSV|FILE_ANSI, ',');
        if(g_jfile != INVALID_HANDLE)
            FileWriteString(g_jfile,
                "time,symbol,direction,exit_reason,entry,sl,tp1,tp2,tp3,"
                "exit_price,lots,sl_dist,r_multiple\n");
    }

    // Warm up MTF trails immediately
    g_m5_trend  = GetTFTrailTrend(PERIOD_M5,  Inp_Liq_ATR_Len, Inp_Liq_ATR_Mult);
    g_m15_trend = GetTFTrailTrend(PERIOD_M15, Inp_Liq_ATR_Len, Inp_Liq_ATR_Mult);
    g_h1_trend  = GetTFTrailTrend(PERIOD_H1,  Inp_Liq_ATR_Len, Inp_Liq_ATR_Mult);

    datetime t[1];
    if(CopyTime(_Symbol, PERIOD_M5,  0, 1, t) == 1) g_last_m5  = t[0];
    if(CopyTime(_Symbol, PERIOD_M15, 0, 1, t) == 1) g_last_m15 = t[0];
    if(CopyTime(_Symbol, PERIOD_H1,  0, 1, t) == 1) g_last_h1  = t[0];

    PrintFormat("Deep Claw Agent INIT — %s  Magic=%u  ConfThresh=%.0f%%  MTFMin=%d",
        _Symbol, Inp_Magic, Inp_Conf_Thresh, Inp_MTF_Min_Align);
    return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
    if(g_h_rsi != INVALID_HANDLE) IndicatorRelease(g_h_rsi);
    if(g_h_atr != INVALID_HANDLE) IndicatorRelease(g_h_atr);
    if(g_jfile != INVALID_HANDLE) FileClose(g_jfile);
    Comment("");
    PrintFormat("Deep Claw Agent DEINIT — reason=%d", reason);
}

void OnTick()
{
    // ── Every tick: trade management ────────────────────────────────
    if(g_posState != 0) RunPositionManager();

    // ── New-bar logic (confirmed candles only) ───────────────────────
    datetime cur_bar = iTime(_Symbol, PERIOD_CURRENT, 0);
    if(cur_bar != g_last_bar)
    {
        g_last_bar = cur_bar;

        // 1. Update perception
        UpdateExecTrail();
        UpdateMTFTrails();
        UpdateRSI();
        UpdateATR();
        UpdateVWAP();
        UpdateSMC();

        // 2. Compute confidence
        g_conf_bull = ComputeConfidence( 1);
        g_conf_bear = ComputeConfidence(-1);

        // 3. Signal evaluation — only when flat
        if(g_posState == 0)
        {
            int signal = GetATMBotSignal();
            if(signal != 0)
            {
                bool mtf_ok   = true;
                bool conf_ok  = false;

                if(Inp_Use_MTF)
                    mtf_ok = (CountMTFAligned(signal) >= Inp_MTF_Min_Align);

                double conf = (signal == 1) ? g_conf_bull : g_conf_bear;
                conf_ok = (conf >= Inp_Conf_Thresh);

                if(mtf_ok && conf_ok)
                {
                    OpenTrade(signal);
                }
                else
                {
                    // Shadow candidate log (feeds journal for future ML)
                    string reject_reason = !mtf_ok ? "MTF_GATE"    :
                                           !conf_ok ? "CONFIDENCE"  : "UNKNOWN";
                    PrintFormat("Signal BLOCKED [%s] Conf=%.1f%% MTF_OK=%s Reason=%s",
                        (signal == 1 ? "LONG" : "SHORT"),
                        (signal == 1 ? g_conf_bull : g_conf_bear),
                        (mtf_ok ? "Y" : "N"),
                        reject_reason);
                }
            }
        }
    }

    // ── Dashboard (every tick) ───────────────────────────────────────
    RenderDashboard();
}

//+------------------------------------------------------------------+
//| Helper: count how many of M5/M15/H1 trail agrees with direction |
//+------------------------------------------------------------------+
int CountMTFAligned(int direction)
{
    return (int)(g_m5_trend == direction) +
           (int)(g_m15_trend == direction) +
           (int)(g_h1_trend  == direction);
}
