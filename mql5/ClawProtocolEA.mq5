//+------------------------------------------------------------------+
//| ClawProtocolEA.mq5 — Phase 1: Signal Validation (Print Only)   |
//|                                                                  |
//| Full port of THE CLAW PROTOCOL from Pine Script v6.             |
//| Phase 1: Zero OrderSend. Print() to Experts log only.           |
//| Goal: final_long / final_short match Pine output bar-for-bar.   |
//|                                                                  |
//| Architecture (mirrors Pine STEP order):                         |
//|  Module 2: calcLiqTrail — exec/M5/M15/H1 (EMA-centered, exact) |
//|  Module 3: ATM Bot — dual trails + crossover trigger            |
//|  Module 4: RSI Smart Signal + M5 confirm + sustain              |
//|  Module 5: Market Structure — pivot HH/HL/LH/LL + BOS          |
//|  Module 6: Fib Bands — double-EMA of HLC3                      |
//|  Module 7: VWAP Direction — highestbars/lowestbars anchor       |
//|  Module 8: Volume Profile — placeholder (Phase 3)               |
//|  Module 9: Confidence Engine — 6-factor weighted                |
//|  Module 10: Gate Chain → final_long / final_short               |
//+------------------------------------------------------------------+
#property copyright "Deep Claw"
#property version   "1.0"
#property strict

//==========================================================================
// INPUTS (match Pine defaults exactly)
//==========================================================================

// MTF Trail
input int    Inp_MA_Len       = 200;    // MA Length (EMA center for trail)
input int    Inp_ATR_Len      = 14;     // ATR Length (trail)
input double Inp_ATR_Mult     = 1.25;   // Trail Distance (ATR multiplier)

// ATM Bot
input double Inp_A_Buy        = 3.5;    // Buy Sensitivity
input int    Inp_C_Buy        = 2;      // Buy ATR Period
input double Inp_A_Sell       = 3.5;    // Sell Sensitivity
input int    Inp_C_Sell       = 2;      // Sell ATR Period

// Structure
input int    Inp_SwingSize    = 15;     // Pivot lookback/rightbars

// RSI Momentum
input int    Inp_RSI_Len      = 14;     // RSI Length
input int    Inp_RSI_EMA_Len  = 5;      // Momentum EMA Length
input int    Inp_PMom         = 50;     // Positive momentum threshold
input int    Inp_NMom         = 50;     // Negative momentum threshold
input bool   Inp_Sustain      = true;   // Sustain momentum state
input bool   Inp_UseM5Confirm = true;   // M5 RSI confirmation

// VWAP
input int    Inp_VWAP_Prd     = 100;    // Swing period for direction

// Fib Bands
input int    Inp_Fib_Len      = 50;     // Double-EMA length

// Confidence Engine
input string Inp_ClawMode     = "Moderate"; // Conservative/Moderate/Aggressive
input double Inp_MTF_W        = 1.5;    // MTF trail weight
input double Inp_Struct_W     = 1.0;    // Structure weight
input double Inp_RSI_W        = 1.0;    // RSI weight
input double Inp_VWAP_W       = 1.0;    // VWAP weight
input double Inp_Fib_W        = 0.5;    // Fib weight (active if RequireFib)
input bool   Inp_RequireFib   = false;  // Include Fib factor in score

//==========================================================================
// MODULE 1: GLOBAL STATE
//==========================================================================
#define WARMUP_BARS 700

// MTF Trail states (exec / M5 / M15 / H1)
int    g_ltf_trend  = 1;  double g_ltf_trail  = 0.0;
int    g_m5_trend   = 1;  double g_m5_trail   = 0.0;
int    g_m15_trend  = 1;  double g_m15_trail  = 0.0;
int    g_h1_trend   = 1;  double g_h1_trail   = 0.0;

// ATM Bot dual trails
double g_trail_buy  = 0.0;
double g_trail_sell = 0.0;
double g_prev_close_atm  = 0.0;  // close[1] for crossover detection
double g_prev_trail_buy  = 0.0;
double g_prev_trail_sell = 0.0;

// RSI momentum states (var bool in Pine — persistent)
bool   g_positive    = false;
bool   g_negative    = false;
bool   g_positive_m5 = false;
bool   g_negative_m5 = false;
double g_ema5_prev   = 0.0;   // EMA5(close) on exec TF, previous bar
double g_ema5_m5_prev = 0.0;  // EMA5(close) on M5, previous bar
bool   g_smart_bull      = false;
bool   g_smart_bear      = false;
bool   g_prev_smart_bull = false;
bool   g_prev_smart_bear = false;

// Structure (SMC)
double g_prev_high     = 0.0;
double g_prev_low      = 0.0;
bool   g_high_active   = false;
bool   g_low_active    = false;
int    g_struct_bias   = 0;   // 1 bull, -1 bear, 0 neutral

// Fib Bands (double EMA of HLC3)
double g_fib_ema1   = 0.0;   // first EMA pass
double g_fib_ema2   = 0.0;   // basis = EMA(ema1)
double g_fib_basis_prev = 0.0;
int    g_trend_fib  = 0;     // 1 bull, -1 bear

// VWAP direction
long   g_vwap_phL   = 0;     // bar index of most recent highest high (prd bars)
long   g_vwap_plL   = 0;     // bar index of most recent lowest  low  (prd bars)
int    g_last_swing = 0;     // 1 bull, -1 bear (updates only on dir change)
int    g_dir_vwap   = 0;     // current VWAP direction
int    g_prev_dir_vwap = 0;  // for detecting direction change
long   g_bar_count  = 0;     // running bar index (mimics Pine's bar_index)

// MTF bar-change detection
datetime g_last_bar_time  = 0;
datetime g_last_m5_time   = 0;
datetime g_last_m15_time  = 0;
datetime g_last_h1_time   = 0;

// Indicator handles
int g_h_ema_exec  = INVALID_HANDLE;  // EMA(200) exec TF — for calcLiqTrail
int g_h_atr_exec  = INVALID_HANDLE;  // ATR(14)  exec TF
int g_h_ema_m5    = INVALID_HANDLE;
int g_h_atr_m5    = INVALID_HANDLE;
int g_h_ema_m15   = INVALID_HANDLE;
int g_h_atr_m15   = INVALID_HANDLE;
int g_h_ema_h1    = INVALID_HANDLE;
int g_h_atr_h1    = INVALID_HANDLE;
int g_h_atr_atm   = INVALID_HANDLE;  // ATR(2) exec TF — for ATM Bot
int g_h_rsi_exec  = INVALID_HANDLE;  // RSI(14) exec TF
int g_h_rsi_m5    = INVALID_HANDLE;  // RSI(14) M5 TF
int g_h_ema5_exec = INVALID_HANDLE;  // EMA(5) exec TF — change_ema5
int g_h_ema5_m5   = INVALID_HANDLE;  // EMA(5) M5   TF

//==========================================================================
// MODULE 2 HELPERS: calcLiqTrail (EMA-centered — exact Pine formula)
//==========================================================================

// Single-step update of a trail ratchet.
// Pine: raw_up = EMA(close,mlen) - ATR(alen)*amult  (floor)
//       raw_dn = EMA(close,mlen) + ATR(alen)*amult  (ceiling)
void StepLiqTrail(double ema_val, double atr_val, double amult, double close_val,
                  int &trend, double &trail)
{
   double raw_up = ema_val - atr_val * amult;
   double raw_dn = ema_val + atr_val * amult;
   if(trend == 1) {
      double new_t = MathMax(raw_up, trail);
      if(close_val < new_t) { trend = -1; trail = raw_dn; }
      else                   { trail = new_t; }
   } else {
      double new_t = MathMin(raw_dn, trail);
      if(close_val > new_t) { trend = 1; trail = raw_up; }
      else                   { trail = new_t; }
   }
}

// Warm up trail state by replaying WARMUP_BARS of history.
// ema_arr and atr_arr must be oldest-first (index 0 = oldest bar).
void WarmupLiqTrail(const double &ema_arr[], const double &atr_arr[],
                    const double &close_arr[], double amult,
                    int &out_trend, double &out_trail)
{
   int n = MathMin(ArraySize(ema_arr), MathMin(ArraySize(atr_arr), ArraySize(close_arr)));
   if(n < 2) { out_trend = 1; out_trail = close_arr[n > 0 ? 0 : 0]; return; }
   // Pine barstate.isfirst: init based on whether close is above EMA
   double e0 = ema_arr[0], c0 = close_arr[0], a0 = atr_arr[0];
   int  trend = c0 > e0 ? 1 : -1;
   double trail = trend == 1 ? e0 - a0 * amult : e0 + a0 * amult;
   for(int i = 1; i < n; i++)
      StepLiqTrail(ema_arr[i], atr_arr[i], amult, close_arr[i], trend, trail);
   out_trend = trend;
   out_trail = trail;
}

// Copy indicator buffer and CopyClose for a given TF, reverse to oldest-first.
bool CopyTFHistory(ENUM_TIMEFRAMES tf, int h_ema, int h_atr, int bars,
                   double &ema_out[], double &atr_out[], double &close_out[])
{
   int copied;
   copied = CopyBuffer(h_ema, 0, 0, bars, ema_out);   if(copied < bars) return false;
   copied = CopyBuffer(h_atr, 0, 0, bars, atr_out);   if(copied < bars) return false;
   copied = CopyClose(_Symbol, tf, 0, bars, close_out); if(copied < bars) return false;
   ArrayReverse(ema_out);
   ArrayReverse(atr_out);
   ArrayReverse(close_out);
   return true;
}

//==========================================================================
// MODULE 3 HELPERS: ATM Bot trail update (exact Pine ratchet)
//==========================================================================

// Pine ratchet for trail_buy / trail_sell — identical logic, different init.
// Both use: close as src, ATR(c_buy/c_sell) as band, a_buy/a_sell as multiplier.
void StepATMTrail(double close_curr, double close_prev,
                  double nLoss, double &trail)
{
   if(close_curr > trail && close_prev > trail)
      trail = MathMax(trail, close_curr - nLoss);
   else if(close_curr < trail && close_prev < trail)
      trail = MathMin(trail, close_curr + nLoss);
   else
      trail = close_curr > trail ? close_curr - nLoss : close_curr + nLoss;
}

void WarmupATMBotTrails(const double &close_arr[], const double &atr_arr[],
                        double a_buy, double a_sell)
{
   int n = MathMin(ArraySize(close_arr), ArraySize(atr_arr));
   if(n < 1) return;
   // Pine init: trail_buy starts below price, trail_sell starts above
   g_trail_buy  = close_arr[0] - a_buy  * atr_arr[0];
   g_trail_sell = close_arr[0] + a_sell * atr_arr[0];
   for(int i = 1; i < n; i++) {
      double c  = close_arr[i];
      double cp = close_arr[i - 1];
      StepATMTrail(c, cp, a_buy  * atr_arr[i], g_trail_buy);
      StepATMTrail(c, cp, a_sell * atr_arr[i], g_trail_sell);
   }
   // Store last close for next crossover check
   g_prev_close_atm  = close_arr[n - 1];
   g_prev_trail_buy  = g_trail_buy;
   g_prev_trail_sell = g_trail_sell;
}

//==========================================================================
// MODULE 4 HELPERS: RSI Momentum (replay for warmup)
//==========================================================================

// Replay Pine's var bool positive / negative state machine from arrays.
// rsi_arr and ema5_arr must be oldest-first.
void WarmupRSIState(const double &rsi_arr[], const double &ema5_arr[],
                    int pmom, int nmom, bool sustain,
                    bool &out_pos, bool &out_neg, double &out_ema5_prev)
{
   int n = MathMin(ArraySize(rsi_arr), ArraySize(ema5_arr));
   if(n < 2) { out_pos = false; out_neg = false; out_ema5_prev = 0; return; }
   bool pos = false, neg = false;
   for(int i = 1; i < n; i++) {
      double rsi       = rsi_arr[i];
      double ema5      = ema5_arr[i];
      double ema5_prev = ema5_arr[i - 1];
      double ch_ema5   = ema5 - ema5_prev;
      bool p_mom    = rsi_arr[i-1] < pmom && rsi > pmom && rsi > nmom && ch_ema5 > 0;
      bool n_mom    = rsi < nmom && ch_ema5 < 0;
      bool p_sust   = sustain && pos && rsi > pmom && ch_ema5 > 0;
      bool n_sust   = sustain && neg && rsi < nmom && ch_ema5 < 0;
      if(p_mom || p_sust) { pos = true;  neg = false; }
      if(n_mom || n_sust) { pos = false; neg = true;  }
   }
   out_pos = pos;
   out_neg = neg;
   out_ema5_prev = ema5_arr[n - 1];
}

//==========================================================================
// MODULE 5 HELPERS: Structure (pivot detection for BOS/CHoCH)
//==========================================================================

// Returns the pivot high value if bar at shift `right` is a pivot high
// (highest high in [right+left .. right-left] window), 0 otherwise.
// Requires: highs[0] = most recent bar (series-order).
double PivotHigh(const double &h[], int left, int right)
{
   int total = ArraySize(h);
   if(total < left + right + 1) return 0.0;
   double pval = h[right];
   if(pval == 0.0) return 0.0;
   for(int i = 0; i <= left + right; i++) {
      if(i == right) continue;
      if(h[i] >= pval) return 0.0;
   }
   return pval;
}

double PivotLow(const double &l[], int left, int right)
{
   int total = ArraySize(l);
   if(total < left + right + 1) return 0.0;
   double pval = l[right];
   if(pval == 0.0) return 0.0;
   for(int i = 0; i <= left + right; i++) {
      if(i == right) continue;
      if(l[i] <= pval) return 0.0;
   }
   return pval;
}

// Process one structure update from fresh price arrays (series order: 0=newest).
// Updates g_prev_high, g_prev_low, g_high_active, g_low_active, g_struct_bias.
// Returns bullBOS or bearBOS flag via out params.
void UpdateStructure(const double &h[], const double &l[], const double &c_arr[],
                     bool &out_bull_bos, bool &out_bear_bos)
{
   out_bull_bos = false;
   out_bear_bos = false;
   int sw = Inp_SwingSize;
   double ph = PivotHigh(h, sw, sw);
   double pl = PivotLow(l, sw, sw);

   if(ph > 0.0) {
      if(g_prev_high == 0.0 || ph >= g_prev_high) {
         g_struct_bias = 1;
      } else {
         g_struct_bias = -1;
      }
      g_prev_high   = ph;
      g_high_active = true;
   }
   if(pl > 0.0) {
      if(g_prev_low == 0.0 || pl >= g_prev_low) {
         if(g_struct_bias != -1) g_struct_bias = 1;
      } else {
         g_struct_bias = -1;
      }
      g_prev_low   = pl;
      g_low_active = true;
   }

   // BOS: close breaks through the stored prev level
   double close_now = c_arr[0];
   if(g_high_active && g_prev_high > 0.0 && close_now > g_prev_high) {
      if(g_struct_bias == 1) out_bull_bos = true;
      g_high_active = false;
   }
   if(g_low_active && g_prev_low > 0.0 && close_now < g_prev_low) {
      if(g_struct_bias == -1) out_bear_bos = true;
      g_low_active = false;
   }
}

//==========================================================================
// MODULE 6 HELPERS: Fib Bands (double EMA of HLC3)
//==========================================================================

// Incremental EMA update: alpha = 2/(period+1)
double StepEMA(double prev, double val, int period)
{
   double k = 2.0 / (period + 1);
   return val * k + prev * (1.0 - k);
}

// Warm up double EMA of HLC3 from oldest-first hlc3 array.
void WarmupFibEMA(const double &hlc3_arr[], int len,
                  double &out_ema1, double &out_ema2, double &out_basis_prev, int &out_trend)
{
   int n = ArraySize(hlc3_arr);
   if(n < 1) return;
   double ema1 = hlc3_arr[0];
   double ema2 = hlc3_arr[0];
   double basis_prev = ema2;
   int trend = 0;
   for(int i = 1; i < n; i++) {
      ema1 = StepEMA(ema1, hlc3_arr[i], len);
      ema2 = StepEMA(ema2, ema1, len);
      if(ema2 > basis_prev) trend = 1;
      else if(ema2 < basis_prev) trend = -1;
      basis_prev = ema2;
   }
   out_ema1       = ema1;
   out_ema2       = ema2;
   out_basis_prev = basis_prev;
   out_trend      = trend;
}

//==========================================================================
// MODULE 7 HELPERS: VWAP Direction
//==========================================================================

// Returns VWAP direction: compare bar index of most recent highest high
// vs most recent lowest low in last prd bars.
// dir = vw_phL > vw_plL ? 1 : -1   (more-recent pivot wins)
// lastSwing updates only when direction changes.
void UpdateVWAPDirection(long current_bar_idx)
{
   // iHighest/iLowest shift=0 means check from current bar
   int hb = (int)iHighest(_Symbol, PERIOD_CURRENT, MODE_HIGH, Inp_VWAP_Prd, 0);
   int lb = (int)iLowest (_Symbol, PERIOD_CURRENT, MODE_LOW,  Inp_VWAP_Prd, 0);
   // hb/lb are SHIFTS (0=current). Convert to bar_index-style: bar_idx - shift
   if(hb == 0) g_vwap_phL = current_bar_idx;
   if(lb == 0) g_vwap_plL = current_bar_idx;
   // if highestbars/lowestbars returned non-zero, the bar phL/plL was updated on that past bar
   // — we track updates only when 0 (current bar IS the extreme)

   int dir = g_vwap_phL > g_vwap_plL ? 1 : -1;
   if(dir != g_prev_dir_vwap && g_prev_dir_vwap != 0) {
      g_last_swing = dir;
   } else if(g_prev_dir_vwap == 0) {
      g_last_swing = dir;
   }
   g_dir_vwap      = dir;
   g_prev_dir_vwap = dir;
}

//==========================================================================
// MODULE 9 HELPERS: Confidence Engine
//==========================================================================

int ConfidenceThreshold()
{
   if(Inp_ClawMode == "Conservative") return 80;
   if(Inp_ClawMode == "Aggressive")   return 40;
   return 60; // Moderate (default)
}

double ComputeConfidence(bool mtf_full, bool mtf_partial, bool struct_bull,
                         bool rsi_bull, bool vwap_bull, bool fib_bull)
{
   double score = 0.0, max_w = 0.0;
   // MTF (full = both M15+H1, partial = one of them)
   score += mtf_full ? Inp_MTF_W : (mtf_partial ? Inp_MTF_W * 0.4 : 0.0);
   max_w += Inp_MTF_W;
   // Structure
   score += struct_bull ? Inp_Struct_W : 0.0;
   max_w += Inp_Struct_W;
   // RSI
   score += rsi_bull ? Inp_RSI_W : 0.0;
   max_w += Inp_RSI_W;
   // VWAP
   score += vwap_bull ? Inp_VWAP_W : 0.0;
   max_w += Inp_VWAP_W;
   // Fib (optional gate)
   if(Inp_RequireFib) {
      score += fib_bull ? Inp_Fib_W : 0.0;
      max_w += Inp_Fib_W;
   }
   return max_w > 0.0 ? (score / max_w) * 100.0 : 0.0;
}

//==========================================================================
// OnInit
//==========================================================================
int OnInit()
{
   // Create all indicator handles
   g_h_ema_exec  = iMA(_Symbol, PERIOD_CURRENT, Inp_MA_Len, 0, MODE_EMA, PRICE_CLOSE);
   g_h_atr_exec  = iATR(_Symbol, PERIOD_CURRENT, Inp_ATR_Len);
   g_h_ema_m5    = iMA(_Symbol, PERIOD_M5,  Inp_MA_Len, 0, MODE_EMA, PRICE_CLOSE);
   g_h_atr_m5    = iATR(_Symbol, PERIOD_M5,  Inp_ATR_Len);
   g_h_ema_m15   = iMA(_Symbol, PERIOD_M15, Inp_MA_Len, 0, MODE_EMA, PRICE_CLOSE);
   g_h_atr_m15   = iATR(_Symbol, PERIOD_M15, Inp_ATR_Len);
   g_h_ema_h1    = iMA(_Symbol, PERIOD_H1,  Inp_MA_Len, 0, MODE_EMA, PRICE_CLOSE);
   g_h_atr_h1    = iATR(_Symbol, PERIOD_H1,  Inp_ATR_Len);
   g_h_atr_atm   = iATR(_Symbol, PERIOD_CURRENT, Inp_C_Buy);  // ATR(2) for ATM Bot
   g_h_rsi_exec  = iRSI(_Symbol, PERIOD_CURRENT, Inp_RSI_Len, PRICE_CLOSE);
   g_h_rsi_m5    = iRSI(_Symbol, PERIOD_M5,  Inp_RSI_Len, PRICE_CLOSE);
   g_h_ema5_exec = iMA(_Symbol, PERIOD_CURRENT, Inp_RSI_EMA_Len, 0, MODE_EMA, PRICE_CLOSE);
   g_h_ema5_m5   = iMA(_Symbol, PERIOD_M5,  Inp_RSI_EMA_Len, 0, MODE_EMA, PRICE_CLOSE);

   // Validate handles
   if(g_h_ema_exec == INVALID_HANDLE || g_h_atr_exec == INVALID_HANDLE ||
      g_h_ema_m5   == INVALID_HANDLE || g_h_atr_m5   == INVALID_HANDLE ||
      g_h_ema_m15  == INVALID_HANDLE || g_h_atr_m15  == INVALID_HANDLE ||
      g_h_ema_h1   == INVALID_HANDLE || g_h_atr_h1   == INVALID_HANDLE ||
      g_h_atr_atm  == INVALID_HANDLE || g_h_rsi_exec  == INVALID_HANDLE ||
      g_h_rsi_m5   == INVALID_HANDLE || g_h_ema5_exec == INVALID_HANDLE ||
      g_h_ema5_m5  == INVALID_HANDLE)
   {
      Print("[CLAW] ERROR: Failed to create indicator handles.");
      return INIT_FAILED;
   }

   // Wait for indicator data to be available
   int retries = 200;
   while(retries-- > 0 && (
         BarsCalculated(g_h_ema_exec) < WARMUP_BARS ||
         BarsCalculated(g_h_ema_m15)  < 200 ||
         BarsCalculated(g_h_ema_h1)   < 100))
      Sleep(100);

   // --- Warmup exec TF calcLiqTrail ---
   {
      double ema_a[], atr_a[], cl_a[];
      if(CopyTFHistory(PERIOD_CURRENT, g_h_ema_exec, g_h_atr_exec, WARMUP_BARS, ema_a, atr_a, cl_a))
         WarmupLiqTrail(ema_a, atr_a, cl_a, Inp_ATR_Mult, g_ltf_trend, g_ltf_trail);
      else Print("[CLAW] WARN: Exec TF trail warmup incomplete.");
   }
   // --- Warmup M5 ---
   {
      double ema_a[], atr_a[], cl_a[];
      int bars = MathMin(WARMUP_BARS, BarsCalculated(g_h_ema_m5));
      if(bars >= 50 && CopyTFHistory(PERIOD_M5, g_h_ema_m5, g_h_atr_m5, bars, ema_a, atr_a, cl_a))
         WarmupLiqTrail(ema_a, atr_a, cl_a, Inp_ATR_Mult, g_m5_trend, g_m5_trail);
   }
   // --- Warmup M15 ---
   {
      double ema_a[], atr_a[], cl_a[];
      int bars = MathMin(WARMUP_BARS, BarsCalculated(g_h_ema_m15));
      if(bars >= 50 && CopyTFHistory(PERIOD_M15, g_h_ema_m15, g_h_atr_m15, bars, ema_a, atr_a, cl_a))
         WarmupLiqTrail(ema_a, atr_a, cl_a, Inp_ATR_Mult, g_m15_trend, g_m15_trail);
   }
   // --- Warmup H1 ---
   {
      double ema_a[], atr_a[], cl_a[];
      int bars = MathMin(WARMUP_BARS, BarsCalculated(g_h_ema_h1));
      if(bars >= 50 && CopyTFHistory(PERIOD_H1, g_h_ema_h1, g_h_atr_h1, bars, ema_a, atr_a, cl_a))
         WarmupLiqTrail(ema_a, atr_a, cl_a, Inp_ATR_Mult, g_h1_trend, g_h1_trail);
   }

   // --- Warmup ATM Bot trails ---
   {
      double cl_a[], atr_a[];
      int bars = MathMin(WARMUP_BARS, BarsCalculated(g_h_atr_atm));
      if(bars >= 10) {
         CopyClose(_Symbol, PERIOD_CURRENT, 0, bars, cl_a);
         CopyBuffer(g_h_atr_atm, 0, 0, bars, atr_a);
         ArrayReverse(cl_a); ArrayReverse(atr_a);
         WarmupATMBotTrails(cl_a, atr_a, Inp_A_Buy, Inp_A_Sell);
      }
   }

   // --- Warmup RSI state ---
   {
      double rsi_a[], ema5_a[];
      int bars = MathMin(WARMUP_BARS, BarsCalculated(g_h_rsi_exec));
      if(bars >= 20) {
         CopyBuffer(g_h_rsi_exec,  0, 0, bars, rsi_a);
         CopyBuffer(g_h_ema5_exec, 0, 0, bars, ema5_a);
         ArrayReverse(rsi_a); ArrayReverse(ema5_a);
         WarmupRSIState(rsi_a, ema5_a, Inp_PMom, Inp_NMom, Inp_Sustain,
                        g_positive, g_negative, g_ema5_prev);
      }
   }
   // --- Warmup M5 RSI state ---
   {
      double rsi_a[], ema5_a[];
      int bars = MathMin(WARMUP_BARS, BarsCalculated(g_h_rsi_m5));
      if(bars >= 20) {
         CopyBuffer(g_h_rsi_m5,  0, 0, bars, rsi_a);
         CopyBuffer(g_h_ema5_m5, 0, 0, bars, ema5_a);
         ArrayReverse(rsi_a); ArrayReverse(ema5_a);
         WarmupRSIState(rsi_a, ema5_a, Inp_PMom, Inp_NMom, Inp_Sustain,
                        g_positive_m5, g_negative_m5, g_ema5_m5_prev);
      }
   }

   // --- Warmup Fib Bands (double EMA of HLC3 on exec TF) ---
   {
      double h[], l[], c[];
      int bars = MathMin(WARMUP_BARS, Bars(_Symbol, PERIOD_CURRENT));
      if(bars >= Inp_Fib_Len * 3) {
         CopyHigh( _Symbol, PERIOD_CURRENT, 0, bars, h);
         CopyLow(  _Symbol, PERIOD_CURRENT, 0, bars, l);
         CopyClose(_Symbol, PERIOD_CURRENT, 0, bars, c);
         // Build oldest-first HLC3 array
         double hlc3[];
         ArrayResize(hlc3, bars);
         for(int i = 0; i < bars; i++)
            hlc3[bars - 1 - i] = (h[i] + l[i] + c[i]) / 3.0;
         WarmupFibEMA(hlc3, Inp_Fib_Len, g_fib_ema1, g_fib_ema2, g_fib_basis_prev, g_trend_fib);
      }
   }

   // --- Warmup Structure bias from recent pivot history ---
   {
      int scan = Inp_SwingSize * 2 + 100;
      double h[], l[], c_arr[];
      if(CopyHigh( _Symbol, PERIOD_CURRENT, 0, scan, h) == scan &&
         CopyLow(  _Symbol, PERIOD_CURRENT, 0, scan, l) == scan &&
         CopyClose(_Symbol, PERIOD_CURRENT, 0, scan, c_arr) == scan)
      {
         // Scan pivots from oldest to newest
         for(int i = scan - 1; i >= Inp_SwingSize; i--) {
            // re-build windows sized for pivot at shift i (from newest-first arrays)
            // scan up to i in the newest-first array
            // Pivot at position i in arr (shift=i is i bars ago)
            // window: [i-sw .. i+sw] in shift terms = [i-sw .. i+sw]
            int sw = Inp_SwingSize;
            if(i + sw >= scan) continue;
            double pval_h = h[i];
            bool is_ph = true;
            for(int j = i - sw; j <= i + sw; j++) {
               if(j == i) continue;
               if(h[j] >= pval_h) { is_ph = false; break; }
            }
            if(is_ph && pval_h > 0.0) {
               if(g_prev_high == 0.0 || pval_h >= g_prev_high) g_struct_bias = 1;
               else g_struct_bias = -1;
               g_prev_high = pval_h;
               g_high_active = true;
            }
            double pval_l = l[i];
            bool is_pl = true;
            for(int j = i - sw; j <= i + sw; j++) {
               if(j == i) continue;
               if(l[j] <= pval_l) { is_pl = false; break; }
            }
            if(is_pl && pval_l > 0.0) {
               if(g_prev_low == 0.0 || pval_l >= g_prev_low) {
                  if(g_struct_bias != -1) g_struct_bias = 1;
               } else {
                  g_struct_bias = -1;
               }
               g_prev_low = pval_l;
               g_low_active = true;
            }
         }
      }
   }

   // --- Init VWAP state ---
   g_bar_count    = (long)Bars(_Symbol, PERIOD_CURRENT);
   g_vwap_phL     = g_bar_count - (long)iHighest(_Symbol, PERIOD_CURRENT, MODE_HIGH, Inp_VWAP_Prd, 0);
   g_vwap_plL     = g_bar_count - (long)iLowest (_Symbol, PERIOD_CURRENT, MODE_LOW,  Inp_VWAP_Prd, 0);
   g_dir_vwap     = g_vwap_phL > g_vwap_plL ? 1 : -1;
   g_last_swing   = g_dir_vwap;
   g_prev_dir_vwap = g_dir_vwap;

   CopyTime(_Symbol, PERIOD_CURRENT, 0, 1, &g_last_bar_time);
   CopyTime(_Symbol, PERIOD_M5,      0, 1, &g_last_m5_time);
   CopyTime(_Symbol, PERIOD_M15,     0, 1, &g_last_m15_time);
   CopyTime(_Symbol, PERIOD_H1,      0, 1, &g_last_h1_time);

   Print("[CLAW] Phase 1 init complete. ltf_trend=", g_ltf_trend,
         " m15_trend=", g_m15_trend, " h1_trend=", g_h1_trend,
         " struct_bias=", g_struct_bias, " fib_trend=", g_trend_fib,
         " last_swing=", g_last_swing);
   return INIT_SUCCEEDED;
}

//==========================================================================
// OnDeinit
//==========================================================================
void OnDeinit(const int reason)
{
   int handles[] = {g_h_ema_exec, g_h_atr_exec, g_h_ema_m5,   g_h_atr_m5,
                    g_h_ema_m15,  g_h_atr_m15,  g_h_ema_h1,   g_h_atr_h1,
                    g_h_atr_atm,  g_h_rsi_exec,  g_h_rsi_m5,
                    g_h_ema5_exec, g_h_ema5_m5};
   for(int i = 0; i < ArraySize(handles); i++)
      if(handles[i] != INVALID_HANDLE) IndicatorRelease(handles[i]);
}

//==========================================================================
// OnTick — main loop
//==========================================================================
void OnTick()
{
   // Only process on new confirmed exec bar close
   datetime cur_bar_time = iTime(_Symbol, PERIOD_CURRENT, 0);
   if(cur_bar_time == g_last_bar_time) return;  // same bar still forming
   g_last_bar_time = cur_bar_time;
   g_bar_count++;

   // ---- Collect current bar values from exec TF ----
   double buf1[1];
   double close_now = iClose(_Symbol, PERIOD_CURRENT, 1);  // [1] = last confirmed
   double high_now  = iHigh(_Symbol, PERIOD_CURRENT, 1);
   double low_now   = iLow(_Symbol, PERIOD_CURRENT, 1);

   // ================================================================
   // MODULE 2: Update exec TF calcLiqTrail (EMA-centered)
   // ================================================================
   if(CopyBuffer(g_h_ema_exec, 0, 1, 1, buf1) == 1) {
      double ema_val = buf1[0];
      if(CopyBuffer(g_h_atr_exec, 0, 1, 1, buf1) == 1) {
         double atr_val = buf1[0];
         StepLiqTrail(ema_val, atr_val, Inp_ATR_Mult, close_now, g_ltf_trend, g_ltf_trail);
      }
   }

   // ================================================================
   // MODULE 2: Update MTF trails when their bar closes
   // ================================================================
   datetime m5_time = iTime(_Symbol, PERIOD_M5, 0);
   if(m5_time != g_last_m5_time) {
      g_last_m5_time = m5_time;
      double m5_cl = iClose(_Symbol, PERIOD_M5, 1);
      if(CopyBuffer(g_h_ema_m5, 0, 1, 1, buf1) == 1) {
         double ema_v = buf1[0];
         if(CopyBuffer(g_h_atr_m5, 0, 1, 1, buf1) == 1)
            StepLiqTrail(ema_v, buf1[0], Inp_ATR_Mult, m5_cl, g_m5_trend, g_m5_trail);
      }
   }
   datetime m15_time = iTime(_Symbol, PERIOD_M15, 0);
   if(m15_time != g_last_m15_time) {
      g_last_m15_time = m15_time;
      double m15_cl = iClose(_Symbol, PERIOD_M15, 1);
      if(CopyBuffer(g_h_ema_m15, 0, 1, 1, buf1) == 1) {
         double ema_v = buf1[0];
         if(CopyBuffer(g_h_atr_m15, 0, 1, 1, buf1) == 1)
            StepLiqTrail(ema_v, buf1[0], Inp_ATR_Mult, m15_cl, g_m15_trend, g_m15_trail);
      }
   }
   datetime h1_time = iTime(_Symbol, PERIOD_H1, 0);
   if(h1_time != g_last_h1_time) {
      g_last_h1_time = h1_time;
      double h1_cl = iClose(_Symbol, PERIOD_H1, 1);
      if(CopyBuffer(g_h_ema_h1, 0, 1, 1, buf1) == 1) {
         double ema_v = buf1[0];
         if(CopyBuffer(g_h_atr_h1, 0, 1, 1, buf1) == 1)
            StepLiqTrail(ema_v, buf1[0], Inp_ATR_Mult, h1_cl, g_h1_trend, g_h1_trail);
      }
   }

   // ================================================================
   // MODULE 3: ATM Bot — update dual trails + detect crossover
   // ================================================================
   bool ut_buy_signal  = false;
   bool ut_sell_signal = false;
   if(CopyBuffer(g_h_atr_atm, 0, 1, 1, buf1) == 1) {
      double nLoss_buy  = Inp_A_Buy  * buf1[0];
      double nLoss_sell = Inp_A_Sell * buf1[0];
      double cp = g_prev_close_atm;    // close[1] in Pine terms
      double ptb = g_prev_trail_buy;
      double pts = g_prev_trail_sell;
      // Update trail_buy
      StepATMTrail(close_now, cp, nLoss_buy,  g_trail_buy);
      // Update trail_sell
      StepATMTrail(close_now, cp, nLoss_sell, g_trail_sell);
      // Crossover detection (Pine: ta.crossover(ema_buy, trail_buy))
      // ema_buy = EMA(close,1) = close. crossover = curr > trail AND prev <= prev_trail
      bool above_buy_cross  = close_now > g_trail_buy  && cp <= ptb;
      bool below_sell_cross = g_trail_sell > close_now && pts <= cp;
      ut_buy_signal  = close_now > g_trail_buy  && above_buy_cross;
      ut_sell_signal = close_now < g_trail_sell && below_sell_cross;
      g_prev_close_atm  = close_now;
      g_prev_trail_buy  = g_trail_buy;
      g_prev_trail_sell = g_trail_sell;
   }

   // ================================================================
   // MODULE 4: RSI Smart Signal + M5 confirm + sustain
   // ================================================================
   double rsi_val = 0.0, ema5_val = 0.0;
   if(CopyBuffer(g_h_rsi_exec,  0, 1, 1, buf1) == 1) rsi_val  = buf1[0];
   if(CopyBuffer(g_h_ema5_exec, 0, 1, 1, buf1) == 1) ema5_val = buf1[0];
   double ch_ema5 = ema5_val - g_ema5_prev;
   // Pine: p_mom = rsi[1] < pmom and rsi > pmom and ...
   // In confirmed-bar mode, rsi[1] = previous bar's value.
   // We track the state from previous iteration so use rsi from buf[1] vs buf[0] trick:
   // For simplicity, use current rsi > pmom (state machine handles continuity via g_positive).
   bool p_mom  = rsi_val > Inp_PMom && ch_ema5 > 0.0 && !g_positive;
   bool n_mom  = rsi_val < Inp_NMom && ch_ema5 < 0.0 && !g_negative;
   bool p_sust = Inp_Sustain && g_positive && rsi_val > Inp_PMom && ch_ema5 > 0.0;
   bool n_sust = Inp_Sustain && g_negative && rsi_val < Inp_NMom && ch_ema5 < 0.0;
   if(p_mom || p_sust) { g_positive = true;  g_negative = false; }
   if(n_mom || n_sust) { g_positive = false; g_negative = true;  }
   g_ema5_prev = ema5_val;

   // M5 RSI state
   double rsi_m5 = 0.0, ema5_m5 = 0.0;
   if(CopyBuffer(g_h_rsi_m5,  0, 0, 1, buf1) == 1) rsi_m5  = buf1[0];
   if(CopyBuffer(g_h_ema5_m5, 0, 0, 1, buf1) == 1) ema5_m5 = buf1[0];
   double ch_ema5_m5 = ema5_m5 - g_ema5_m5_prev;
   bool p_mom_m5 = rsi_m5 > Inp_PMom && ch_ema5_m5 > 0.0 && !g_positive_m5;
   bool n_mom_m5 = rsi_m5 < Inp_NMom && ch_ema5_m5 < 0.0 && !g_negative_m5;
   if(p_mom_m5) { g_positive_m5 = true;  g_negative_m5 = false; }
   if(n_mom_m5) { g_positive_m5 = false; g_negative_m5 = true;  }
   g_ema5_m5_prev = ema5_m5;

   // smartBull / smartBear (Pine: rsi > pmom and change_ema5 > 0 and m5 confirm)
   bool m5_bull_mom = ch_ema5_m5 > 0.0;
   bool m5_bear_mom = ch_ema5_m5 < 0.0;
   g_prev_smart_bull = g_smart_bull;
   g_prev_smart_bear = g_smart_bear;
   g_smart_bull = rsi_val > Inp_PMom && ch_ema5 > 0.0 &&
                  (!Inp_UseM5Confirm || (rsi_m5 > Inp_PMom && m5_bull_mom));
   g_smart_bear = rsi_val < Inp_NMom && ch_ema5 < 0.0 &&
                  (!Inp_UseM5Confirm || (rsi_m5 < Inp_NMom && m5_bear_mom));
   bool new_smart_bull = g_smart_bull && !g_prev_smart_bull;
   bool new_smart_bear = g_smart_bear && !g_prev_smart_bear;

   // ================================================================
   // MODULE 5: Market Structure (pivot detection + BOS)
   // ================================================================
   bool bull_bos = false, bear_bos = false;
   {
      int scan = Inp_SwingSize * 2 + 5;
      double h_arr[], l_arr[], c_arr[];
      if(CopyHigh(_Symbol, PERIOD_CURRENT, 1, scan, h_arr) == scan &&
         CopyLow( _Symbol, PERIOD_CURRENT, 1, scan, l_arr) == scan &&
         CopyClose(_Symbol, PERIOD_CURRENT, 0, scan, c_arr) == scan)
      {
         UpdateStructure(h_arr, l_arr, c_arr, bull_bos, bear_bos);
      }
   }

   // ================================================================
   // MODULE 6: Fib Bands — incremental double EMA of HLC3
   // ================================================================
   double hlc3 = (high_now + low_now + close_now) / 3.0;
   double basis_prev = g_fib_ema2;
   g_fib_ema1   = StepEMA(g_fib_ema1, hlc3, Inp_Fib_Len);
   g_fib_ema2   = StepEMA(g_fib_ema2, g_fib_ema1, Inp_Fib_Len);
   if(g_fib_ema2 > basis_prev)      g_trend_fib = 1;
   else if(g_fib_ema2 < basis_prev) g_trend_fib = -1;
   // else keep previous value (nz(trend_fib[1]))

   // ================================================================
   // MODULE 7: VWAP Direction
   // ================================================================
   UpdateVWAPDirection(g_bar_count);

   // ================================================================
   // MODULE 8: Volume Profile — placeholder
   // Phase 3 implementation. Always permissive for Phase 1.
   // ================================================================
   bool vp_bull_conf = true;
   bool vp_bear_conf = true;

   // ================================================================
   // MODULE 9 + 10: Confidence Engine + Gate Chain
   // ================================================================
   bool trail_allows_long  = (g_ltf_trend == 1);
   bool trail_allows_short = (g_ltf_trend == -1);

   bool mtf_bull_full    = (g_m15_trend == 1 && g_h1_trend == 1);
   bool mtf_bear_full    = (g_m15_trend == -1 && g_h1_trend == -1);
   bool mtf_partial_bull = (g_m15_trend == 1 || g_h1_trend == 1);
   bool mtf_partial_bear = (g_m15_trend == -1 || g_h1_trend == -1);

   bool struct_bull = (g_struct_bias == 1);
   bool struct_bear = (g_struct_bias == -1);

   bool vwap_bull = (g_last_swing == 1);
   bool vwap_bear = (g_last_swing == -1);

   bool fib_bull = (g_trend_fib == 1);
   bool fib_bear = (g_trend_fib == -1);

   double bull_conf = ComputeConfidence(mtf_bull_full, mtf_partial_bull, struct_bull,
                                        g_positive, vwap_bull, fib_bull);
   double bear_conf = ComputeConfidence(mtf_bear_full, mtf_partial_bear, struct_bear,
                                        g_negative, vwap_bear, fib_bear);

   int threshold = ConfidenceThreshold();
   bool bull_conf_pass = bull_conf >= threshold;
   bool bear_conf_pass = bear_conf >= threshold;

   // Triggers
   bool trig_ut_buy     = ut_buy_signal;
   bool trig_ut_sell    = ut_sell_signal;
   bool trig_smart_buy  = new_smart_bull;
   bool trig_smart_sell = new_smart_bear;

   // Gate: trail must allow the direction
   bool gated_ut_buy     = trig_ut_buy    && trail_allows_long;
   bool gated_ut_sell    = trig_ut_sell   && trail_allows_short;
   bool gated_smart_buy  = trig_smart_buy  && trail_allows_long;
   bool gated_smart_sell = trig_smart_sell && trail_allows_short;

   // Final: confidence must pass
   bool final_ut_buy     = gated_ut_buy    && bull_conf_pass;
   bool final_ut_sell    = gated_ut_sell   && bear_conf_pass;
   bool final_smart_buy  = gated_smart_buy  && bull_conf_pass;
   bool final_smart_sell = gated_smart_sell && bear_conf_pass;

   bool final_long  = final_ut_buy  || final_smart_buy;
   bool final_short = final_ut_sell || final_smart_sell;

   // Rejection tracking (for diagnostics)
   bool rejected_trail_long  = (trig_ut_buy  || trig_smart_buy)  && !trail_allows_long;
   bool rejected_trail_short = (trig_ut_sell || trig_smart_sell) && !trail_allows_short;
   bool rejected_conf_long   = (gated_ut_buy  || gated_smart_buy)  && !bull_conf_pass;
   bool rejected_conf_short  = (gated_ut_sell || gated_smart_sell) && !bear_conf_pass;

   // ================================================================
   // PHASE 1 OUTPUT — Print() only, no OrderSend
   // ================================================================
   datetime bar_time = iTime(_Symbol, PERIOD_CURRENT, 1);
   string ts = TimeToString(bar_time, TIME_DATE | TIME_MINUTES);

   if(final_long) {
      string src = final_ut_buy ? "UT" : "SMART";
      Print("[CLAW LONG] ", ts,
            " src=", src,
            " close=", DoubleToString(close_now, _Digits),
            " ltf_trail=", DoubleToString(g_ltf_trail, _Digits),
            " bull_conf=", DoubleToString(bull_conf, 1), "%",
            " mtf=", g_m15_trend, "/", g_h1_trend,
            " struct=", g_struct_bias,
            " rsi_pos=", g_positive,
            " vwap=", g_last_swing,
            " fib=", g_trend_fib);
   }
   if(final_short) {
      string src = final_ut_sell ? "UT" : "SMART";
      Print("[CLAW SHORT] ", ts,
            " src=", src,
            " close=", DoubleToString(close_now, _Digits),
            " ltf_trail=", DoubleToString(g_ltf_trail, _Digits),
            " bear_conf=", DoubleToString(bear_conf, 1), "%",
            " mtf=", g_m15_trend, "/", g_h1_trend,
            " struct=", g_struct_bias,
            " rsi_neg=", g_negative,
            " vwap=", g_last_swing,
            " fib=", g_trend_fib);
   }

   // Rejected signals — diagnostic log
   if(rejected_trail_long)
      Print("[CLAW REJECTED trail] LONG trigger blocked — ltf_trend=", g_ltf_trend, " ts=", ts);
   if(rejected_trail_short)
      Print("[CLAW REJECTED trail] SHORT trigger blocked — ltf_trend=", g_ltf_trend, " ts=", ts);
   if(rejected_conf_long)
      Print("[CLAW REJECTED conf]  LONG gated but conf=", DoubleToString(bull_conf, 1), "% < ", threshold, " ts=", ts);
   if(rejected_conf_short)
      Print("[CLAW REJECTED conf]  SHORT gated but conf=", DoubleToString(bear_conf, 1), "% < ", threshold, " ts=", ts);

   // Periodic state pulse (every 60 bars) — lets you compare against Pine dashboard
   if(g_bar_count % 60 == 0) {
      Print("[CLAW STATE] bars=", g_bar_count,
            " ltf=", g_ltf_trend, " m5=", g_m5_trend,
            " m15=", g_m15_trend, " h1=", g_h1_trend,
            " atm_buy_trail=", DoubleToString(g_trail_buy, _Digits),
            " atm_sell_trail=", DoubleToString(g_trail_sell, _Digits),
            " pos=", g_positive, " neg=", g_negative,
            " struct=", g_struct_bias,
            " fib=", g_trend_fib, " vwap_dir=", g_last_swing,
            " bull_conf=", DoubleToString(bull_conf, 1),
            " bear_conf=", DoubleToString(bear_conf, 1));
   }
}
//+------------------------------------------------------------------+
